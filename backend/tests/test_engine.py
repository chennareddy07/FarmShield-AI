import copy
import json
from datetime import datetime, timezone

import pytest

from app.core.errors import AppError
from app.engine import risk_engine as eng, rule_loader
from app.services import crop_config_service as cc

NOW = datetime(2026, 11, 1, tzinfo=timezone.utc)


def day(d, rain=0.0, tmax=30.0):
    return {"forecast_for": d, "precipitation_sum_mm": rain, "temperature_max_c": tmax, "temperature_min_c": 22.0}


def weather(rains=None, tmaxs=None, n=7, quality=None):
    rains = rains or [0.0] * n
    tmaxs = tmaxs or [30.0] * n
    out = {"daily": [day(f"2026-11-{i + 1:02d}", rains[i], tmaxs[i]) for i in range(n)]}
    if quality:
        out["data_quality"] = quality
    return out


def verified_test_rules(**overrides):
    rule = {"rule_id": "TEST-DAILY-RAIN", "crop_id": "*", "growth_stage_ids": ["*"], "risk_category": "rainfall",
            "weather_variable": "precipitation_sum_mm", "comparison_operator": ">=", "threshold": 10.0,
            "threshold_unit": "mm", "duration_or_window": {"type": "daily", "days": 2}, "severity": "high",
            "source_reference": {"title": "Test fixture", "url": "https://example.test/rule"},
            "source_excerpt": "Test fixture, not agricultural guidance.", "review_status": "verified",
            "rule_version": "test", "source_time_window": "two local calendar days",
            "weather_input_time_window": "two local calendar days", "window_alignment_verified": True,
            "_window_compatible": True, "recommended_action": None}
    rule.update(overrides)
    return {"enabled": [rule], "disabled": [], "rejected": [], "rule_version": "test", "allow_unverified": False}


def run(w, crop="paddy", stage="flowering", warnings=None, rules=None, lang="en"):
    cfg = cc.get_crop(crop)
    return eng.assess(weather=w, warnings=warnings, crop_cfg=cfg, stage=cc.validate_stage(cfg, stage), rules=rules or rule_loader.load_rules(), language=lang, now=NOW)


def cat(out, name):
    return next(c for c in out["risk_categories"] if c["category"] == name)


# ---------- Crop configuration (F5, AC7, E8) ----------
def test_crops_have_distinct_stage_catalogues(client):
    crops = {c["crop_id"]: c for c in client.get("/api/crops").json()["crops"]}
    assert set(crops) == {"paddy", "groundnut"}
    p = {s["stage_id"] for s in crops["paddy"]["supported_stages"]}
    g = {s["stage_id"] for s in crops["groundnut"]["supported_stages"]}
    assert p != g and "pegging" in g and "pegging" not in p


def test_invalid_crop_lists_supported(client):
    r = client.post("/api/risk/assess", json={"latitude": 16, "longitude": 80, "crop_id": "wheat"})
    assert r.status_code == 422 and r.json()["details"]["supported_crops"] == ["groundnut", "paddy"]


def test_invalid_stage_rejected(client):
    r = client.post("/api/risk/assess", json={"latitude": 16, "longitude": 80, "crop_id": "paddy", "growth_stage_id": "pegging"})
    assert r.status_code == 422 and "supported_stages" in r.json()["details"]


def test_calendar_unavailable_without_verified_source(client):
    r = client.get("/api/crops/paddy/calendar").json()
    assert r["calendar_status"] == "unavailable" and len(r["stages"]) == 7


# ---------- Rule loading (E11) ----------
def test_rule_without_source_is_rejected():
    r = {"rule_id": "X", "crop_id": "*", "growth_stage_ids": ["*"], "risk_category": "rainfall", "weather_variable": "precipitation_sum_mm", "comparison_operator": ">",
         "threshold": 1, "threshold_unit": "mm", "duration_or_window": {"type": "daily", "days": 1}, "severity": "high", "source_reference": {}, "source_excerpt": "", "effective_from": "x",
         "review_status": "verified", "rule_version": "1", "source_time_window": "test window",
         "weather_input_time_window": "test window", "window_alignment_verified": True}
    assert "source_reference" in rule_loader.validate_rule(r)


@pytest.mark.parametrize("field,value", [
    ("growth_stage_ids", []),
    ("duration_or_window", {"type": "daily", "days": 0}),
    ("threshold", float("inf")),
    ("threshold_upper", 0.5),
])
def test_malformed_rule_dimensions_are_rejected(field, value):
    r = verified_test_rules()["enabled"][0] | {"comparison_operator": "between", "threshold_upper": 2.0}
    r[field] = value
    assert rule_loader.validate_rule(r)


