"""Structured logging with secret redaction.

Every log line carries the request id. A filter scrubs anything that looks
like a credential — passwords, bearer tokens, cookies, Groq keys, JWTs —
before it is written, so secrets cannot reach a log file even by accident.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.request_context import current_request_id

REDACTED = "[REDACTED]"

_SENSITIVE_KEYS = re.compile(
    r"pass(word)?|secret|token|authorization|cookie|api[-_]?key", re.IGNORECASE
)
# Token *counts* (LLM usage) are not secrets — keep them visible for cost tracking.
_SAFE_KEYS = {"prompttokens", "completiontokens", "totaltokens", "maxtokens"}


def _is_sensitive_key(key: object) -> bool:
    name = str(key)
    if name.replace("_", "").lower() in _SAFE_KEYS:
        return False
    return bool(_SENSITIVE_KEYS.search(name))


_SENSITIVE_PATTERNS = [
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/-]+=*"),
    re.compile(r"\bgsk_[A-Za-z0-9]+"),  # Groq API keys
    re.compile(r"\bsk-or-[A-Za-z0-9_-]+"),  # OpenRouter API keys
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),  # other OpenAI-style keys
    re.compile(r"(?i)(postgres(?:ql)?(?:\+\w+)?://[^:/\s]+:)[^@\s]+"),  # database passwords
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*"),  # JWTs
    re.compile(r"(?i)(cc_refresh=)[^;\s]+"),  # the refresh cookie
    re.compile(r"(?i)(app_key=)[^&\s]+"),  # Adzuna key in a URL
]


def redact(value: Any) -> Any:
    """Recursively scrub secrets from strings, dicts and lists."""
    if isinstance(value, str):
        for pattern in _SENSITIVE_PATTERNS:
            value = pattern.sub(lambda m: (m.group(1) if m.groups() else "") + REDACTED, value)
        return value
    if isinstance(value, dict):
        return {
            key: REDACTED if _is_sensitive_key(key) else redact(item) for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [redact(item) for item in value]
    return value


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage())
        record.args = None
        extra = getattr(record, "context", None)
        if extra is not None:
            record.context = redact(extra)
        record.request_id = current_request_id() or "-"
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "requestId": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        context = getattr(record, "context", None)
        if context:
            payload["context"] = context
        if record.exc_info:
            payload["error"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload, default=str)


class ReadableFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        time = datetime.now().strftime("%H:%M:%S")
        context = getattr(record, "context", None)
        request_id = getattr(record, "request_id", "-")[:8]
        line = f"{time} {record.levelname:<7} [{request_id}] {record.getMessage()}"
        if context:
            line += f"  {context}"
        if record.exc_info:
            line += "\n" + str(redact(self.formatException(record.exc_info)))
        return line


def configure_logging(level: str, *, json_output: bool, stream: Any = None) -> logging.Handler:
    """Install one redacting handler on the root logger. Returns it (tests read its stream)."""
    if stream is None and hasattr(sys.stdout, "reconfigure"):
        # Windows consoles default to cp1252: degrade odd characters instead of crashing.
        sys.stdout.reconfigure(errors="backslashreplace")
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.addFilter(RedactingFilter())
    handler.setFormatter(JsonFormatter() if json_output else ReadableFormatter())

    root = logging.getLogger()
    for existing in list(root.handlers):
        if getattr(existing, "_career_compass", False):
            root.removeHandler(existing)
    handler._career_compass = True  # type: ignore[attr-defined]
    root.addHandler(handler)
    root.setLevel(level)

    # Uvicorn's own access log is replaced by our request middleware (it has request ids).
    logging.getLogger("uvicorn.access").disabled = True
    for noisy in ("httpx", "httpcore", "aiosqlite", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return handler
