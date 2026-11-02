"""FarmShield AI backend entry point."""
import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles

from .api.routes import assess_routes, core_routes, data_routes, extra_routes
from .core.config import PROJECT_DIR, get_settings
from .core.db import init_db
from .core.errors import install_error_handlers
from .core.logging import setup_logging
from .core.middleware import BodySizeLimitMiddleware, RateLimitMiddleware, RequestIDMiddleware
from .services import knowledge_service

log = logging.getLogger("farmshield")
_DEVELOPMENT_SESSION_SECRET = secrets.token_urlsafe(48)


def _session_signing_key(settings) -> str:
    configured = settings.secret("session_secret")
    if configured:
        if len(configured) < 32:
            raise RuntimeError("SESSION_SECRET must contain at least 32 characters.")
        return configured
    if settings.app_env.lower() in {"production", "prod"}:
        raise RuntimeError("SESSION_SECRET must be configured for production.")
    log.warning("SESSION_SECRET is not configured; anonymous sessions will not survive process restarts.")
    return _DEVELOPMENT_SESSION_SECRET


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    setup_logging(s.log_level)
    try:
        init_db()
        knowledge_service.ensure_seeded()
    except Exception:
        log.exception("database initialisation failed - starting in degraded mode")
    yield


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="FarmShield AI", version="1.0.0", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json")
    install_error_handlers(app)
    # middleware order: last added runs first
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=s.max_body_bytes)
    app.add_middleware(RateLimitMiddleware, per_minute=s.rate_limit_per_minute, ai_per_minute=s.rate_limit_ai_per_minute)
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origin_list, allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["*"], expose_headers=["X-Request-ID", "Content-Disposition"], allow_credentials=True)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        SessionMiddleware,
        secret_key=_session_signing_key(s),
        session_cookie="farmshield_session",
        max_age=60 * 60 * 24 * 30,
        same_site="lax",
        https_only=s.app_env.lower() in {"production", "prod"},
    )
    for r in (core_routes.router, data_routes.router, assess_routes.router, extra_routes.router):
        app.include_router(r)
    dist = Path(PROJECT_DIR) / "frontend" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="frontend")
    return app


app = create_app()
