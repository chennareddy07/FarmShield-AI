"""AI advisory + Q&A (F7, F14). Never changes the engine's risk output; always has a deterministic fallback."""
import logging
import uuid
from typing import List, Optional

from ..core import i18n
from ..utils.timeutil import iso, utcnow
from . import fallback, output_validator as ov, prompt_templates as pt
from .llm_provider import LLMProvider, LLMUnavailable, get_provider

log = logging.getLogger("farmshield.ai")


def _evidence_index(assessment: dict) -> dict:
    return {e["evidence_id"]: e for e in assessment["evidence"]}


def _is_reference_evidence(item: dict, assessment: dict) -> bool:
    return (
        item.get("kind") == "agricultural_reference"
        and item.get("crop_id") == assessment["crop_id"]
        and item.get("growth_stage_id") in (None, assessment.get("growth_stage_id"))
        and item.get("evidence_status") in {"source_verified", "expert_review_required", "expert_approved"}
        and item.get("source_access_status") in {"source_verified", "page_verified", "pdf_verified"}
    )


def _is_expert_approved_action(item: dict) -> bool:
    return (
        item.get("evidence_status") == "expert_approved"
        and item.get("verification_status") == "verified"
        and item.get("content_type") == "recommendation"
    )


async def generate_advisory(assessment: dict, language: str, question: Optional[str] = None, personalisation: Optional[str] = None,
                            provider: Optional[LLMProvider] = None) -> dict:
    provider = provider or get_provider()
    idx = _evidence_index(assessment)
    passages = [e for e in assessment["evidence"] if _is_reference_evidence(e, assessment)]
    action_evidence = [e for e in passages if _is_expert_approved_action(e)]
    if provider.name == "disabled":
        return fallback.build_fallback(assessment, language, "fallback_no_provider", [i18n.msg(language, "ai_unavailable")], personalisation)
    prompt = pt.build_advisory_prompt(assessment, passages, language, question, personalisation)
    valid_ids = set(idx)
    last_errors: List[str] = []
    for attempt in range(2):                                   # initial + exactly one constrained retry (L10)
        try:
            raw = await provider.generate_json(pt.SYSTEM_ADVISORY, prompt if attempt == 0 else pt.build_correction_prompt(prompt, last_errors))
        except LLMUnavailable as e:
            log.warning("llm unavailable: %s", e.reason)
            if attempt == 0 and e.reason.startswith("bad_output"):
                last_errors = ["output was not valid JSON"]
                continue
            return fallback.build_fallback(assessment, language, "fallback_ai_unavailable", [i18n.msg(language, "ai_unavailable")], personalisation)
        ok, clean, errors = ov.validate_advisory(raw, valid_ids, language, assessment["overall_risk"], bool(action_evidence))
        if ok:
            notices = []
            if any(idx[i].get("verification_status") == "needs_review" for i in clean["evidence_ids"] if i in idx):
                notices.append(i18n.msg(language, "unverified_evidence"))
            return {"advisory_id": f"adv-{uuid.uuid4().hex[:12]}", **clean, "language": language, "generated_at": iso(utcnow()),
                    "model_provider": provider.name, "generation_status": "ai_generated", "notices": notices,
                    "disclaimer": i18n.msg(language, "disclaimer"), "personalisation_note": personalisation,
                    "evidence": [idx[i] for i in clean["evidence_ids"]]}
        last_errors = errors
        log.warning("advisory validation failed (attempt %d): %s", attempt + 1, errors)
    return fallback.build_fallback(assessment, language, "fallback_invalid_output", [i18n.msg(language, "ai_invalid")], personalisation)


