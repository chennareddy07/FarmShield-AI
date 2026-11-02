"""Provider-independent LLM adapter (P4). ALL LLM network calls live in this module."""
import base64
import json
import re
from typing import Optional, Protocol

from ..core import monitoring
from ..core.config import get_settings
from ..core.http import ProviderError, request_json


class LLMUnavailable(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class LLMProvider(Protocol):
    name: str
    supports_vision: bool

    async def generate_json(self, system: str, user: str, max_tokens: int = 1200) -> dict: ...
    async def generate_vision_json(self, system: str, user: str, image: bytes, media_type: str, max_tokens: int = 1200) -> dict: ...


def extract_json(text: str) -> dict:
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.I)
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in model output")
    obj = json.loads(t[start:end + 1])
    if not isinstance(obj, dict):
        raise ValueError("model output JSON is not an object")
    return obj


class DisabledProvider:
    name = "disabled"
    supports_vision = False

    async def generate_json(self, system, user, max_tokens=1200):
        raise LLMUnavailable("not_configured")

    async def generate_vision_json(self, system, user, image, media_type, max_tokens=1200):
        raise LLMUnavailable("not_configured")


class AnthropicProvider:
    name = "anthropic"
    supports_vision = True

    def __init__(self, key: str, model: str, base_url: Optional[str], timeout: float):
        self.key, self.model, self.timeout = key, model, timeout
        self.base = (base_url or "https://api.anthropic.com").rstrip("/")

    async def _call(self, system: str, content, max_tokens: int) -> dict:
        try:
            data = await request_json("llm", "POST", f"{self.base}/v1/messages", headers={"x-api-key": self.key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                                      json={"model": self.model, "max_tokens": max_tokens, "system": system, "messages": [{"role": "user", "content": content}]},
                                      timeout=self.timeout, retries=1)
            text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
            monitoring.record_success("llm")
            return extract_json(text)
        except ProviderError as e:
            monitoring.record_failure("llm", e.kind)
            raise LLMUnavailable(e.kind)
        except (ValueError, KeyError, AttributeError) as e:
            raise LLMUnavailable(f"bad_output:{type(e).__name__}")

    async def generate_json(self, system, user, max_tokens=1200):
        return await self._call(system, user, max_tokens)

    async def generate_vision_json(self, system, user, image, media_type, max_tokens=1200):
        blocks = [{"type": "image", "source": {"type": "base64", "media_type": media_type, "data": base64.b64encode(image).decode()}}, {"type": "text", "text": user}]
        return await self._call(system, blocks, max_tokens)


def _supports_vision_model(model: str) -> bool:
    model_id = model.casefold()
    return any(marker in model_id for marker in (
        "gpt-4o", "gpt-4.1", "grok-2-vision", "grok-vision",
        "llama-4-scout", "llava", "qwen2-vl", "qwen2.5-vl",
    ))


class OpenAICompatibleProvider:
    name = "openai_compatible"

    def __init__(self, key: str, model: str, base_url: str, timeout: float):
        self.key, self.model, self.base, self.timeout = key, model, base_url.rstrip("/"), timeout
        self.supports_vision = _supports_vision_model(model)

    async def _call(self, system: str, user_content, max_tokens: int) -> dict:
        try:
            data = await request_json("llm", "POST", f"{self.base}/chat/completions", headers={"Authorization": f"Bearer {self.key}"},
                                      json={"model": self.model, "max_tokens": max_tokens, "response_format": {"type": "json_object"},
                                            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user_content}]},
                                      timeout=self.timeout, retries=1)
            monitoring.record_success("llm")
            return extract_json(data["choices"][0]["message"]["content"])
        except ProviderError as e:
            monitoring.record_failure("llm", e.kind)
            raise LLMUnavailable(e.kind)
        except (ValueError, KeyError, IndexError, TypeError) as e:
            raise LLMUnavailable(f"bad_output:{type(e).__name__}")

    async def generate_json(self, system, user, max_tokens=1200):
        return await self._call(system, user, max_tokens)

    async def generate_vision_json(self, system, user, image, media_type, max_tokens=1200):
        uri = f"data:{media_type};base64,{base64.b64encode(image).decode()}"
        return await self._call(system, [{"type": "text", "text": user}, {"type": "image_url", "image_url": {"url": uri}}], max_tokens)


_override: Optional[LLMProvider] = None


def set_provider_override(p: Optional[LLMProvider]) -> None:     # used by tests only
    global _override
    _override = p


def get_provider() -> LLMProvider:
    if _override is not None:
        return _override
    s = get_settings()
    key = s.secret("llm_api_key")
    if s.llm_provider == "anthropic" and key and s.llm_model:
        return AnthropicProvider(key, s.llm_model, s.llm_base_url, s.llm_timeout_seconds)
    if s.llm_provider == "openai_compatible" and key and s.llm_model and s.llm_base_url:
        return OpenAICompatibleProvider(key, s.llm_model, s.llm_base_url, s.llm_timeout_seconds)
    return DisabledProvider()
