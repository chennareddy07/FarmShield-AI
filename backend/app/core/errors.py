"""Uniform error envelope: {error_code, message, request_id, details?}. Never leaks stack traces/secrets."""
import logging
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("farmshield.errors")

HTTP_CODES = {400: "bad_request", 401: "authentication_required", 403: "permission_denied", 404: "not_found",
              413: "payload_too_large", 415: "unsupported_media_type", 422: "validation_error",
              429: "rate_limited", 500: "internal_error", 502: "provider_failure", 503: "service_unavailable",
              504: "provider_timeout"}


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str, details: Optional[Any] = None):
        super().__init__(message)
        self.status, self.code, self.message, self.details = status, code, message, details


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def envelope(request: Request, status: int, code: str, message: str, details: Any = None) -> JSONResponse:
    body = {"error_code": code, "message": message, "request_id": _rid(request)}
    if details is not None:
        body["details"] = details
    return JSONResponse(status_code=status, content=body, headers={"X-Request-ID": _rid(request)})


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        return envelope(request, exc.status, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        safe = [{"field": ".".join(str(p) for p in e.get("loc", []) if p != "body"), "issue": e.get("msg")}
                for e in exc.errors()]
        return envelope(request, 422, "validation_error", "The request is invalid.", safe)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        return envelope(request, exc.status_code, HTTP_CODES.get(exc.status_code, "http_error"), str(exc.detail))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        log.exception("unhandled error request_id=%s", _rid(request))   # stack trace goes to server log only
        return envelope(request, 500, "internal_error", "An unexpected error occurred.")
