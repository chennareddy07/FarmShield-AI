from typing import Optional

from fastapi import APIRouter, Query

from ...core.errors import AppError
from ...services import crop_config_service as cc, history_service, imd_service, knowledge_service, location_service, weather_service

router = APIRouter()
Lat = Query(..., ge=-90, le=90)
Lon = Query(..., ge=-180, le=180)


@router.get("/api/locations/search")
async def search_locations(q: Optional[str] = Query(default=None)):
    return await location_service.search(q)


@router.get("/api/locations/nearest-district")
async def nearest(latitude: float = Lat, longitude: float = Lon):
    return {"result": await location_service.nearest_district(latitude, longitude), "note": "Approximate: nearest configured district centre."}


@router.get("/api/crops")
async def crops():
    return {"crops": cc.list_crops()}


@router.get("/api/crops/{crop_id}/calendar")
async def crop_calendar(crop_id: str):
    return cc.calendar_for(crop_id)


@router.get("/api/weather/current")
async def weather_current(latitude: float = Lat, longitude: float = Lon):
    b = await weather_service.fetch_weather(latitude, longitude, 7)
    return {"location": {"latitude": b.latitude, "longitude": b.longitude, "elevation_m": b.elevation_m, "timezone": b.timezone, "spatial_note": b.spatial_note},
            "current": b.current, "units": b.units, "provider": b.provider, "attribution": b.attribution,
            "observed_at": b.current.observed_at if b.current else None, "retrieved_at": b.retrieved_at, "data_quality": b.data_quality}


@router.get("/api/weather/forecast")
async def weather_forecast(latitude: float = Lat, longitude: float = Lon, days: int = Query(default=7, ge=1, le=16)):
    b = await weather_service.fetch_weather(latitude, longitude, days)
    return {"hourly": b.hourly, "daily": b.daily, "units": b.units, "provider": b.provider, "attribution": b.attribution, "retrieved_at": b.retrieved_at,
            "timezone": b.timezone, "data_quality": b.data_quality, "spatial_note": b.spatial_note}


@router.get("/api/warnings")
async def warnings(district: Optional[str] = None):
    return await imd_service.get_warnings(district)


@router.get("/api/history")
async def history(latitude: float = Lat, longitude: float = Lon, start_date: str = Query(...), end_date: str = Query(...)):
    return await history_service.fetch_history(latitude, longitude, start_date, end_date)


@router.get("/api/history/seasonal")
async def history_seasonal(latitude: float = Lat, longitude: float = Lon, start_month: int = Query(default=6), end_month: int = Query(default=9), baseline_years: int = Query(default=10)):
    return await history_service.fetch_seasonal(latitude, longitude, start_month, end_month, baseline_years)


@router.get("/api/knowledge/search")
async def knowledge_search(
    q: str = Query(default="", max_length=200),
    crop_id: Optional[str] = Query(default=None, max_length=40),
    growth_stage_id: Optional[str] = Query(default=None, max_length=60),
    topic: Optional[str] = Query(default=None, max_length=80),
    state: Optional[str] = Query(default=None, max_length=40),
    district: Optional[str] = Query(default=None, max_length=80),
    season: Optional[str] = Query(default=None, max_length=20),
    concern: Optional[str] = Query(default=None, max_length=80),
    evidence_status: Optional[str] = Query(default=None, max_length=32),
    limit: int = Query(default=8, ge=1, le=20),
):
    if crop_id:
        cc.get_crop(crop_id)
    res = knowledge_service.search(q, crop_id=crop_id, stage_id=growth_stage_id, topics=[topic] if topic else None,
                                   state=state, district=district, season=season, concern=concern,
                                   evidence_status=evidence_status, limit=limit)
    return {"results": res, "count": len(res), "message": None if res else "No matching verified or reviewable material was found."}


@router.get("/api/knowledge/documents")
async def knowledge_documents(
    crop_id: Optional[str] = Query(default=None, max_length=40),
    topic: Optional[str] = Query(default=None, max_length=80),
    growth_stage_id: Optional[str] = Query(default=None, max_length=60),
    state: Optional[str] = Query(default=None, max_length=40),
    district: Optional[str] = Query(default=None, max_length=80),
    season: Optional[str] = Query(default=None, max_length=20),
    concern: Optional[str] = Query(default=None, max_length=80),
    evidence_status: Optional[str] = Query(default=None, max_length=32),
):
    if crop_id:
        cc.get_crop(crop_id)
    return {"documents": knowledge_service.list_documents(
        crop_id, topic, growth_stage_id, state=state, district=district, season=season,
        concern=concern, evidence_status=evidence_status)}


@router.get("/api/knowledge/evidence-registry")
async def knowledge_evidence_registry(crop_id: Optional[str] = Query(default=None, max_length=40)):
    if crop_id:
        cc.get_crop(crop_id)
    return knowledge_service.load_evidence_registry(crop_id)
