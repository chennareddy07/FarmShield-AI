"""F22 NDVI via the ORNL DAAC MODIS subset REST service (MOD13Q1, 250 m, 16-day). UNVERIFIED endpoint: see specs/external-verification.md.
Never fabricates indicators; limits are attached to every result."""
from datetime import date, datetime, timedelta
from typing import Optional

from ..core import monitoring
from ..core.config import get_settings
from ..core.errors import AppError
from ..core.http import ProviderError, request_json
from ..utils.timeutil import iso, utcnow

LIMITS = ["MODIS NDVI at 250 m resolution is a 16-day composite and may mix fields, roads and trees.",
          "Cloud/quality filtering is applied by the provider's composite; quality flags are not individually interpreted here.",
          "NDVI alone cannot identify a crop disease or predict yield."]
SCALE = 0.0001


def modis_date(d: date) -> str:
    return f"A{d.year}{d.timetuple().tm_yday:03d}"


def parse_modis_date(s: str) -> str:
    return datetime.strptime(s[1:], "%Y%j").date().isoformat()


def normalise(raw: dict) -> list:
    out = []
    for item in raw.get("subset", []):
        if item.get("band", "").endswith("NDVI") and item.get("data"):
            v = item["data"][0]
            if v is None or v == -3000:                                       # fill value
                continue
            out.append({"date": item.get("calendar_date") or parse_modis_date(item["modis_date"]), "ndvi": round(v * SCALE, 4)})
    return out


async def get_indicators(lat: float, lon: float, days: int = 120) -> dict:
    s = get_settings()
    base = {"indicators": [], "provider": "NASA MODIS MOD13Q1 via ORNL DAAC", "spatial_resolution": "250 m", "temporal_resolution": "16-day composite",
            "quality_notes": LIMITS, "retrieved_at": iso(utcnow())}
    if s.satellite_provider == "disabled":
        return {**base, "status": "not_configured", "message": "Satellite module disabled by configuration."}
    end = date.today()
    params = {"latitude": lat, "longitude": lon, "band": "250m_16_days_NDVI", "startDate": modis_date(end - timedelta(days=days)), "endDate": modis_date(end), "kmAboveBelow": 0, "kmLeftRight": 0}
    try:
        raw = await request_json("modis", "GET", f"{s.modis_base_url.rstrip('/')}/MOD13Q1/subset", params=params, headers={"Accept": "application/json"})
        monitoring.record_success("satellite")
    except ProviderError as e:
        monitoring.record_failure("satellite", e.kind)
        return {**base, "status": "unavailable", "message": "Satellite data is unavailable. No vegetation indicator is shown."}   # E25
    ind = normalise(raw)
    if not ind:
        return {**base, "status": "empty", "message": "The provider returned no valid vegetation observations for this location and period."}
    return {**base, "indicators": ind, "observation_date": ind[-1]["date"], "status": "available", "message": None}
