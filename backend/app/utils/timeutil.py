from datetime import datetime, timedelta, timezone
from typing import Optional


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def localize(naive_iso: Optional[str], utc_offset_seconds: int) -> Optional[str]:
    """Open-Meteo returns local times without offset; attach the explicit offset (spec §5-B: explicit time zones)."""
    if not naive_iso:
        return None
    try:
        dt = datetime.fromisoformat(naive_iso)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone(timedelta(seconds=utc_offset_seconds)))
    return dt.isoformat()


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def minutes_between(later: datetime, earlier: datetime) -> float:
    return (later - earlier).total_seconds() / 60.0
