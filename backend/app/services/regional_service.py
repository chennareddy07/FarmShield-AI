"""F26 regional risk (district-level markers) and F29 aggregated summary. Resolution = one geocoded point per district; never finer."""
import asyncio
import time
from collections import Counter
from typing import Optional

from ..core.errors import AppError
from ..engine import risk_engine, rule_loader
from . import crop_config_service as cc, imd_service, location_service, weather_service

_cache: dict = {}
TTL = 900
RESOLUTION_NOTE = ("Each marker is one geocoded point for the district and one weather grid cell. It is NOT a district-wide measurement, and warnings are shown at district level only.")


async def _row(name: str, cfg: dict, stage, rules: dict, warnings_all, sem: asyncio.Semaphore):
    async with sem:
        try:
            c = await location_service.district_centre(name)
            if not c:
                return {"district": name, "status": "unresolved", "message": "District could not be located."}
            w = await weather_service.fetch_weather(c["latitude"], c["longitude"], 7)
            wr = None
            if warnings_all is not None:
                wr = warnings_all.model_dump()
                wr["warnings"] = [x for x in wr["warnings"] if x.get("affected_area") and name.lower() in x["affected_area"].lower()]
            out = risk_engine.assess(weather=w.model_dump(), warnings=wr, crop_cfg=cfg, stage=stage, rules=rules)
            rain_max = max((d.precipitation_sum_mm for d in w.daily if d.precipitation_sum_mm is not None), default=None)
            return {"district": name, "latitude": c["latitude"], "longitude": c["longitude"], "status": "ok", "overall_risk": out["overall_risk"],
                    "categories": {x["category"]: x["risk"] for x in out["risk_categories"]}, "triggered_rule_ids": [r["rule_id"] for r in out["triggered_rules"]],
                    "forecast_rain_max_mm": rain_max, "coverage": out["coverage"]["assessed_count"], "data_status": w.data_quality.status, "retrieved_at": w.retrieved_at}
        except Exception as e:                                                  # one district failing must not break the map
            import logging; logging.getLogger("farmshield.regional").warning("district %s failed: %s: %s", name, type(e).__name__, e)
            return {"district": name, "status": "unavailable", "message": getattr(e, "message", "Data unavailable.")}


async def regional_risk(crop_id: str, stage_id: Optional[str], use_cache: bool = True) -> dict:
    cfg = cc.get_crop(crop_id)
    stage = cc.validate_stage(cfg, stage_id)
    key = (crop_id, stage_id)
    if use_cache and key in _cache and time.monotonic() - _cache[key][0] < TTL:
        return _cache[key][1]
    rules = rule_loader.load_rules()
    wa = await imd_service.get_warnings(None)
    sem = asyncio.Semaphore(4)
    rows = await asyncio.gather(*[_row(n, cfg, stage, rules, wa if wa.source_status == "available" else None, sem) for n in location_service.districts()])
    res = {"crop_id": crop_id, "growth_stage_id": stage_id, "districts": rows, "resolution_note": RESOLUTION_NOTE, "warnings_status": wa.source_status,
           "rule_version": rules["rule_version"], "provider": "Open-Meteo", "stage_specific": stage is not None}
    _cache[key] = (time.monotonic(), res)
    return res


def summarise(region: dict) -> dict:
    rows = region["districts"]
    ok = [r for r in rows if r["status"] == "ok"]
    return {"crop_id": region["crop_id"], "districts_total": len(rows), "districts_with_data": len(ok), "districts_unavailable": len(rows) - len(ok),
            "risk_distribution": dict(Counter(r["overall_risk"] for r in ok)), "data_freshness": dict(Counter(r["data_status"] for r in ok)),
            "warnings_status": region["warnings_status"], "districts_with_triggered_rules": sorted(r["district"] for r in ok if r["triggered_rule_ids"]),
            "resolution_note": region["resolution_note"], "aggregated_only": True}


def clear_cache() -> None:
    _cache.clear()
