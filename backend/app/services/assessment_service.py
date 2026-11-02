"""Implements the L1 main pipeline (steps 1-15) and stores assessments for advisory/report reuse."""
import asyncio
import logging
import uuid
from collections import OrderedDict
from typing import Optional

from sqlalchemy import select

from ..core import i18n, monitoring
from ..core.config import get_settings
from ..core.db import session
from ..core.errors import AppError
from ..engine import risk_engine, rule_loader
from ..models.tables import Assessment
from ..schemas.common import DataQuality
from ..schemas.risk import RiskRequest
from ..utils.timeutil import iso, utcnow
from . import crop_config_service as cc, imd_service, knowledge_service, location_service, weather_service

log = logging.getLogger("farmshield.pipeline")
_memory: "OrderedDict[tuple[str, str], dict]" = OrderedDict()  # owner-scoped short-term store (E27)
MEMORY_MAX = 300


def _remember(owner_id: str, a: dict) -> None:
    key = (owner_id, a["assessment_id"])
    _memory[key] = a
    _memory.move_to_end(key)
    while len(_memory) > MEMORY_MAX:
        _memory.popitem(last=False)


def _warning_quality(resp) -> DataQuality:
    status = {"available": "fresh", "partial": "partial", "stale": "stale"}.get(resp.source_status, "unavailable")
    return DataQuality(status=status, provider="IMD", retrieved_at=resp.retrieved_at, notes=[resp.source_status_message] if resp.source_status_message else [])


async def run_assessment(req: RiskRequest, request_id: str, owner_id: str) -> dict:
    lang, _ = i18n.normalize_language(req.language)
    # 2-3. validate and resolve
    location_service.validate_coordinates(req.latitude, req.longitude)
    cfg = cc.get_crop(req.crop_id)
    stage = cc.validate_stage(cfg, req.growth_stage_id)                      # L7: never assume a stage
    if req.profile_id:
        from . import profile_service
        profile_service.get(req.profile_id, owner_id)

    # 4-5. retrieve weather and warnings concurrently; failures become explicit states
    district = req.district
    if not district and get_settings().imd_cap_feed_url:
        nd = await location_service.nearest_district(req.latitude, req.longitude)
        district = nd["district"] if nd else None

    async def _weather():
        try:
            return await weather_service.fetch_weather(req.latitude, req.longitude, req.forecast_days)
        except AppError as e:
            return e

    weather, warnings = await asyncio.gather(_weather(), imd_service.get_warnings(district))
    weather_unavailable = isinstance(weather, AppError)
    w_dict = None if weather_unavailable else weather.model_dump()
    wr_dict = warnings.model_dump()

    # 6-9. engine
    rules = rule_loader.load_rules()
    engine_out = risk_engine.assess(weather=w_dict, warnings=wr_dict, crop_cfg=cfg, stage=stage, rules=rules, language=lang)

    # 10. evidence retrieval
    triggered_cats = sorted({r["risk_category"] for r in engine_out["triggered_rules"]} | {c["category"] for c in engine_out["risk_categories"] if c["risk"] in ("moderate", "high", "critical")})
    passages = knowledge_service.retrieve_for_assessment(
        cfg["crop_id"], stage["stage_id"] if stage else None, triggered_cats, district=district)
    evidence = engine_out["evidence"] + [
        {k: v for k, v in p.items() if k in (
            "evidence_id", "kind", "title", "publisher", "publication_date", "excerpt", "source_url",
            "verification_status", "document_id", "crop_id", "growth_stage_id",
            "evidence_status", "source_access_status", "evidence_class", "state", "districts", "seasons",
            "concern", "source_section", "source_time_window", "weather_input_time_window",
            "measurement_window_status", "threshold_details", "recommendation", "limitations",
        )}
        for p in passages
    ]

    notices = list(engine_out["notices"])
    dq = {"weather": (DataQuality(status="unavailable", provider="Open-Meteo", notes=[weather.message]) if weather_unavailable else weather.data_quality),
          "warnings": _warning_quality(warnings)}
    if weather_unavailable:
        notices.append(i18n.msg(lang, "weather_down"))
    if not weather_unavailable:
        notices.append(i18n.msg(lang, "forecast_not_observation"))
        if weather.data_quality.status == "stale":
            notices.append(i18n.msg(lang, "stale_weather", age=int(weather.data_quality.age_minutes or 0)))
    if not location_service.in_pilot_region(req.latitude, req.longitude):
        notices.append(i18n.msg(lang, "outside_pilot"))
    if triggered_cats and not passages:
        notices.append(i18n.msg(lang, "no_evidence"))                          # E13: risk shown, no unsupported recommendation
    if any(p.get("verification_status") == "needs_review" for p in passages):
        notices.append(i18n.msg(lang, "unverified_evidence"))
    _, invalid_lang = i18n.normalize_language(req.language)
    if invalid_lang:
        notices.append(f"Unsupported language code; English is used. Supported: {', '.join(i18n.SUPPORTED_LANGUAGES)}.")  # E29

    daily = (w_dict or {}).get("daily") or []
    forecast_window = {"start": daily[0]["forecast_for"] if daily else None, "end": daily[-1]["forecast_for"] if daily else None}
    if weather_unavailable:
        weather_current = {"location": {"latitude": req.latitude, "longitude": req.longitude},
                           "current": None, "provider": "Open-Meteo", "retrieved_at": iso(utcnow()),
                           "data_quality": dq["weather"].model_dump()}
        weather_forecast = {"hourly": [], "daily": [], "provider": "Open-Meteo", "data_quality": dq["weather"].model_dump()}
    else:
        weather_current = {"location": {"latitude": weather.latitude, "longitude": weather.longitude,
                                        "elevation_m": weather.elevation_m, "timezone": weather.timezone,
                                        "spatial_note": weather.spatial_note},
                           "current": weather.current.model_dump() if weather.current else None, "units": weather.units,
                           "provider": weather.provider, "attribution": weather.attribution,
                           "observed_at": weather.current.observed_at if weather.current else None,
                           "retrieved_at": weather.retrieved_at, "data_quality": weather.data_quality.model_dump()}
        weather_forecast = {"hourly": [point.model_dump() for point in weather.hourly],
                            "daily": [point.model_dump() for point in weather.daily], "units": weather.units,
                            "provider": weather.provider, "attribution": weather.attribution,
                            "retrieved_at": weather.retrieved_at, "timezone": weather.timezone,
                            "data_quality": weather.data_quality.model_dump(), "spatial_note": weather.spatial_note}
    stage_name = (stage["name"].get(lang) or stage["name"]["en"]) if stage else None
    assessment_id = f"as-{uuid.uuid4().hex[:14]}"
    result = {
        "assessment_id": assessment_id, "request_id": request_id,
        "location": {"name": req.location_name or f"{req.latitude:.2f}, {req.longitude:.2f}", "latitude": req.latitude, "longitude": req.longitude, "district": district,
                     "resolution_note": "Weather is modelled on a grid; district or town centres do not represent every village."},
        "crop_id": cfg["crop_id"], "crop_name": i18n.crop_name(lang, cfg["crop_id"]), "growth_stage_id": stage["stage_id"] if stage else None,
        "growth_stage_name": stage_name, "assessment_time": iso(utcnow()), "forecast_window": forecast_window,
        **{k: engine_out[k] for k in ("overall_risk", "overall_risk_label", "risk_categories", "triggered_rules", "all_evaluations", "explanations",
                                      "recommended_actions", "timeline", "coverage", "confidence_label", "stage_specific", "rule_version")},
        "evidence": evidence, "data_quality": {k: v.model_dump() for k, v in dq.items()}, "warnings_status": warnings.source_status,
        "weather_snapshot": {"current": weather_current, "forecast": weather_forecast},
        "warnings_snapshot": wr_dict,
        "language": lang, "notices": list(dict.fromkeys(notices)), "disclaimer": i18n.msg(lang, "disclaimer"),
        "disabled_rules": engine_out["disabled_rules"],
        "method_note": "Rule-based classification from documented rules. Not a machine-learning prediction.",
    }
    # 15. persist (best effort - DB outage must not break the response, E27) + keep private inputs for re-localisation
    private = {"weather": w_dict, "warnings": wr_dict, "crop_id": cfg["crop_id"], "stage_id": result["growth_stage_id"]}
    _remember(owner_id, {**result, "_inputs": private})
    try:
        with session() as db:
            db.add(Assessment(assessment_id=assessment_id, owner_id=owner_id, request_id=request_id, profile_id=req.profile_id, crop_id=cfg["crop_id"],
                              growth_stage_id=result["growth_stage_id"], approx_lat=round(req.latitude, 1), approx_lon=round(req.longitude, 1),
                              overall_risk=result["overall_risk"], rule_version=result["rule_version"],
                              providers={"weather": dq["weather"].status, "warnings": dq["warnings"].status},
                              knowledge_document_ids=[p["document_id"] for p in passages], status="ok",
                              payload={**result, "_inputs": private}))
            db.commit()
    except Exception:
        log.exception("could not persist assessment audit record")
        monitoring.record_failure("database", "write_failed")
    return result


