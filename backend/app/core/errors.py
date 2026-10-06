"""Application errors.

Services raise these; core/handlers.py turns them into the standard envelope.
They carry no FastAPI types, so business logic stays independent of HTTP.
"""

from __future__ import annotations


class AppError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: dict[str, list[str]] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.details = details


class ValidationFailed(AppError):
    status_code = 400
    code = "VALIDATION_ERROR"


class Unauthorized(AppError):
    status_code = 401
    code = "UNAUTHORIZED"


class Forbidden(AppError):
    status_code = 403
    code = "FORBIDDEN"


class NotFound(AppError):
    status_code = 404
    code = "NOT_FOUND"


class Conflict(AppError):
    status_code = 409
    code = "CONFLICT"


class RateLimited(AppError):
    status_code = 429
    code = "RATE_LIMITED"
