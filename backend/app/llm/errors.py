from __future__ import annotations


class LlmError(Exception):
    """Base for every gateway failure. Agents catch this and fall back gracefully."""


class LlmUnavailable(LlmError):
    """No key could serve the request (none configured, all cooling down, or all failing)."""


class LlmBadRequest(LlmError):
    """The provider rejected the request itself (4xx) — retrying on another key won't help."""


class LlmBadOutput(LlmError):
    """The model answered, but not with valid JSON for the requested schema."""
