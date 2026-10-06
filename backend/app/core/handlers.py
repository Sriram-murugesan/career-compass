"""Every error leaves the API in the standard envelope.

- AppError (raised by services)      → its own status, code and message
- Request validation (bad body)      → 400 VALIDATION_ERROR with per-field messages
- Starlette HTTP errors (404, 405…)  → their status
- Anything else                      → logged in full, generic 500 — internals never leak
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import AppError
from app.core.responses import fail_body

logger = logging.getLogger("app.errors")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.error("application error: %s", exc.message, exc_info=exc)
        return JSONResponse(
            status_code=exc.status_code, content=fail_body(exc.code, exc.message, exc.details)
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        details: dict[str, list[str]] = {}
        for error in exc.errors():
            # loc is ("body", "email") → "email"; a whole-body problem → "body"
            location = [str(part) for part in error.get("loc", ()) if part != "body"]
            field = ".".join(location) or "body"
            details.setdefault(field, []).append(str(error.get("msg", "Invalid value")))
        return JSONResponse(
            status_code=400,
            content=fail_body("VALIDATION_ERROR", "Request validation failed", details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            body = fail_body("NOT_FOUND", f"Route {request.method} {request.url.path} not found")
        else:
            body = fail_body(f"HTTP_{exc.status_code}", str(exc.detail))
        return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=fail_body("INTERNAL_ERROR", "Something went wrong on our side"),
        )
