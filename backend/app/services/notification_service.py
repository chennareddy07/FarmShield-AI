"""F21 in-app notifications with explicit consent, quiet hours and deduplication (L15)."""
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select

from ..core.db import session
from ..core.errors import AppError
from ..models.tables import Notification, Subscription
from ..schemas.common import SEVERITY_ORDER
from ..schemas.risk import RiskRequest
from ..utils.timeutil import iso, parse_iso, utcnow
from . import assessment_service, crop_config_service as cc

ALLOWED_CHANNELS = {"in_app"}
PLANNED_CHANNELS = {"email", "sms"}
RISK_LEVELS = {"moderate", "high", "critical"}


def save_preferences(data: dict) -> dict:
    channels = data.get("channels") or ["in_app"]
    unsupported = [c for c in channels if c not in ALLOWED_CHANNELS]
    if unsupported:
        raise AppError(422, "channel_not_supported", "Only in-app notifications are available in this version.", {"planned": sorted(PLANNED_CHANNELS), "requested": unsupported})
    levels = data.get("risk_levels") or ["high", "critical"]
    if set(levels) - RISK_LEVELS:
        raise AppError(422, "invalid_risk_levels", "risk_levels must be among moderate, high, critical.")
    if data.get("enabled") and not data.get("consent"):
        raise AppError(422, "consent_required", "Explicit consent is required before enabling notifications.")           # E23
    cfg = cc.get_crop(data["crop_id"])
    cc.validate_stage(cfg, data.get("growth_stage_id"))
    loc = data["location"]
    lat, lon = loc.get("latitude"), loc.get("longitude")
    if lat is None or lon is None or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise AppError(422, "invalid_coordinates", "A valid location is required.")
    with session() as db:
        sub = db.scalar(select(Subscription).where(Subscription.user_id == data["user_id"], Subscription.crop_id == data["crop_id"], Subscription.location_id == loc.get("location_id", f"{lat:.2f},{lon:.2f}")))
        if sub is None:
            sub = Subscription(subscription_id=f"sub-{uuid.uuid4().hex[:12]}", user_id=data["user_id"], location_id=loc.get("location_id", f"{lat:.2f},{lon:.2f}"), latitude=lat, longitude=lon, district=loc.get("district"), crop_id=data["crop_id"])
            db.add(sub)
        sub.growth_stage_id = data.get("growth_stage_id")
        sub.enabled = bool(data.get("enabled"))
        sub.channels, sub.risk_levels, sub.warning_categories = channels, levels, data.get("warning_categories") or []
        sub.quiet_hours = data.get("quiet_hours")
        if sub.enabled:
            sub.consent_timestamp = iso(utcnow())
        db.commit()
        return _sub_dict(sub)


def _sub_dict(s: Subscription) -> dict:
    return {"subscription_id": s.subscription_id, "location_id": s.location_id, "crop_id": s.crop_id, "growth_stage_id": s.growth_stage_id, "enabled": s.enabled,
            "channels": s.channels, "risk_levels": s.risk_levels, "warning_categories": s.warning_categories, "quiet_hours": s.quiet_hours, "consent_timestamp": s.consent_timestamp}


def dedupe_key(source_event: str, location_id: str, category: str, window: str) -> str:
    return hashlib.sha256(f"{source_event}|{location_id}|{category}|{window}".encode()).hexdigest()[:40]


def in_quiet_hours(quiet: Optional[dict], now: datetime) -> bool:
    """quiet = {"start": "22:00", "end": "06:00"} in UTC offset given by `utc_offset_minutes` (default IST +330)."""
    if not quiet or not quiet.get("start") or not quiet.get("end"):
        return False
    off = int(quiet.get("utc_offset_minutes", 330))
    local = now + timedelta(minutes=off)
    cur = local.hour * 60 + local.minute
    sh, sm = map(int, quiet["start"].split(":"))
    eh, em = map(int, quiet["end"].split(":"))
    s, e = sh * 60 + sm, eh * 60 + em
    return (s <= cur < e) if s <= e else (cur >= s or cur < e)


