from datetime import datetime, timezone

from fastapi import APIRouter, Query
from fastapi import Depends, Request

from ...core import i18n, monitoring
from ...core.config import get_settings
from ...core.db import db_ok
from ...core.modules import modules
from ...services import location_service
from ..deps import current_owner_id

router = APIRouter()


@router.get("/api/health")
async def health():
    s = get_settings()
    db = db_ok()
    services = {
        "database": "available" if db else "unavailable",
        "weather_provider": monitoring.status_for("weather"),
        "geocoding_provider": monitoring.status_for("geocoding"),
        "official_warnings": "not_configured" if not s.imd_cap_feed_url else monitoring.status_for("imd"),
        "llm": s.llm_status,
    }
    return {"status": "ok" if db else "degraded", "timestamp": datetime.now(timezone.utc).isoformat(), "services": services}


@router.get("/api/session")
async def session_bootstrap(request: Request):
    current_owner_id(request)
    s = get_settings()
    return {"mode": "anonymous", "persistent": bool(s.secret("session_secret"))}


@router.get("/api/meta/modules")
async def meta_modules():
    return {"modules": modules()}


@router.get("/api/meta/languages")
async def meta_languages():
    return {"languages": [{"code": c, "review_status": i18n.TRANSLATION_REVIEW_STATUS[c]} for c in i18n.SUPPORTED_LANGUAGES], "default": "en",
            "planned": ["hi", "ta", "kn", "ml"]}


@router.get("/api/regions")
async def regions():
    r = location_service.load_region()
    return {"state": r["state"], "districts": r["districts"], "review_status": r["review_status"], "review_note": r["review_note"]}


@router.get("/api/monitoring/status")
async def monitoring_status():
    s = get_settings()
    return {"providers": monitoring.snapshot(), "freshness_policy": {"weather_fresh_minutes": s.weather_fresh_minutes, "weather_stale_minutes": s.weather_stale_minutes, "imd_fresh_minutes": s.imd_fresh_minutes},
            "timestamp": datetime.now(timezone.utc).isoformat()}
