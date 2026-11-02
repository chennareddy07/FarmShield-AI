from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from pydantic import BaseModel, Field

from ...core.config import get_settings
from ...core.errors import AppError
from ..deps import current_owner_id, require_admin
from ...services import crop_config_service as cc, image_service, market_service, notification_service, profile_service, regional_service, satellite_service, voice_service

router = APIRouter()


# ---- F13 profile ----
class ProfileIn(BaseModel):
    nickname: Optional[str] = Field(default=None, max_length=80)
    preferred_location: Optional[dict] = None
    preferred_crop: Optional[str] = None
    preferred_growth_stage: Optional[str] = None
    farm_area: Optional[float] = Field(default=None, gt=0, le=100000)
    farm_area_unit: Optional[str] = Field(default=None, pattern="^(acre|hectare)$")
    language: str = "en"
    notification_preferences: Optional[dict] = None


@router.post("/api/profile", status_code=201)
async def profile_create(p: ProfileIn, owner_id: str = Depends(current_owner_id)):
    return profile_service.create(p.model_dump(), owner_id)


@router.get("/api/profile/{profile_id}")
async def profile_get(profile_id: str, owner_id: str = Depends(current_owner_id)):
    return profile_service.get(profile_id, owner_id)


@router.put("/api/profile/{profile_id}")
async def profile_update(profile_id: str, p: ProfileIn, owner_id: str = Depends(current_owner_id)):
    return profile_service.update(profile_id, p.model_dump(exclude_unset=True), owner_id)


@router.delete("/api/profile/{profile_id}")
async def profile_delete(profile_id: str, owner_id: str = Depends(current_owner_id)):
    if not profile_service.delete_profile(profile_id, owner_id):
        raise AppError(404, "profile_not_found", "Profile not found.")
    return {"deleted": True}


# ---- F19 market ----
class MarketAdviceIn(BaseModel):
    state: str = Field(..., min_length=2, max_length=100)
    district: Optional[str] = Field(default=None, max_length=100)
    commodity: str = Field(..., min_length=1, max_length=120)
    language: str = Field(default="en", max_length=8)
    question: Optional[str] = Field(default=None, max_length=300)


@router.get("/api/market/options")
async def market_options(state: Optional[str] = Query(None, max_length=100),
                         district: Optional[str] = Query(None, max_length=100)):
    return await market_service.get_options(state, district)


@router.get("/api/market/prices")
async def market_prices(crop_id: Optional[str] = None, commodity: Optional[str] = Query(None, max_length=120),
                        state: Optional[str] = Query(None, max_length=100),
                        district: Optional[str] = Query(None, max_length=100),
                        market_id: Optional[str] = Query(None, max_length=120),
                        limit: int = Query(100, ge=1, le=500)):
    return await market_service.get_prices(crop_id, district, market_id, limit, state, commodity)


@router.post("/api/market/advice")
async def market_advice(request: MarketAdviceIn):
    return await market_service.get_sale_advice(
        request.state, request.commodity, request.district, request.language, request.question,
    )


# ---- F20 crop health ----
@router.post("/api/crop-health/analyze")
async def crop_health(image: UploadFile = File(...), crop_id: Optional[str] = Form(None), growth_stage_id: Optional[str] = Form(None),
                      symptoms_description: Optional[str] = Form(None), language: str = Form("en"), consent: bool = Form(False)):
    limit = get_settings().max_image_bytes
    data = await image.read(limit + 1)
    if crop_id:
        cc.validate_stage(cc.get_crop(crop_id), growth_stage_id)
    return await image_service.analyze(data, image.content_type, consent, crop_id, growth_stage_id, (symptoms_description or "")[:500], language)


# ---- F21 notifications ----
class PrefsIn(BaseModel):
    location: dict
    crop_id: str
    growth_stage_id: Optional[str] = None
    enabled: bool = False
    consent: bool = False
    channels: list = ["in_app"]
    risk_levels: list = ["high", "critical"]
    warning_categories: list = []
    quiet_hours: Optional[dict] = None


@router.get("/api/notifications")
async def notifications(owner_id: str = Depends(current_owner_id)):
    return notification_service.list_notifications(owner_id)


@router.post("/api/notifications/preferences")
async def notifications_prefs(p: PrefsIn, owner_id: str = Depends(current_owner_id)):
    return notification_service.save_preferences({**p.model_dump(), "user_id": owner_id})


@router.get("/api/notifications/preferences")
async def notifications_prefs_get(owner_id: str = Depends(current_owner_id)):
    return {"subscriptions": notification_service.get_preferences(owner_id)}


@router.post("/api/notifications/refresh")
async def notifications_refresh(owner_id: str = Depends(current_owner_id)):
    return {"created": await notification_service.refresh_for_user(owner_id)}


@router.post("/api/notifications/{notification_id}/read")
async def notifications_read(notification_id: str, owner_id: str = Depends(current_owner_id)):
    if not notification_service.mark_read(owner_id, notification_id):
        raise AppError(404, "notification_not_found", "Notification not found.")
    return {"read": True}


# ---- F22 satellite ----
@router.get("/api/satellite/indicators")
async def satellite(latitude: float = Query(..., ge=-90, le=90), longitude: float = Query(..., ge=-180, le=180)):
    return await satellite_service.get_indicators(latitude, longitude)


# ---- F23 voice ----
@router.post("/api/voice/transcribe")
async def voice(audio: UploadFile = File(...), language: Optional[str] = Form(None)):
    data = await audio.read(10 * 1024 * 1024 + 1)
    return await voice_service.transcribe(data, audio.content_type, language)


# ---- F26 / F29 ----
@router.get("/api/regional/risk")
async def regional(crop_id: str = Query(...), growth_stage_id: Optional[str] = None):
    return await regional_service.regional_risk(crop_id, growth_stage_id)


@router.get("/api/admin/regional-summary", dependencies=[Depends(require_admin)])
async def admin_summary(crop_id: str = Query(...), growth_stage_id: Optional[str] = None):
    return regional_service.summarise(await regional_service.regional_risk(crop_id, growth_stage_id))
