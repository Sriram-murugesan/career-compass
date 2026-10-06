"""Composition root: the one place that knows every module.

    uvicorn app.main:create_app --factory --reload --port 4000

Adding a module = one `include_router` line below, its paths in endpoints.py,
and its models in model_registry.py if it has tables.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import endpoints as ep
from app.agents.registry import REGISTRY
from app.core.config import Settings, get_settings
from app.core.handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.core.rate_limit import RateLimiter
from app.db.migrations import upgrade_to_head
from app.db.session import Database
from app.llm.gateway import LlmGateway
from app.llm.pool import build_pool
from app.memory.context import ContextBuilder
from app.memory.store import SqlMemoryStore
from app.modules import auth, chat, health, profile
from app.orchestrator import Orchestrator, OrchestratorDeps

logger = logging.getLogger("app")


def create_app(
    settings: Settings | None = None,
    *,
    log_stream: Any = None,
    llm_transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(
        settings.log_level, json_output=settings.environment == "production", stream=log_stream
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        db = Database(
            settings.database_url, pool_size=settings.db_pool_size, pgbouncer=settings.db_pgbouncer
        )
        if settings.db_auto_migrate:
            await upgrade_to_head(settings.database_direct_url or settings.database_url)

        llm = LlmGateway(
            build_pool(
                [key.get_secret_value() for key in settings.groq_api_keys],
                base_url=settings.groq_base_url,
                large_model=settings.llm_model_large,
                fast_model=settings.llm_model_fast,
            ),
            timeout_seconds=settings.llm_timeout_seconds,
            transport=llm_transport,
        )
        app.state.db = db
        app.state.llm = llm
        app.state.orchestrator = Orchestrator(
            OrchestratorDeps(
                llm=llm,
                memory=SqlMemoryStore(db),
                context_builder=ContextBuilder(settings.memory_context_budget_chars),
                registry=REGISTRY,
                memory_recall_limit=settings.memory_recall_limit,
            )
        )
        logger.info(
            "Career Compass API ready",
            extra={
                "context": {
                    "environment": settings.environment,
                    "database": "sqlite" if db.is_sqlite else "postgres",
                    "llmKeys": len(settings.groq_api_keys),
                    "agents": len(REGISTRY),
                }
            },
        )
        try:
            yield
        finally:
            await llm.aclose()
            await db.dispose()

    app = FastAPI(
        title="Career Compass API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/api/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/api/openapi.json",
    )
    app.state.settings = settings
    app.state.auth_rate_limiter = RateLimiter(settings.auth_rate_limit_per_minute)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,  # the refresh cookie
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
        expose_headers=["x-request-id"],
        max_age=600,
    )
    app.add_middleware(RequestContextMiddleware, hsts=settings.is_production)
    register_exception_handlers(app)

    for router in (health.router, auth.router, profile.router, chat.router):
        app.include_router(router, prefix=ep.API_PREFIX)
    return app
