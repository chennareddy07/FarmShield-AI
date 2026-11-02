"""Location resolution (F1, F17). Uses Open-Meteo geocoding; district names come from config, coordinates from the geocoder."""
import json
import logging
import math
from typing import Dict, List, Optional

from ..core import monitoring
from ..core.config import BASE_DIR, get_settings
from ..core.errors import AppError
from ..core.http import ProviderError, request_json
from ..schemas.location import LocationResult

log = logging.getLogger("farmshield.location")
PROVIDER = "Open-Meteo Geocoding"
REGION_FILE = BASE_DIR / "data" / "regions" / "andhra_pradesh.json"
# Approximate bounding box of Andhra Pradesh, used ONLY to add a "outside pilot region" notice (not for resolution).
AP_BBOX = {"lat": (12.6, 19.95), "lon": (76.7, 84.8)}
_district_cache: Dict[str, Optional[dict]] = {}


def load_region() -> dict:
    return json.loads(REGION_FILE.read_text(encoding="utf-8"))


def districts() -> List[str]:
    return load_region()["districts"]


def clear_cache() -> None:
    _district_cache.clear()


def validate_coordinates(lat: float, lon: float) -> None:
    if not (isinstance(lat, (int, float)) and isinstance(lon, (int, float))) or math.isnan(lat) or math.isnan(lon):
        raise AppError(422, "invalid_coordinates", "Latitude and longitude must be numbers.")
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise AppError(422, "invalid_coordinates", "Latitude must be within -90..90 and longitude within -180..180.")      # E2


def in_pilot_region(lat: float, lon: float) -> bool:
    return AP_BBOX["lat"][0] <= lat <= AP_BBOX["lat"][1] and AP_BBOX["lon"][0] <= lon <= AP_BBOX["lon"][1]


def _to_result(r: dict) -> LocationResult:
    return LocationResult(location_id=f"om-{r.get('id', 'x')}", name=r.get("name", ""), district=r.get("admin2") or None,
                          state=r.get("admin1"), latitude=r["latitude"], longitude=r["longitude"], source="search")


async def _geocode(name: str, count: int = 10) -> List[dict]:
    s = get_settings()
    try:
        data = await request_json(PROVIDER, "GET", f"{s.open_meteo_geocoding_url.rstrip('/')}/v1/search",
                                  params={"name": name, "count": count, "language": "en", "format": "json", "countryCode": "IN"})
        monitoring.record_success("geocoding")
    except ProviderError as e:
        monitoring.record_failure("geocoding", e.kind)
        raise AppError(e.http_status, "geocoding_unavailable", "Location search is currently unavailable. Please try again later.", {"provider": PROVIDER, "kind": e.kind})
    return data.get("results") or []


async def search(q: Optional[str]) -> dict:
    if q is None or not q.strip():
        raise AppError(422, "empty_location", "Please enter or select a location.")                   # E1
    q = q.strip()
    if len(q) < 2 or len(q) > 100:
        raise AppError(422, "invalid_location_query", "Location query must be 2-100 characters.")
    raw = await _geocode(q)
    results = [_to_result(r) for r in raw if (r.get("admin1") or "").lower() == "andhra pradesh"]
    note = None
    if not results:
        note = "No supported Andhra Pradesh location matched. Try a broader name, such as the district or nearest town."   # E3
    return {"results": [r.model_dump() for r in results], "query": q, "message": note, "supported_state": "Andhra Pradesh"}


async def district_centre(name: str) -> Optional[dict]:
    """Resolve a configured district name to a point (cached). Returned as an approximate district-level point."""
    if name in _district_cache:
        return _district_cache[name]
    raw = await _geocode(name, count=10)
    hit = next((r for r in raw if (r.get("admin1") or "").lower() == "andhra pradesh"), None)
    res = {"district": name, "latitude": hit["latitude"], "longitude": hit["longitude"], "matched_name": hit.get("name")} if hit else None
    _district_cache[name] = res
    return res


def _haversine(a_lat, a_lon, b_lat, b_lon) -> float:
    p = math.pi / 180
    x = math.sin((b_lat - a_lat) * p / 2) ** 2 + math.cos(a_lat * p) * math.cos(b_lat * p) * math.sin((b_lon - a_lon) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))


async def nearest_district(lat: float, lon: float) -> Optional[dict]:
    """Approximate district for browser-geolocation (no reverse geocoder available). Uses cached district centre points."""
    best = None
    for name in districts():
        try:
            c = await district_centre(name)
        except AppError:
            return None
        if c:
            d = _haversine(lat, lon, c["latitude"], c["longitude"])
            if best is None or d < best[0]:
                best = (d, name)
    return {"district": best[1], "distance_km": round(best[0], 1), "approximate": True} if best else None