def get_assessment(assessment_id: str, owner_id: str) -> dict:
    key = (owner_id, assessment_id)
    if key in _memory:
        _memory.move_to_end(key)
        return _memory[key]
    try:
        with session() as db:
            row = db.scalar(select(Assessment).where(
                Assessment.assessment_id == assessment_id, Assessment.owner_id == owner_id))
            if row:
                _remember(owner_id, row.payload)
                return row.payload
    except Exception:
        log.exception("assessment lookup failed")
        raise AppError(503, "database_unavailable", "Stored data is temporarily unavailable.")      # E27: no DB details exposed
    raise AppError(404, "assessment_not_found", "Assessment not found or expired. Please run the analysis again.")


def public_view(a: dict) -> dict:
    return {k: v for k, v in a.items() if not k.startswith("_")}


def localize(stored: dict, language: str) -> dict:
    """Re-run the deterministic engine on the stored inputs in another language (same risk outcome, translated text)."""
    lang, _ = i18n.normalize_language(language)
    if lang == stored["language"]:
        return stored
    inputs = stored["_inputs"]
    cfg = cc.get_crop(inputs["crop_id"])
    stage = cc.validate_stage(cfg, inputs["stage_id"])
    out = risk_engine.assess(weather=inputs["weather"], warnings=inputs["warnings"], crop_cfg=cfg, stage=stage, rules=rule_loader.load_rules(), language=lang)
    new = dict(stored)
    new.update({k: out[k] for k in ("overall_risk_label", "risk_categories", "triggered_rules", "all_evaluations", "explanations", "recommended_actions", "timeline", "coverage")})
    new["language"] = lang
    new["crop_name"] = i18n.crop_name(lang, cfg["crop_id"])
    new["growth_stage_name"] = (stage["name"].get(lang) or stage["name"]["en"]) if stage else None
    new["disclaimer"] = i18n.msg(lang, "disclaimer")
    new["evidence"] = [e for e in stored["evidence"] if e["kind"] != "risk_rule"] + out["evidence"]
    return new