async def answer_question(message: str, language: str, assessment: Optional[dict], passages: List[dict], history: List[str],
                          provider: Optional[LLMProvider] = None, tool_results: Optional[List[dict]] = None,
                          user_context: Optional[dict] = None) -> dict:
    """F14: grounded Q&A. Out-of-knowledge questions are declined explicitly."""
    provider = provider or get_provider()
    by_id = {p["evidence_id"]: p for p in passages}
    if assessment:
        for e in assessment["evidence"]:
            by_id.setdefault(e["evidence_id"], e)
    for result in tool_results or []:
        for evidence in result.get("evidence", []):
            by_id.setdefault(evidence["evidence_id"], evidence)
    if assessment:
        by_id.setdefault("EV-ASSESSMENT-CALC", {"evidence_id": "EV-ASSESSMENT-CALC", "kind": "risk_assessment",
                                                "title": "FarmShield deterministic assessment", "publisher": "FarmShield",
                                                "publication_date": assessment.get("assessment_time"), "verification_status": "calculated"})
        if assessment.get("weather_snapshot", {}).get("current", {}).get("current"):
            by_id.setdefault("EV-ASSESSMENT-WEATHER-ANALYSIS", {"evidence_id": "EV-ASSESSMENT-WEATHER-ANALYSIS",
                "kind": "forecast", "title": "Open-Meteo current model analysis", "publisher": "Open-Meteo",
                "publication_date": assessment.get("weather_snapshot", {}).get("current", {}).get("retrieved_at"),
                "excerpt": "Model analysis, not a station observation.", "source_url": "https://open-meteo.com",
                "verification_status": "official"})
        if assessment.get("weather_snapshot", {}).get("forecast", {}).get("daily"):
            by_id.setdefault("EV-ASSESSMENT-FORECAST", {"evidence_id": "EV-ASSESSMENT-FORECAST", "kind": "forecast",
                "title": "Open-Meteo weather forecast", "publisher": "Open-Meteo",
                "publication_date": assessment.get("weather_snapshot", {}).get("forecast", {}).get("retrieved_at"),
                "excerpt": "Forecast values are model data, not station observations.", "source_url": "https://open-meteo.com",
                "verification_status": "official"})
    if not by_id and not assessment:
        return {"answer": i18n.msg(language, "chat_out_of_scope"), "evidence": [], "uncertainties": [i18n.msg(language, "no_evidence")], "status": "out_of_scope"}
    if provider.name == "disabled":
        if assessment:
            return _assessment_chat_fallback(assessment, by_id, user_context, tool_results or [], language)
        if not by_id and not assessment:
            return {"answer": i18n.msg(language, "chat_out_of_scope"), "evidence": [], "uncertainties": [i18n.msg(language, "no_evidence")], "status": "out_of_scope"}
        lines = [i18n.msg(language, "chat_no_llm")]
        lines.extend(f"- {p['title']} ({p.get('publisher')}): {p.get('excerpt', '')[:300]}" for p in passages[:3])
        lines.extend(_tool_result_summaries(tool_results or [], language))
        unc = [i18n.msg(language, "ai_unavailable")]
        unc.extend(_tool_result_uncertainties(tool_results or [], language))
        if any(p.get("verification_status") == "needs_review" for p in passages[:3]):
            unc.append(i18n.msg(language, "unverified_evidence"))
        if not passages and not any(result.get("status") == "available" for result in tool_results or []):
            lines = [i18n.msg(language, "chat_context_no_llm")]
        return {"answer": "\n".join(lines), "evidence": list(by_id.values())[:5], "uncertainties": unc, "status": "retrieval_only"}
    view = pt._assessment_view(assessment) if assessment else None
    verified_actions = []
    if user_context and user_context.get("crop_id"):
        for item in passages:
            if item.get("kind") != "agricultural_reference" or not _is_expert_approved_action(item):
                continue
            if item.get("crop_id") != user_context["crop_id"]:
                continue
            if item.get("growth_stage_id") not in (None, user_context.get("growth_stage_id")):
                continue
            verified_actions.append(item)
    prompt = pt.build_chat_prompt(message, view, list(by_id.values()), language, history, tool_results, user_context)
    errors: List[str] = []
    for attempt in range(2):
        try:
            raw = await provider.generate_json(pt.SYSTEM_CHAT, prompt if attempt == 0 else pt.build_correction_prompt(prompt, errors))
        except LLMUnavailable:
            if assessment:
                return _assessment_chat_fallback(assessment, by_id, user_context, tool_results or [], language)
            lines = [i18n.msg(language, "ai_unavailable")]
            lines.extend(f"- {p['title']}: {p.get('excerpt', '')[:240]}" for p in passages[:2])
            lines.extend(_tool_result_summaries(tool_results or [], language))
            uncertainties = [i18n.msg(language, "ai_unavailable")]
            uncertainties.extend(_tool_result_uncertainties(tool_results or [], language))
            return {"answer": "\n".join(lines), "evidence": list(by_id.values())[:5],
                    "uncertainties": list(dict.fromkeys(uncertainties)), "status": "retrieval_only"}
        ok, clean, errors = ov.validate_chat(raw, set(by_id), language, assessment["overall_risk"] if assessment else None,
                                             allow_crop_actions=bool(verified_actions))
        if ok:
            if not clean["in_scope"] or (not clean["evidence_ids"] and not assessment):
                return {"answer": i18n.msg(language, "chat_out_of_scope"), "evidence": [], "uncertainties": clean["uncertainties"], "status": "out_of_scope"}
            ev = [by_id[i] for i in clean["evidence_ids"]]
            unc = clean["uncertainties"] + _tool_result_uncertainties(tool_results or [], language)
            if any(e.get("verification_status") == "needs_review" for e in ev):
                unc.append(i18n.msg(language, "unverified_evidence"))
            unc = list(dict.fromkeys(unc))
            return {"answer": clean["answer"], "evidence": ev, "uncertainties": unc, "status": "ai_generated"}
    answer_lines = [i18n.msg(language, "ai_invalid")]
    answer_lines.extend(_tool_result_summaries(tool_results or [], language))
    uncertainties = [i18n.msg(language, "ai_invalid")]
    uncertainties.extend(_tool_result_uncertainties(tool_results or [], language))
    return {"answer": "\n".join(answer_lines), "evidence": list(by_id.values())[:5],
            "uncertainties": list(dict.fromkeys(uncertainties)), "status": "fallback_invalid_output"}