def test_shipped_rules_are_disabled_until_measurement_windows_are_verified():
    rules = rule_loader.load_rules()
    assert not rules["enabled"] and len(rules["disabled"]) == 5 and not rules["rejected"]
    assert all(not r["_window_compatible"] for r in rules["disabled"])
    assert all(r["source_time_window"] != r["weather_input_time_window"] for r in rules["disabled"])
    assert all(r["review_status"] == "needs_review" for r in rules["disabled"])


def test_all_shipped_rules_have_sources():
    for r in rule_loader.load_rules()["enabled"] + rule_loader.load_rules()["disabled"]:
        assert r["source_reference"]["url"].startswith("http") and r["source_excerpt"]


def test_unverified_rules_stay_disabled_even_when_override_is_enabled(monkeypatch):
    w = weather(tmaxs=[30, 30, 37, 30, 30, 30, 30])
    out = run(w)
    assert cat(out, "high_temperature")["risk"] == "insufficient_data"
    assert not any(e["state"] == "triggered" for e in out["all_evaluations"])
    assert any(e["state"] == "disabled_unverified" for e in out["all_evaluations"])
    monkeypatch.setenv("ALLOW_UNVERIFIED_RULES", "true")
    from app.core.config import get_settings
    get_settings.cache_clear(); rule_loader.clear_cache()
    out2 = run(w, rules=rule_loader.load_rules())
    assert cat(out2, "high_temperature")["risk"] == "insufficient_data" and not out2["triggered_rules"]


# ---------- Applicability (L5, Scenario 2) ----------
def test_groundnut_does_not_reuse_paddy_rule(monkeypatch):
    monkeypatch.setenv("ALLOW_UNVERIFIED_RULES", "true")
    from app.core.config import get_settings
    get_settings.cache_clear(); rule_loader.clear_cache()
    rules = rule_loader.load_rules()
    w = weather(tmaxs=[36.0] * 7)
    g = run(w, "groundnut", "flowering", rules=rules)
    assert not g["triggered_rules"]
    g2 = run(w, "groundnut", "vegetative", rules=rules)        # stage-specific rule not applicable
    assert not g2["triggered_rules"]
    p = run(w, "paddy", "tillering", rules=rules)
    assert not p["triggered_rules"]


def test_missing_stage_gives_general_assessment():
    out = run(weather(tmaxs=[37] * 7), stage=None)
    assert out["stage_specific"] is False and out["notices"]
    assert cat(out, "high_temperature")["risk"] == "insufficient_data"


# ---------- Thresholds, aggregation, insufficient data (AC8-AC10, E10) ----------
def test_weather_amount_classes_do_not_become_crop_risk_without_aligned_rules():
    out = run(weather(rains=[0, 250, 0, 0, 0, 0, 0]))
    assert out["overall_risk"] == "insufficient_data"
    assert cat(out, "rainfall")["risk"] == "insufficient_data"
    assert not out["triggered_rules"]


def test_no_trigger_with_incomplete_category_coverage_is_insufficient():
    out = run(weather())
    assert out["overall_risk"] == "insufficient_data" and out["coverage"]["assessed_count"] < out["coverage"]["required_count"]
    assert out["confidence_label"] == "none" and out["coverage"]["not_assessed"]


def test_no_weather_and_no_warnings_is_insufficient():
    out = run(None)
    assert out["overall_risk"] == "insufficient_data" and out["confidence_label"] == "none"


def test_missing_rain_days_are_not_evaluable_not_zero():
    w = weather()
    w["daily"][3]["precipitation_sum_mm"] = None
    out = run(w)
    assert cat(out, "rainfall")["risk"] == "insufficient_data"
    assert all(e["state"] == "disabled_unverified" for e in out["all_evaluations"] if e["rule_id"].startswith("IMD"))


def test_missing_data_does_not_hide_a_trigger():
    w = weather(rains=[0, 130, 0, 0, 0, 0, 0])
    w["daily"][3]["precipitation_sum_mm"] = None
    assert run(w)["overall_risk"] == "insufficient_data"


def test_verified_test_rule_requires_fresh_complete_forecast():
    stale = weather(quality={"status": "stale"})
    out = run(stale, rules=verified_test_rules())
    assert out["all_evaluations"][0]["state"] == "not_evaluable"
    short = run(weather(n=1), rules=verified_test_rules())
    assert short["all_evaluations"][0]["state"] == "not_evaluable"
    missing = weather(n=2)
    missing["daily"][1]["precipitation_sum_mm"] = None
    assert run(missing, rules=verified_test_rules())["all_evaluations"][0]["state"] == "not_evaluable"


