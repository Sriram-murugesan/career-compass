"""Request id, access log and security headers — one pure-ASGI middleware so
it also wraps streaming (SSE) responses without buffering them."""

from __future__ import annotations

import logging
import time
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.request_context import reset_request_id, set_request_id

logger = logging.getLogger("app.http")

SECURITY_HEADERS = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"cross-origin-opener-policy", b"same-origin"),
    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
]
_DOCS_PATHS = ("/api/docs", "/api/openapi.json")


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp, *, hsts: bool) -> None:
        self.app = app
        self.hsts = hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Always generate the id server-side: a client-chosen id could forge log lines.
        request_id = str(uuid.uuid4())
        token = set_request_id(request_id)
        started = time.perf_counter()
        status_code = 500
        path = scope.get("path", "")

        async def send_with_headers(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                if not path.startswith(_DOCS_PATHS):  # Swagger UI needs scripts; the API never does
                    headers.extend(SECURITY_HEADERS)
                if self.hsts:
                    headers.append(
                        (b"strict-transport-security", b"max-age=31536000; includeSubDomains")
                    )
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            logger.info(
                "%s %s -> %s",
                scope.get("method"),
                path,
                status_code,
                extra={"context": {"durationMs": round((time.perf_counter() - started) * 1000, 1)}},
            )
            reset_request_id(token)
