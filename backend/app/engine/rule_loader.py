"""Loads versioned rules; unaligned measurement windows are always disabled (E11)."""
import json
import logging
import math
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Tuple

from ..core.config import BASE_DIR, get_settings

log = logging.getLogger("farmshield.rules")
RULES_DIR = BASE_DIR / "data" / "risk_rules"
REQUIRED = ["rule_id", "crop_id", "growth_stage_ids", "risk_category", "weather_variable", "comparison_operator",
            "threshold", "threshold_unit", "duration_or_window", "severity", "source_reference", "source_excerpt",
            "effective_from", "review_status", "rule_version", "source_time_window", "weather_input_time_window",
            "window_alignment_verified"]
OPERATORS = {">", ">=", "<", "<=", "between"}
SEVERITIES = {"moderate", "high", "critical"}
REVIEW = {"verified", "needs_review", "outdated"}


def validate_rule(r: dict) -> Optional[str]:
    """Returns an error string, or None when valid. A rule without a source reference is never loadable (P3)."""
    missing = [k for k in REQUIRED if k not in r]
    if missing:
        return f"missing fields {missing}"
    if r["comparison_operator"] not in OPERATORS:
        return "bad operator"
    if r["severity"] not in SEVERITIES:
        return "bad severity"
    if r["review_status"] not in REVIEW:
        return "bad review_status"
    if not isinstance(r["growth_stage_ids"], list) or not r["growth_stage_ids"] or any(not isinstance(s, str) for s in r["growth_stage_ids"]):
        return "growth_stage_ids must be a non-empty list of strings"
    window = r["duration_or_window"]
    if not isinstance(window, dict) or window.get("type") != "daily" or type(window.get("days")) is not int or window["days"] < 1:
        return "duration_or_window must specify a positive number of daily forecast days"
    if not isinstance(r["source_time_window"], str) or not r["source_time_window"].strip():
        return "source_time_window must describe the source measurement window"
    if not isinstance(r["weather_input_time_window"], str) or not r["weather_input_time_window"].strip():
        return "weather_input_time_window must describe the provider input window"
    if not isinstance(r["window_alignment_verified"], bool):
        return "window_alignment_verified must be boolean"
    sr = r["source_reference"]
    if not isinstance(sr, dict) or not sr.get("title") or not sr.get("url"):
        return "source_reference must contain title and url"
    if not r["source_excerpt"]:
        return "source_excerpt required"
    if r["comparison_operator"] == "between" and r.get("threshold_upper") is None:
        return "between requires threshold_upper"
    try:
        threshold = float(r["threshold"])
    except (TypeError, ValueError):
        return "threshold must be numeric"
    if not math.isfinite(threshold):
        return "threshold must be finite"
    if r["comparison_operator"] == "between":
        try:
            upper = float(r["threshold_upper"])
        except (TypeError, ValueError):
            return "threshold_upper must be numeric"
        if not math.isfinite(upper) or upper <= threshold:
            return "threshold_upper must be finite and greater than threshold"
    return None


@lru_cache
def _load_raw(directory: str) -> Tuple[List[dict], List[dict], str]:
    good, bad, versions = [], [], []
    for f in sorted(Path(directory).glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        versions.append(f"{data.get('ruleset_id', f.stem)}@{data.get('rule_version', '?')}")
        for r in data.get("rules", []):
            err = validate_rule(r)
            if err:
                log.error("rule %s in %s rejected: %s", r.get("rule_id"), f.name, err)
                bad.append({"rule_id": r.get("rule_id"), "file": f.name, "error": err})
            else:
                good.append(r)
    return good, bad, "+".join(versions)


def clear_cache() -> None:
    _load_raw.cache_clear()


def load_rules(directory: Optional[Path] = None) -> dict:
    d = str(directory or RULES_DIR)
    good, bad, version = _load_raw(d)
    allow = get_settings().allow_unverified_rules
    enabled, disabled = [], []
    for r in good:
        rule = {**r, "_window_compatible": (
            r["window_alignment_verified"] and r["source_time_window"] == r["weather_input_time_window"]
        )}
        (enabled if rule["_window_compatible"] and (r["review_status"] == "verified" or allow) else disabled).append(rule)
    return {"enabled": enabled, "disabled": disabled, "rejected": bad, "rule_version": version, "allow_unverified": allow}
