"""F23 server-side transcription (optional). Browser Web Speech API is the default client path."""
import uuid
from typing import Optional

from ..core import monitoring
from ..core.config import get_settings
from ..core.errors import AppError
from ..core.http import ProviderError, client

ALLOWED = {"audio/webm", "audio/ogg", "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp4", "audio/m4a", "audio/x-m4a"}
MAX_AUDIO = 10 * 1024 * 1024


async def transcribe(data: bytes, content_type: Optional[str], language_hint: Optional[str]) -> dict:
    ct = (content_type or "").split(";")[0].lower()
    if ct not in ALLOWED:
        raise AppError(415, "unsupported_audio_type", "Unsupported audio format.", {"supported": sorted(ALLOWED)})
    if not data or len(data) > MAX_AUDIO:
        raise AppError(413 if data else 422, "audio_size_invalid", "Audio must be non-empty and at most 10 MB.")
    s = get_settings()
    if not s.stt_api_base_url or not s.secret("stt_api_key"):
        return {"transcription": None, "language": None, "confidence": None, "status": "not_configured",
                "message": "Server-side speech recognition is not configured. Use your browser's speech input or type your question."}
    try:
        async with client(60) as c:
            r = await c.post(f"{s.stt_api_base_url.rstrip('/')}/audio/transcriptions", headers={"Authorization": f"Bearer {s.secret('stt_api_key')}"},
                             files={"file": (f"audio.{ct.split('/')[-1]}", data, ct)}, data={"model": s.stt_model, "response_format": "verbose_json", **({"language": language_hint} if language_hint in ("en", "te") else {})})
        if r.status_code >= 400:
            raise ProviderError("stt", "unavailable", f"HTTP {r.status_code}")
        j = r.json()
        monitoring.record_success("stt")
        text = (j.get("text") or "").strip()
        if not text:
            return {"transcription": None, "language": None, "confidence": None, "status": "failed", "message": "Could not recognise speech. Please try again or type your question."}
        return {"transcription": text, "language": j.get("language"), "confidence": None, "status": "ok",
                "message": "Please check the recognised text before sending; speech recognition can be wrong. Confidence is not provided by this service."}
    except Exception as e:                                           # E26
        monitoring.record_failure("stt", type(e).__name__)
        return {"transcription": None, "language": None, "confidence": None, "status": "failed", "message": "Transcription failed. Please retry or type your question."}