def test_verified_test_rule_trigger_remains_visible_with_other_categories_unassessed():
    out = run(weather(rains=[10, 0, 0, 0, 0, 0, 0]), rules=verified_test_rules())
    assert out["overall_risk"] == "high"
    assert cat(out, "rainfall")["risk"] == "high"
    assert out["coverage"]["not_assessed"]


def test_category_without_verified_rule_is_insufficient_not_invented():        # AC9
    out = run(weather())
    for c in ("dry_spell", "excess_rainfall", "wind", "humidity", "low_temperature"):
        assert cat(out, c)["risk"] == "insufficient_data"


# ---------- Explainability (AC15, F12) ----------
def test_triggered_rule_explanation_fields():
    out = run(weather(rains=[10, 0, 0, 0, 0, 0, 0]), rules=verified_test_rules())
    t = out["triggered_rules"][0]
    for k in ("rule_id", "weather_variable", "threshold", "actual_value", "severity", "period", "source_reference", "reason", "evidence_id",
              "source_time_window", "weather_input_time_window"):
        assert t[k] is not None
    assert t["actual_value"] == 10 and t["period"] == "2026-11-01" and t["source_reference"]["url"].startswith("https://")
    assert out["timeline"][0]["start"] == "2026-11-01" and out["timeline"][0]["end"] == "2026-11-01"
    assert out["evidence"][0]["evidence_id"] == "EV-RULE-TEST-DAILY-RAIN"


def test_actions_are_general_only_never_chemical():
    out = run(weather(rains=[0, 0, 130, 0, 0, 0, 0]))
    assert out["recommended_actions"] == []


def test_telugu_output_preserves_numbers_and_urls():
    en = run(weather(rains=[130, 0, 0, 0, 0, 0, 0]), rules=verified_test_rules())
    te = run(weather(rains=[130, 0, 0, 0, 0, 0, 0]), rules=verified_test_rules(), lang="te")
    assert te["overall_risk"] == en["overall_risk"] and te["risk_categories"][0]["label"] != en["risk_categories"][0]["label"]
    assert "130.0" in te["triggered_rules"][0]["reason"] and te["triggered_rules"][0]["source_reference"]["url"] == en["triggered_rules"][0]["source_reference"]["url"]


# ---------- Official warnings category ----------
def wr(status="available", **w):
    base = {"warning_id": "w1", "source": "IMD", "title": "Heavy rain", "severity": "Severe", "valid_until": "2026-11-05T00:00:00+00:00"}
    base.update(w)
    return {"source_status": status, "warnings": [base] if status == "available" and w is not None else []}


@pytest.mark.parametrize("kw,expected", [({"severity_color": "Red"}, "critical"), ({"severity_color": "orange"}, "high"), ({"severity_color": "Yellow"}, "moderate"),
                                         ({"severity": "Extreme"}, "critical"), ({"severity": "Severe"}, "high"), ({"severity": "Moderate"}, "moderate")])
def test_warning_severity_mapping(kw, expected):
    d = {"severity": None, "severity_color": None}
    d.update(kw)
    out = run(weather(), warnings=wr(**d))
    assert cat(out, "severe_weather_warning")["risk"] == expected and out["overall_risk"] == expected
    assert any(e["kind"] == "official_warning" for e in out["evidence"])


def test_unrecognised_warning_severity_not_guessed():
    out = run(weather(), warnings=wr(severity="Weird", severity_color=None))
    assert cat(out, "severe_weather_warning")["risk"] == "insufficient_data"


def test_partial_warning_feed_without_active_entries_is_insufficient():
    out = run(weather(), warnings={"source_status": "partial", "warnings": []})
    result = cat(out, "severe_weather_warning")
    assert result["risk"] == "insufficient_data" and "incomplete" in result["reason"]


def test_expired_warning_ignored_and_none_is_low():
    out = run(weather(), warnings=wr(valid_until="2026-10-01T00:00:00+00:00", severity_color="red"))
    assert cat(out, "severe_weather_warning")["risk"] == "low"


@pytest.mark.parametrize("status", ["unavailable", "not_configured"])
def test_warning_source_unavailable_never_generates_warning(status):
    out = run(weather(), warnings={"source_status": status, "warnings": []})
    assert cat(out, "severe_weather_warning")["risk"] == "insufficient_data" and not any(e["kind"] == "official_warning" for e in out["evidence"])


def test_engine_is_deterministic():
    w = weather(rains=[0, 90, 0, 0, 0, 0, 0])
    assert json.dumps(run(w), sort_keys=True, default=str) == json.dumps(run(w), sort_keys=True, default=str)
