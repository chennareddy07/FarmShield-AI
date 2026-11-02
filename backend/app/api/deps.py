import hmac
import uuid
from typing import Optional

from fastapi import Header, Request

from ..core.config import get_settings
from ..core.errors import AppError


def current_owner_id(request: Request) -> str:
    """Return a server-issued, browser-session identity for anonymous demo data."""
    owner_id = request.session.get("owner_id")
    if not isinstance(owner_id, str) or len(owner_id) != 32:
        owner_id = uuid.uuid4().hex
        request.session["owner_id"] = owner_id
    return owner_id


def require_admin(authorization: Optional[str] = Header(default=None)) -> None:
    token = get_settings().secret("admin_api_token")
    if not token:
        raise AppError(403, "admin_not_configured", "The admin dashboard is disabled: ADMIN_API_TOKEN is not configured.")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(401, "authentication_required", "Authentication required.")
    if not hmac.compare_digest(authorization[7:].strip(), token):
        raise AppError(403, "permission_denied", "Permission denied.")
