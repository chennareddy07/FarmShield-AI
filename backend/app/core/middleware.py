"""Request ID, body-size limit, and per-IP rate limiting (stricter on AI/image routes)."""
import time
import uuid
from collections import OrderedDict, deque
from typing import Dict, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .errors import envelope

AI_PREFIXES = ("/api/advisory", "/api/assistant", "/api/crop-health", "/api/voice", "/api/market/advice")
RATE_LIMIT_WINDOW_SECONDS = 60
MAX_RATE_LIMIT_BUCKETS = 10_000


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-ID", "")[:64] or uuid.uuid4().hex[:16]
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response


class BodySizeLimitMiddleware:
    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_lengths = [value for name, value in scope.get("headers", []) if name.lower() == b"content-length"]
        if len(content_lengths) == 1 and content_lengths[0].isdigit() and int(content_lengths[0]) > self.max_bytes:
            await self._reject(scope, receive, send)
            return

        messages = deque()
        body_size = 0
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] != "http.request":
                break
            body_size += len(message.get("body", b""))
            if body_size > self.max_bytes:
                await self._reject(scope, receive, send)
                return
            if not message.get("more_body", False):
                break

        async def replay():
            return messages.popleft() if messages else await receive()

        await self.app(scope, replay, send)

    @staticmethod
    async def _reject(scope, receive, send):
        request = Request(scope, receive=receive)
        request_id = getattr(request.state, "request_id", "unknown")
        response = JSONResponse(
            status_code=413,
            content={"error_code": "payload_too_large", "message": "The request body is too large.",
                     "request_id": request_id},
            headers={"X-Request-ID": request_id},
        )
        await response(scope, receive, send)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window limiter, in-memory (single-process). Use a shared store for multi-worker deployments."""

    def __init__(self, app, per_minute: int, ai_per_minute: int):
        super().__init__(app)
        self.per_minute, self.ai_per_minute = per_minute, ai_per_minute
        self.hits: Dict[Tuple[str, str], list] = OrderedDict()
        self._last_cleanup = time.monotonic()

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api") or path == "/api/health":
            return await call_next(request)
        bucket = "ai" if path.startswith(AI_PREFIXES) else "std"
        limit = self.ai_per_minute if bucket == "ai" else self.per_minute
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        if now - self._last_cleanup >= RATE_LIMIT_WINDOW_SECONDS:
            expired = [key for key, times in self.hits.items()
                       if not times or now - times[-1] >= RATE_LIMIT_WINDOW_SECONDS]
            for key in expired:
                self.hits.pop(key, None)
            self._last_cleanup = now

        key = (ip, bucket)
        if key not in self.hits and len(self.hits) >= MAX_RATE_LIMIT_BUCKETS:
            self.hits.popitem(last=False)
        q = [t for t in self.hits.get(key, []) if now - t < RATE_LIMIT_WINDOW_SECONDS]
        if len(q) >= limit:
            self.hits[key] = q
            self.hits.move_to_end(key)
            return envelope(request, 429, "rate_limited", "Too many requests. Please wait a minute and retry.")
        q.append(now)
        self.hits[key] = q
        self.hits.move_to_end(key)
        return await call_next(request)