def _assessment_chat_fallback(assessment: dict, evidence_by_id: dict, user_context: Optional[dict],
                              tool_results: List[dict], language: str) -> dict:
    unassessed = [item["label"] for item in assessment["coverage"].get("not_assessed", [])]
    answer = i18n.msg(language, "chat_assessment", risk=assessment["overall_risk_label"],
                      time=assessment.get("assessment_time") or "unknown time",
                      unassessed=", ".join(unassessed) or i18n.msg(language, "none"))
    summaries = _tool_result_summaries(tool_results, language)
    if summaries:
        answer += "\n" + "\n".join(summaries)
    uncertainties = [i18n.msg(language, "forecast_not_observation")]
    if user_context and user_context.get("assessment_snapshot_status") == "historical":
        uncertainties.append(i18n.msg(language, "chat_assessment_stale"))
    uncertainties.extend(_tool_result_uncertainties(tool_results, language))
    ids = ["EV-ASSESSMENT-CALC"] + [item["evidence_id"] for result in tool_results for item in result.get("evidence", [])]
    evidence = [evidence_by_id[evidence_id] for evidence_id in dict.fromkeys(ids) if evidence_id in evidence_by_id]
    return {"answer": answer, "evidence": evidence, "uncertainties": list(dict.fromkeys(uncertainties)),
            "status": "retrieval_only"}


