"""The response envelope every endpoint returns — mirrors ApiEnvelope in
frontend/src/lib/api.ts so the frontend reads one shape everywhere:

    { "success": true, "data": {...}, "error": null, "meta": { "requestId": "..." } }
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from app.core.request_context import current_request_id
from app.core.schema import ApiModel

T = TypeVar("T")


class ApiErrorBody(ApiModel):
    code: str
    message: str
    details: dict[str, list[str]] | None = None


class Meta(ApiModel):
    request_id: str | None = None


class Envelope(ApiModel, Generic[T]):
    success: bool
    data: T | None
    error: ApiErrorBody | None
    meta: Meta


def ok(data: T) -> Envelope[T]:
    return Envelope[T](
        success=True, data=data, error=None, meta=Meta(request_id=current_request_id())
    )


def fail_body(
    code: str, message: str, details: dict[str, list[str]] | None = None
) -> dict[str, Any]:
    """Serialized failure envelope, for exception handlers that build raw responses."""
    envelope = Envelope[None](
        success=False,
        data=None,
        error=ApiErrorBody(code=code, message=message, details=details),
        meta=Meta(request_id=current_request_id()),
    )
    return envelope.model_dump(by_alias=True, exclude_none=False)