def candidates(assessment: dict, sub: dict) -> List[dict]:
    """Events worth notifying for this subscription. Pure function (unit-testable)."""
    wanted = set(sub["risk_levels"])
    loc = sub["location_id"]
    out = []
    for r in assessment["triggered_rules"]:
        if r["severity"] in wanted:
            window = f"{r['period_start']}..{r['period_end']}"
            out.append({"category": r["risk_category"], "severity": r["severity"], "title": f"{r['risk_category']}: {r['rule_id']}", "body": r["reason"], "source": r["source_reference"]["title"] if r.get("source_reference") else "FarmShield rule",
                        "expires_at": f"{r['period_end']}T23:59:59+00:00", "key": dedupe_key(r["rule_id"], loc, r["risk_category"], window)})
    wc = set(sub.get("warning_categories") or [])
    for e in assessment["evidence"]:
        if e["kind"] == "official_warning":
            out.append({"category": "official_warning", "severity": "high", "title": e["title"], "body": (e.get("excerpt") or e["title"])[:500], "source": e.get("publisher") or "IMD", "expires_at": None,
                        "key": dedupe_key(e["evidence_id"], loc, "official_warning", e.get("publication_date") or "")})
    return out


async def process_subscription(sub_row: Subscription) -> int:
    if not sub_row.enabled or not sub_row.consent_timestamp:
        return 0                                                                    # AC29: no consent -> nothing created
    now = utcnow()
    if in_quiet_hours(sub_row.quiet_hours, now):
        return 0
    sub = _sub_dict(sub_row)
    a = await assessment_service.run_assessment(
        RiskRequest(latitude=sub_row.latitude, longitude=sub_row.longitude, crop_id=sub_row.crop_id,
                    growth_stage_id=sub_row.growth_stage_id, district=sub_row.district),
        "notif", sub_row.user_id)
    created = 0
    with session() as db:
        for c in candidates(a, sub):
            exists = db.scalar(select(Notification).where(Notification.user_id == sub_row.user_id, Notification.dedupe_key == c["key"], Notification.status == "active"))
            if exists:
                continue                                                            # AC30 / E24
            db.add(Notification(notification_id=f"n-{uuid.uuid4().hex[:12]}", user_id=sub_row.user_id, category=c["category"], severity=c["severity"], title=c["title"], body=c["body"],
                                source=c["source"], location_label=sub_row.location_id, expires_at=c["expires_at"], dedupe_key=c["key"]))
            created += 1
        db.commit()
    return created


async def refresh_for_user(user_id: str) -> int:
    with session() as db:
        subs = db.scalars(select(Subscription).where(Subscription.user_id == user_id, Subscription.enabled == True)).all()  # noqa: E712
    total = 0
    for s in subs:
        total += await process_subscription(s)
    return total


def list_notifications(user_id: str) -> dict:
    now = utcnow()
    with session() as db:
        rows = db.scalars(select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc())).all()
        for r in rows:
            exp = parse_iso(r.expires_at)
            if r.status == "active" and exp and exp < now:
                r.status = "expired"
        db.commit()
        items = [{"notification_id": r.notification_id, "category": r.category, "severity": r.severity, "title": r.title, "body": r.body, "source": r.source, "location": r.location_label,
                  "created_at": r.created_at.isoformat(), "expires_at": r.expires_at, "status": r.status, "read": r.read} for r in rows]
    return {"notifications": items, "unread_count": sum(1 for i in items if not i["read"] and i["status"] == "active")}


def mark_read(user_id: str, notification_id: str) -> bool:
    with session() as db:
        n = db.get(Notification, notification_id)
        if not n or n.user_id != user_id:
            return False
        n.read = True
        db.commit()
        return True


def get_preferences(user_id: str) -> List[dict]:
    with session() as db:
        return [_sub_dict(s) for s in db.scalars(select(Subscription).where(Subscription.user_id == user_id)).all()]