def _tool_result_summaries(results: List[dict], language: str) -> List[str]:
    summaries = []
    for result in results:
        if result.get("status") != "available":
            continue
        name, data = result.get("name"), result.get("data") or {}
        if name == "get_current_weather":
            current = data.get("current") or {}
            values = []
            labels = {"en": ("temperature", "precipitation", "humidity"),
                      "te": ("ఉష్ణోగ్రత", "వర్షపాతం", "తేమ")}[language]
            for label, key, unit in zip(labels, ("temperature_c", "precipitation_mm", "relative_humidity_pct"),
                                        ("°C", "mm", "%")):
                value = current.get(key)
                if isinstance(value, (int, float)):
                    values.append(f"{label} {value:g}{unit}")
            if values:
                summaries.append(i18n.msg(language, "chat_current_weather", values=", ".join(values)))
            else:
                summaries.append(i18n.msg(language, "chat_weather_missing"))
        elif name == "get_weather_forecast":
            daily = data.get("daily") or []
            rainfall = [f"{item['forecast_for']}: {item['precipitation_sum_mm']:g} mm"
                        for item in daily if isinstance(item.get("precipitation_sum_mm"), (int, float))]
            summaries.append(i18n.msg(language, "chat_forecast", days=len(daily),
                                      rainfall="; ".join(rainfall[:7]) or i18n.msg(language, "no_data")))
        elif name == "get_historical_weather":
            series = data.get("series") or []
            rainfall = [row["precipitation_sum_mm"] for row in series
                        if isinstance(row.get("precipitation_sum_mm"), (int, float))]
            if rainfall:
                summaries.append(i18n.msg(language, "chat_history",
                                          days=len(rainfall), total=f"{sum(rainfall):g}",
                                          coverage=data.get("coverage", {}).get("rainfall_coverage_pct", "unknown")))
            else:
                summaries.append(i18n.msg(language, "chat_weather_missing"))
        elif name == "get_official_warnings":
            warnings = data.get("warnings") or []
            if warnings:
                summaries.extend(f"- {warning.get('title', 'Official warning')}: {warning.get('description') or ''}"
                                 for warning in warnings[:5])
            elif data.get("source_status") == "available":
                summaries.append(i18n.msg(language, "chat_no_warnings"))
            else:
                summaries.append(i18n.msg(language, "warning_unavailable"))
        elif name == "get_crop_growth_stages":
            stages = []
            for item in data.get("stages", []):
                name = item.get("name")
                if isinstance(name, dict):
                    name = name.get(language, name.get("en"))
                if isinstance(name, str) and name:
                    stages.append(name)
            if stages:
                summaries.append(f"{data.get('crop_id')}: {', '.join(stages)}")
        elif name == "search_agricultural_knowledge":
            for item in data.get("results", [])[:3]:
                excerpt = item.get("excerpt")
                if item.get("kind") != "agricultural_reference" or not isinstance(excerpt, str) or not excerpt.strip():
                    continue
                summaries.append(i18n.msg(
                    language, "chat_source_reference",
                    title=item.get("title") or "Agricultural reference",
                    publisher=item.get("publisher") or "Unknown publisher",
                    publication_date=item.get("publication_date") or "date not recorded",
                    section=item.get("source_section") or "section not recorded",
                    excerpt=excerpt[:300],
                    evidence_id=item.get("evidence_id") or "source reference",
                ))
    return summaries


def _tool_result_uncertainties(results: List[dict], language: str) -> List[str]:
    uncertainties = []
    if any(result.get("status") == "unavailable" for result in results):
        uncertainties.append(i18n.msg(language, "data_unavailable"))
    for result in results:
        if result.get("status") != "available":
            continue
        data = result.get("data") or {}
        status = data.get("source_status")
        if result.get("name") == "search_agricultural_knowledge" and any(
                item.get("evidence_status") in {"source_verified", "expert_review_required"}
                for item in data.get("results", [])):
            uncertainties.append(i18n.msg(language, "unverified_evidence"))
        if result.get("name") == "get_official_warnings" and status in {"unavailable", "not_configured", "partial", "stale"}:
            uncertainties.append(i18n.msg(language, "warning_unavailable"))
        quality = data.get("data_quality")
        if isinstance(quality, dict):
            if quality.get("status") == "stale":
                uncertainties.append(i18n.msg(language, "stale_weather", age="unknown"))
            elif quality.get("status") == "partial":
                uncertainties.append(i18n.msg(language, "chat_weather_partial"))
            elif quality.get("status") in {"incomplete", "unavailable", "missing"}:
                uncertainties.append(i18n.msg(language, "data_unavailable"))
    return list(dict.fromkeys(uncertainties))
