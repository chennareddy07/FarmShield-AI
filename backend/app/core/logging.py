"""Logging with secret redaction (spec §9-C: do not log secrets or sensitive personal data)."""
import logging
import re

_PATTERNS = [
    re.compile(r"\b(?:gsk_[A-Za-z0-9_\-]{8,}|sk-[A-Za-z0-9_\-]{8,})\b"),
    re.compile(r"(?i)(api[_-]?key|authorization|bearer|token)(['\"=: ]+)([A-Za-z0-9_\-\.]{6,})"),
]


def redact(text: str) -> str:
    text = _PATTERNS[0].sub("[REDACTED]", text)
    return _PATTERNS[1].sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", text)


class RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = redact(record.getMessage())
            record.args = ()
        except Exception:
            pass
        return True


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO),
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    for h in logging.getLogger().handlers:
        h.addFilter(RedactFilter())
