"""Crop configuration service (F5, F16). Crops/stages are read from versioned JSON, never hardcoded elsewhere."""
import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from ..core.config import BASE_DIR
from ..core.errors import AppError

CONFIG_DIR = BASE_DIR / "data" / "crop_configs"


@lru_cache
def load_all() -> Dict[str, dict]:
    out = {}
    for f in sorted(Path(CONFIG_DIR).glob("*.json")):
        cfg = json.loads(f.read_text(encoding="utf-8"))
        required = ("crop_id", "crop_name", "growth_stages", "configuration_version")
        missing = [k for k in required if k not in cfg]
        if missing:
            raise ValueError(f"crop config {f.name} missing {missing}")
        out[cfg["crop_id"]] = cfg
    return out


def clear_cache() -> None:
    load_all.cache_clear()


def supported_crop_ids() -> List[str]:
    return list(load_all().keys())


def get_crop(crop_id: str) -> dict:
    cfg = load_all().get(crop_id)
    if cfg is None:
        raise AppError(422, "invalid_crop", "Unsupported crop_id.", {"supported_crops": supported_crop_ids()})   # E8
    return cfg


def stage_ids(cfg: dict) -> List[str]:
    return [s["stage_id"] for s in cfg["growth_stages"]]


def validate_stage(cfg: dict, stage_id: Optional[str]) -> Optional[dict]:
    """Returns the stage dict, or None when no stage was given (L7: never assume one)."""
    if not stage_id:
        return None
    for s in cfg["growth_stages"]:
        if s["stage_id"] == stage_id:
            return s
    raise AppError(422, "invalid_growth_stage", "Unsupported growth_stage_id for this crop.",
                   {"crop_id": cfg["crop_id"], "supported_stages": stage_ids(cfg)})


def list_crops(lang: str = "en") -> List[dict]:
    res = []
    for cfg in load_all().values():
        res.append({
            "crop_id": cfg["crop_id"], "name": cfg["crop_name"], "name_i18n": cfg.get("crop_name_i18n", {}),
            "supported_stages": [{"stage_id": s["stage_id"], "order": s["order"], "name": s["name"]} for s in cfg["growth_stages"]],
            "supported_regions": cfg.get("supported_regions", []),
            "configuration_version": cfg["configuration_version"], "review_status": cfg.get("review_status"),
            "review_note": cfg.get("review_note"),
        })
    return res


def calendar_for(crop_id: str) -> dict:
    """F16: only returns calendar data when a verified reference is configured. Otherwise explicit 'unavailable'."""
    cfg = get_crop(crop_id)
    ref = cfg.get("crop_calendar_reference")
    base = {"crop_id": crop_id, "stages": [{"stage_id": s["stage_id"], "order": s["order"], "name": s["name"]} for s in cfg["growth_stages"]],
            "region": "Andhra Pradesh", "stage_catalogue_review_status": cfg.get("review_status")}
    if not ref:
        return {**base, "calendar_status": "unavailable",
                "message": "No verified regional crop calendar (sowing/harvest windows by district and season) is configured. Planting dates differ between districts and seasons; consult the local agricultural officer or ANGRAU/ICAR calendars."}
    return {**base, "calendar_status": "available", "calendar": ref}
