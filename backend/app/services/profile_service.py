"""Opt-in farmer profiles (F13). No sensitive data is required; deletion is supported."""
import uuid
from typing import Optional

from sqlalchemy import delete, select

from ..core import i18n
from ..core.db import session
from ..core.errors import AppError
from ..models.tables import Profile
from . import crop_config_service as cc


def _dict(p: Profile) -> dict:
    return {"profile_id": p.profile_id, "nickname": p.nickname, "preferred_location": p.preferred_location, "preferred_crop": p.preferred_crop,
            "preferred_growth_stage": p.preferred_growth_stage, "farm_area": p.farm_area, "farm_area_unit": p.farm_area_unit, "language": p.language,
            "notification_preferences": p.notification_preferences, "created_at": p.created_at.isoformat(), "updated_at": p.updated_at.isoformat()}


def _validate(data: dict) -> dict:
    out = dict(data)
    if out.get("preferred_crop"):
        cfg = cc.get_crop(out["preferred_crop"])
        cc.validate_stage(cfg, out.get("preferred_growth_stage"))
    lang, bad = i18n.normalize_language(out.get("language", "en"))
    if bad:
        raise AppError(422, "invalid_language", "Unsupported language.", {"supported": i18n.SUPPORTED_LANGUAGES})
    out["language"] = lang
    loc = out.get("preferred_location")
    if loc is not None:
        lat, lon = loc.get("latitude"), loc.get("longitude")
        if lat is None or lon is None or not -90 <= lat <= 90 or not -180 <= lon <= 180:
            raise AppError(422, "invalid_coordinates", "preferred_location needs valid latitude/longitude.")
    return out


def create(data: dict, owner_id: str) -> dict:
    d = _validate(data)
    with session() as db:
        p = Profile(profile_id=f"fp-{uuid.uuid4().hex[:16]}", owner_id=owner_id,
                    **{k: d.get(k) for k in ("nickname", "preferred_location", "preferred_crop", "preferred_growth_stage", "farm_area", "farm_area_unit", "notification_preferences")},
                    language=d["language"])
        db.add(p)
        db.commit()
        return _dict(p)


def _owned_profile(db, profile_id: str, owner_id: str) -> Profile:
    profile = db.scalar(select(Profile).where(Profile.profile_id == profile_id, Profile.owner_id == owner_id))
    if not profile:
        raise AppError(404, "profile_not_found", "Profile not found.")
    return profile


def get(profile_id: str, owner_id: str) -> dict:
    with session() as db:
        return _dict(_owned_profile(db, profile_id, owner_id))


def update(profile_id: str, data: dict, owner_id: str) -> dict:
    with session() as db:
        p = _owned_profile(db, profile_id, owner_id)
        d = _validate({**_dict(p), **{k: v for k, v in data.items() if v is not None}})
        for k in ("nickname", "preferred_location", "preferred_crop", "preferred_growth_stage", "farm_area", "farm_area_unit", "language", "notification_preferences"):
            setattr(p, k, d.get(k))
        db.commit()
        return _dict(p)


def delete_profile(profile_id: str, owner_id: str) -> bool:
    with session() as db:
        res = db.execute(delete(Profile).where(Profile.profile_id == profile_id, Profile.owner_id == owner_id))
        db.commit()
        return res.rowcount > 0


def personalisation_context(profile_id: Optional[str], owner_id: str) -> Optional[str]:
    """F28: optional saved details + recent assessment history, passed to the advisory as CONTEXT ONLY (no new advice is created)."""
    if not profile_id:
        return None
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from ..models.tables import Assessment
    from ..schemas.common import SEVERITY_ORDER
    try:
        p = get(profile_id, owner_id)
    except AppError as error:
        if error.status == 404:
            return None
        raise
    parts = []
    if p.get("farm_area"):
        parts.append(f"Farm area saved by the user: {p['farm_area']} {p.get('farm_area_unit') or ''}".strip())
    with session() as db:
        since = datetime.now(timezone.utc) - timedelta(days=30)
        rows = db.scalars(select(Assessment).where(Assessment.profile_id == profile_id, Assessment.owner_id == owner_id,
                                                  Assessment.created_at >= since)).all()
    if rows:
        top = max((r.overall_risk for r in rows if r.overall_risk in SEVERITY_ORDER), key=lambda x: SEVERITY_ORDER[x], default=None)
        parts.append(f"Assessments in the last 30 days: {len(rows)}" + (f"; highest risk seen: {top}" if top else ""))
    return "; ".join(parts) or None
