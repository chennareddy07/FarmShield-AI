"""Deterministic crop-risk engine (F6). The ONLY place where risk levels are computed (P2).

Pure function of (weather, warnings, crop config, stage, rules): no network, no LLM, no randomness.

Aggregation policy (spec L6, documented):
  1. per category: any triggered rule -> highest severity (critical takes precedence);
     else all enabled applicable rules evaluated and none triggered -> low;
     else (no verified/enabled rule, stage missing, or data missing) -> insufficient_data.
  2. overall: highest triggered severity across categories; low only when every required category was assessed;
     otherwise no-trigger results are insufficient_data.
  3. `coverage` always reports which categories were NOT assessed.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..core import i18n
from ..schemas.common import SEVERITY_ORDER
from ..utils.timeutil import parse_iso
from . import explainability as xp

CAP_SEVERITY = {"extreme": "critical", "severe": "high", "moderate": "moderate", "minor": "low"}
COLOR_SEVERITY = {"red": "critical", "orange": "high", "yellow": "moderate", "green": "low"}


def warning_severity(w: dict) -> Optional[str]:
    color = (w.get("severity_color") or "").strip().lower()
    if color in COLOR_SEVERITY:
        return COLOR_SEVERITY[color]
    sev = (w.get("severity") or "").strip().lower()
    if sev in COLOR_SEVERITY:
        return COLOR_SEVERITY[sev]
    return CAP_SEVERITY.get(sev)


def _compare(op: str, value: float, rule: dict) -> bool:
    t = float(rule["threshold"])
    if op == ">":
        return value > t
    if op == ">=":
        return value >= t
    if op == "<":
        return value < t
    if op == "<=":
        return value <= t
    if op == "between":
        return t <= value < float(rule["threshold_upper"])
    raise ValueError(op)


def _base_eval(rule: dict, state: str, reason: str) -> dict:
    return {"rule_id": rule["rule_id"], "risk_category": rule["risk_category"], "state": state, "severity": None,
            "weather_variable": rule["weather_variable"], "operator": rule["comparison_operator"],
            "threshold": float(rule["threshold"]), "threshold_unit": rule["threshold_unit"], "actual_value": None,
            "source_time_window": rule["source_time_window"], "weather_input_time_window": rule["weather_input_time_window"],
            "period": None, "period_start": None, "period_end": None, "reason": reason,
            "source_reference": rule["source_reference"], "evidence_id": f"EV-RULE-{rule['rule_id']}",
            "review_status": rule["review_status"], "rule_version": rule["rule_version"], "triggered_days": []}


def applicable(rule: dict, crop_id: str, stage_id: Optional[str]) -> Optional[str]:
    """Returns None when applicable, else the reason it is not."""
    if rule["crop_id"] not in ("*", crop_id):
        return "different crop"
    stages = rule["growth_stage_ids"]
    if "*" in stages:
        return None
    if stage_id is None:
        return "growth stage not selected"
    if stage_id not in stages:
        return "different growth stage"
    return None


def evaluate_rule(rule: dict, weather: Optional[dict], crop_id: str, stage_id: Optional[str], lang: str, allow_unverified: bool) -> dict:
    why = applicable(rule, crop_id, stage_id)
    if why:
        return _base_eval(rule, "not_applicable", i18n.reason(lang, "not_applicable", why=why)) | {"_na_reason": why}
    if not rule.get("_window_compatible", False):
        return _base_eval(rule, "disabled_unverified", i18n.reason(lang, "window_mismatch"))
    if rule["review_status"] != "verified" and not allow_unverified:
        return _base_eval(rule, "disabled_unverified", i18n.reason(lang, "disabled_unverified"))
    quality = (weather or {}).get("data_quality") or {}
    if quality.get("status") in ("stale", "unavailable"):
        return _base_eval(rule, "not_evaluable", i18n.reason(lang, "not_evaluable", why="weather data is stale or unavailable"))
    daily = (weather or {}).get("daily") or []
    window = rule["duration_or_window"]
    if not daily or window.get("type") != "daily":
        return _base_eval(rule, "not_evaluable", i18n.reason(lang, "not_evaluable", why="daily forecast data unavailable or unsupported window"))
    required_days = int(window.get("days", len(daily)))
    if len(daily) < required_days:
        return _base_eval(rule, "not_evaluable", i18n.reason(lang, "not_evaluable", why=f"forecast covers {len(daily)} of {required_days} required days"))
    days = daily[:required_days]
    var = rule["weather_variable"]
    present, missing = [], 0
    for d in days:
        v = d.get(var)
        if v is None:
            missing += 1                       # never treat missing as zero (L3)
        else:
            present.append((d["forecast_for"], float(v)))
    hits = [(day, v) for day, v in present if _compare(rule["comparison_operator"], v, rule)]
    if hits:
        decreasing = rule["comparison_operator"] in ("<", "<=")
        worst = min(hits, key=lambda x: x[1]) if decreasing else max(hits, key=lambda x: x[1])
        hit_days = [d for d, _ in hits]
        ev = _base_eval(rule, "triggered", "")
        ev.update(severity=rule["severity"], actual_value=worst[1], triggered_days=hit_days, period=xp.period_text(sorted(hit_days)),
                  period_start=sorted(hit_days)[0], period_end=sorted(hit_days)[-1])
        ev["reason"] = xp.triggered_reason(rule, worst[1], sorted(hit_days), lang)
        return ev
    if missing:
        return _base_eval(rule, "not_evaluable", i18n.reason(lang, "not_evaluable", why=f"{var} missing for {missing} of {len(days)} forecast days"))
    ev = _base_eval(rule, "not_triggered", i18n.reason(lang, "not_triggered", variable=i18n.variable_label(lang, var), period=xp.period_text([d for d, _ in present])))
    ev["period"] = xp.period_text([d for d, _ in present])
    return ev


def _category_from_rules(cat: str, evals: List[dict], stage_given: bool, weather_ok: bool, lang: str) -> Dict[str, Any]:
    rel = [e for e in evals if e["risk_category"] == cat]
    triggered = [e for e in rel if e["state"] == "triggered"]
    if triggered:
        top = max(triggered, key=lambda e: SEVERITY_ORDER[e["severity"]])
        return {"risk": top["severity"], "reason": top["reason"], "rule_ids": [e["rule_id"] for e in triggered], "assessed": True}
    enabled = [e for e in rel if e["state"] in ("not_triggered", "not_evaluable")]
    if enabled:
        if any(e["state"] == "not_evaluable" for e in enabled):
            return {"risk": "insufficient_data", "reason": i18n.reason(lang, "category_missing_data"), "rule_ids": [e["rule_id"] for e in enabled], "assessed": False}
        return {"risk": "low", "reason": i18n.reason(lang, "category_low"), "rule_ids": [e["rule_id"] for e in enabled], "assessed": True}
    stage_blocked = any(e["state"] == "not_applicable" and e.get("_na_reason") == "growth stage not selected" for e in rel)
    if stage_blocked and not stage_given:
        return {"risk": "insufficient_data", "reason": i18n.reason(lang, "category_stage_needed"), "rule_ids": [], "assessed": False}
    return {"risk": "insufficient_data", "reason": i18n.reason(lang, "category_no_rules"), "rule_ids": [e["rule_id"] for e in rel if e["state"] == "disabled_unverified"], "assessed": False}


def _warning_category(warnings: Optional[dict], lang: str, now: datetime) -> Dict[str, Any]:
    if not warnings or warnings.get("source_status") not in ("available", "partial"):
        return {"risk": "insufficient_data", "reason": i18n.msg(lang, "warning_unavailable"), "rule_ids": [], "assessed": False, "warnings": []}
    active = []
    for w in warnings.get("warnings", []):
        vu = parse_iso(w.get("valid_until"))
        if vu is None or vu >= now:
            active.append(w)
    if not active:
        if warnings.get("source_status") == "partial":
            return {"risk": "insufficient_data", "reason": i18n.reason(lang, "warning_partial"), "rule_ids": [], "assessed": False, "warnings": []}
        return {"risk": "low", "reason": i18n.reason(lang, "warning_none"), "rule_ids": [], "assessed": True, "warnings": []}
    sevs = [(warning_severity(w), w) for w in active]
    known = [(s, w) for s, w in sevs if s]
    if not known:
        return {"risk": "insufficient_data", "reason": "A warning exists but its severity could not be interpreted; see it as published.", "rule_ids": [], "assessed": False, "warnings": active}
    top_s, top_w = max(known, key=lambda x: SEVERITY_ORDER[x[0]])
    reason = i18n.reason(lang, "warning_present", source=top_w.get("source", "IMD"), title=top_w.get("title", ""), severity=top_w.get("severity") or top_w.get("severity_color") or "-")
    return {"risk": top_s, "reason": reason, "rule_ids": [f"WARNING:{w['warning_id']}" for _, w in known], "assessed": True, "warnings": active}


def assess(*, weather: Optional[dict], warnings: Optional[dict], crop_cfg: dict, stage: Optional[dict], rules: dict,
           language: str = "en", now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    crop_id = crop_cfg["crop_id"]
    stage_id = stage["stage_id"] if stage else None
    allow = rules.get("allow_unverified", False)
    all_rules = rules["enabled"] + rules["disabled"]
    evals = [evaluate_rule(r, weather, crop_id, stage_id, language, allow) for r in all_rules]
    rule_by_id = {r["rule_id"]: r for r in all_rules}

    categories: List[dict] = []
    warn_info = None
    for cat in crop_cfg.get("required_risk_categories", []):
        if cat == "severe_weather_warning":
            warn_info = _warning_category(warnings, language, now)
            res = warn_info
        else:
            res = _category_from_rules(cat, evals, stage is not None, bool(weather and weather.get("daily")), language)
        categories.append({"category": cat, "label": i18n.category_label(language, cat), "risk": res["risk"],
                           "risk_label": i18n.risk_label(language, res["risk"]), "reason": res["reason"], "rule_ids": res["rule_ids"],
                           "_assessed": res["assessed"]})

    assessed = [c for c in categories if c["_assessed"]]
    not_assessed = [{"category": c["category"], "label": c["label"], "reason": c["reason"]} for c in categories if not c["_assessed"]]
    triggered_cats = [c for c in assessed if c["risk"] in ("moderate", "high", "critical")]
    if triggered_cats:
        overall = max((c["risk"] for c in triggered_cats), key=lambda r: SEVERITY_ORDER[r])
    elif assessed and not not_assessed:
        overall = "low"
    else:
        overall = "insufficient_data"

    total = len(categories)
    ratio = len(assessed) / total if total else 0
    confidence = "none" if not assessed else ("limited" if ratio < 0.5 else ("partial" if ratio < 1 else "good"))
    coverage = {"assessed_count": len(assessed), "required_count": total, "not_assessed": not_assessed}

    triggered = [e for e in evals if e["state"] == "triggered"]
    triggered.sort(key=lambda e: -SEVERITY_ORDER[e["severity"]])
    explanations = [e["reason"] for e in triggered]
    if warn_info and warn_info["warnings"] and warn_info["risk"] in ("moderate", "high", "critical"):
        explanations.append(next(c["reason"] for c in categories if c["category"] == "severe_weather_warning"))
    if not explanations and overall == "low":
        explanations.append(i18n.msg(language, "none_triggered"))
    if not_assessed:
        explanations.append(i18n.msg(language, "no_rules"))

    # evidence: one entry per triggered rule (+ any warning that drove the category)
    evidence = [xp.rule_evidence(rule_by_id[e["rule_id"]]) for e in triggered]
    for w in (warn_info or {}).get("warnings", []):
        evidence.append({"evidence_id": f"EV-WARN-{w['warning_id']}", "kind": "official_warning", "title": w.get("title", ""),
                         "publisher": w.get("source"), "publication_date": w.get("issued_at"), "excerpt": w.get("description"),
                         "source_url": w.get("source_url"), "verification_status": "official"})

    actions: List[dict] = []
    seen = set()
    for e in triggered:
        act = rule_by_id[e["rule_id"]].get("recommended_action")
        if act and act.get("en_key") and act["en_key"] not in seen:
            seen.add(act["en_key"])
            actions.append({"kind": act.get("kind", "general"), "text": i18n.msg(language, act["en_key"]), "evidence_ids": [f"EV-RULE-{e['rule_id']}"], "verified": False})
    timeline = []
    for e in triggered:
        timeline += xp.timeline_events(e, language)
    timeline.sort(key=lambda t: t["start"])

    for c in categories:
        c.pop("_assessed")
    for e in evals:
        e.pop("_na_reason", None)
    public_evals = [{k: v for k, v in e.items() if k != "triggered_days"} for e in evals]
    public_trig = [{k: v for k, v in e.items() if k != "triggered_days"} for e in triggered]

    notices: List[str] = []
    if stage is None:
        notices.append(i18n.msg(language, "stage_not_selected"))
    return {
        "overall_risk": overall, "overall_risk_label": i18n.risk_label(language, overall), "risk_categories": categories,
        "triggered_rules": public_trig, "all_evaluations": public_evals, "explanations": explanations, "recommended_actions": actions,
        "evidence": evidence, "timeline": timeline, "coverage": coverage, "confidence_label": confidence,
        "stage_specific": stage is not None, "rule_version": rules["rule_version"], "notices": notices,
        "disabled_rules": [{"rule_id": r["rule_id"], "risk_category": r["risk_category"], "review_status": r["review_status"],
                            "source_time_window": r["source_time_window"], "weather_input_time_window": r["weather_input_time_window"],
                            "notes": r.get("notes")} for r in rules["disabled"]],
    }
