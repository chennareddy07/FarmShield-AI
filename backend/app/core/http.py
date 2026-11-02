"""Shared outbound HTTP helper: timeouts, bounded retry with backoff (E30), typed provider errors.
Tests inject `httpx.MockTransport` via `set_transport` - production never uses it."""
import asyncio
import logging
from typing import Any, Dict, Optional

import httpx

from .config import get_settings

log = logging.getLogger("farmshield.http")
_transport: Optional[httpx.AsyncBaseTransport] = None


def set_transport(t: Optional[httpx.AsyncBaseTransport]) -> None:
    global _transport
    _transport = t


class ProviderError(Exception):
    """kind: unavailable | rate_limited | timeout | bad_response"""

    def __init__(self, provider: str, kind: str, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.provider, self.kind, self.message, self.status = provider, kind, message, status

    @property
    def http_status(self) -> int:
        return {"rate_limited": 503, "timeout": 504}.get(self.kind, 502)


def client(timeout: Optional[float] = None) -> httpx.AsyncClient:
    s = get_settings()
    total_timeout = timeout if timeout is not None else s.provider_timeout_seconds
    return httpx.AsyncClient(
        timeout=httpx.Timeout(total_timeout, connect=min(total_timeout, 5.0)),
        transport=_transport,
        follow_redirects=False,
        headers={"User-Agent": "FarmShieldAI/1.0 (+decision-support)"},
    )


async def request_json(provider: str, method: str, url: str, *, params: Optional[Dict[str, Any]] = None,
                       headers: Optional[Dict[str, str]] = None, json: Any = None, retries: Optional[int] = None,
                       timeout: Optional[float] = None, expect: str = "json") -> Any:
    s = get_settings()
    retries = s.provider_max_retries if retries is None else retries
    last: Optional[ProviderError] = None
    for attempt in range(retries + 1):
        try:
            async with client(timeout) as c:
                r = await c.request(method, url, params=params, headers=headers, json=json)
            if r.status_code == 429:
                last = ProviderError(provider, "rate_limited", "Provider rate limit reached.", 429)
            elif 300 <= r.status_code < 400:
                raise ProviderError(provider, "bad_response", "Provider attempted an unexpected redirect.", r.status_code)
            elif r.status_code >= 500:
                last = ProviderError(provider, "unavailable", f"Provider returned HTTP {r.status_code}.", r.status_code)
            elif r.status_code >= 400:
                raise ProviderError(provider, "bad_response", f"Provider rejected the request (HTTP {r.status_code}).", r.status_code)
            else:
                if expect == "text":
                    return r.text
                try:
                    return r.json()
                except ValueError:
                    raise ProviderError(provider, "bad_response", "Provider returned a non-JSON response.", r.status_code)
        except ProviderError as e:
            if e.kind == "bad_response":
                raise
            last = e
        except httpx.TimeoutException:
            last = ProviderError(provider, "timeout", "Provider timed out.")
        except httpx.HTTPError as e:
            last = ProviderError(provider, "unavailable", f"Provider unreachable ({type(e).__name__}).")
        if attempt < retries:
            await asyncio.sleep(min(0.4 * (2 ** attempt), 2.0))
    assert last is not None
    log.warning("provider=%s failed kind=%s", provider, last.kind)
    raise last
