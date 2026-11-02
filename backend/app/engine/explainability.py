"""Builds plain-language reasons, evidence entries and the advisory timeline (F10, F12, L19)."""
from datetime import date, timedelta
from typing import List, Optional

from ..core import i18n


def condition_text(rule: dict, lang: str) -> str:
    op, unit = rule["comparison_operator"], rule["threshold_unit"]
    t = rule["threshold"]
    if op == "between":
        return i18n.reason(lang, "cond_between", lo=t, hi=rule["threshold_upper"], unit=unit)
    key = {">": "cond_gt", ">=": "cond_ge", "<": "cond_lt", "<=": "cond_le"}[op]
    return i18n.reason(lang, key, t=t, unit=unit)


def period_text(days: List[str]) -> str:
    if not days:
        return ""
    return days[0] if len(days) == 1 else f"{days[0]} -> {days[-1]}"


def triggered_reason(rule: dict, actual: float, days: List[str], lang: str) -> str:
    return i18n.reason(lang, "triggered", variable=i18n.variable_label(lang, rule["weather_variable"]), actual=round(actual, 1),
                       unit=rule["threshold_unit"], period=period_text(days), rule_id=rule["rule_id"],
                       condition=condition_text(rule, lang), source=rule["source_reference"]["title"])


def rule_evidence(rule: dict) -> dict:
    sr = rule["source_reference"]
    return {"evidence_id": f"EV-RULE-{rule['rule_id']}", "kind": "risk_rule", "title": sr["title"], "publisher": sr.get("publisher"),
            "publication_date": sr.get("publication_date"), "excerpt": rule["source_excerpt"], "source_url": sr["url"],
            "verification_status": rule["review_status"]}


def group_contiguous(days: List[str]) -> List[List[str]]:
    groups: List[List[str]] = []
    for d in sorted(days):
        cur = date.fromisoformat(d)
        if groups and date.fromisoformat(groups[-1][-1]) + timedelta(days=1) == cur:
            groups[-1].append(d)
        else:
            groups.append([d])
    return groups


def timeline_events(evaluation: dict, lang: str) -> List[dict]:
    """One timeline event per contiguous run of triggered days."""
    ev = []
    for run in group_contiguous(evaluation.get("triggered_days", [])):
        ev.append({"rule_id": evaluation["rule_id"], "category": evaluation["risk_category"], "start": run[0], "end": run[-1],
                   "severity": evaluation["severity"], "actual_value": evaluation.get("actual_value"),
                   "unit": evaluation.get("threshold_unit"),
                   "label": i18n.variable_label(lang, evaluation["weather_variable"])})
    return ev
