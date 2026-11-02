"""Provider health ledger (F18): last success, last failure, counters. In-memory per process."""
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, Optional

_lock = Lock()
_ledger: Dict[str, dict] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_success(provider: str) -> None:
    with _lock:
        e = _ledger.setdefault(provider, {"successes": 0, "failures": 0, "last_success": None, "last_failure": None, "last_error": None})
        e["successes"] += 1
        e["last_success"] = _now()


def record_failure(provider: str, kind: str, message: Optional[str] = None) -> None:
    with _lock:
        e = _ledger.setdefault(provider, {"successes": 0, "failures": 0, "last_success": None, "last_failure": None, "last_error": None})
        e["failures"] += 1
        e["last_failure"] = _now()
        e["last_error"] = kind


def snapshot() -> Dict[str, dict]:
    with _lock:
        return {k: dict(v) for k, v in _ledger.items()}


def status_for(provider: str) -> str:
    with _lock:
        e = _ledger.get(provider)
    if not e:
        return "unknown"
    if e["last_success"] and (not e["last_failure"] or e["last_success"] >= e["last_failure"]):
        return "available"
    return "unavailable"


def reset() -> None:
    with _lock:
        _ledger.clear()
