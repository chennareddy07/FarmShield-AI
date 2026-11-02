"""Deterministic advisory built ONLY from engine output + retrieved evidence (spec L9/L10, E14/E15)."""
import uuid
from typing import List, Optional

from ..core import i18n
from ..services import crop_config_service as cc
from ..utils.timeutil import iso, utcnow


def stage_display(assessment: dict, language: str) -> Optional[str]:
    sid = assessment.get("growth_stage_id")
    if not sid:
        return None
    try:
        cfg = cc.get_crop(assessment["crop_id"])
        st = cc.validate_stage(cfg, sid)
        return st["name"].get(language) or st["name"]["en"]
    except Exception:
        return sid


def build_fallback(assessment: dict, language: str, status: str, notices: List[str], personalisation: Optional[str] = None) -> dict:
    a = assessment
    crop = i18n.crop_name(language, a["crop_id"])
    loc = a["location"].get("name") or "-"
    risk = i18n.risk_label(language, a["overall_risk"])
    stage = stage_display(a, language)
    summary = i18n.msg(language, "summary", crop=crop, stage=stage, location=loc, risk=risk) if stage else i18n.msg(language, "summary_general", crop=crop, location=loc, risk=risk)
    explanation = " ".join(a["explanations"])
    refs = [e for e in a["evidence"] if e["kind"] == "agricultural_reference"
            and e.get("crop_id") == a["crop_id"]
            and e.get("growth_stage_id") in (None, a.get("growth_stage_id"))
            and e.get("evidence_status") in {"source_verified", "expert_review_required", "expert_approved"}
            and e.get("source_access_status") in {"source_verified", "page_verified", "pdf_verified"}]
    approved_refs = [e for e in refs if e.get("evidence_status") == "expert_approved"
                     and e.get("verification_status") == "verified"]
    supported_evidence_ids = {e["evidence_id"] for e in approved_refs}
    immediate = [x["text"] for x in a["recommended_actions"]
                 if x["kind"] in ("immediate", "general") and x.get("verified")
                 and supported_evidence_ids.intersection(x.get("evidence_ids", []))]
    preventive = []
    unc: List[str] = []
    if a["coverage"]["not_assessed"]:
        unc.append(i18n.msg(language, "no_rules"))
    if not refs:
        unc.append(i18n.msg(language, "no_evidence"))
    if not approved_refs:
        unc.append(i18n.msg(language, "no_crop_action"))
    if any(e.get("verification_status") == "needs_review" for e in a["evidence"]):
        unc.append(i18n.msg(language, "unverified_evidence"))
    if a["warnings_status"] == "partial":
        unc.append(i18n.reason(language, "warning_partial"))
    elif a["warnings_status"] != "available":
        unc.append(i18n.msg(language, "warning_unavailable"))
    unc.append(i18n.msg(language, "forecast_not_observation"))
    tl = a.get("timeline") or []
    when = i18n.msg(language, "when_period", start=min(t["start"] for t in tl), end=max(t["end"] for t in tl)) if tl else ""
    return {"advisory_id": f"adv-{uuid.uuid4().hex[:12]}", "summary": summary, "risk_explanation": explanation, "recommended_actions": immediate,
            "preventive_actions": preventive, "when_to_act": when, "uncertainties": list(dict.fromkeys(unc)),
            "evidence_ids": [e["evidence_id"] for e in a["evidence"]], "language": language, "generated_at": iso(utcnow()),
            "model_provider": "deterministic_fallback", "generation_status": status, "notices": notices,
            "disclaimer": i18n.msg(language, "disclaimer"), "personalisation_note": personalisation,
            "evidence": a["evidence"]}
