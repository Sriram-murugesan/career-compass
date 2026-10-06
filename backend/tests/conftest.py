"""Shared fixtures. Every test module gets a fresh app on a fresh SQLite file,
migrated with the real Alembic migrations (so migrations are tested too)."""

from __future__ import annotations

import io
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.core.config import Settings
from app.main import create_app

TEST_SECRET = "test-secret-that-is-long-enough-for-hs256-signing"
VALID_USER = {
    "name": "Ada Lovelace",
    "email": "Ada@Example.com",
    "password": "correct horse battery",
}


def make_settings(db_dir: Path, **overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "environment": "test",
        "jwt_secret": TEST_SECRET,
        "database_url": f"sqlite+aiosqlite:///{(db_dir / 'test.db').as_posix()}",
        "auth_rate_limit_per_minute": 1000,
        "cors_origins": ["http://localhost:3000"],
        **overrides,
    }
    return Settings(_env_file=None, **values)  # _env_file=None: never read backend/.env


@dataclass
class Harness:
    app: FastAPI
    client: httpx.AsyncClient
    logs: io.StringIO

    async def sign_up(self, **overrides: str) -> dict[str, Any]:
        self.client.cookies.clear()
        response = await self.client.post("/api/auth/sign-up", json={**VALID_USER, **overrides})
        assert response.status_code == 201, response.text
        data: dict[str, Any] = response.json()["data"]
        return data

    def auth(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}


@asynccontextmanager
async def running_app(
    settings: Settings, llm_transport: httpx.AsyncBaseTransport | None = None
) -> AsyncIterator[Harness]:
    logs = io.StringIO()
    app = create_app(settings, log_stream=logs, llm_transport=llm_transport)
    async with app.router.lifespan_context(app):  # runs startup: migrations, LLM pool, agents
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield Harness(app=app, client=client, logs=logs)


@pytest.fixture(scope="module")
async def harness(tmp_path_factory: pytest.TempPathFactory) -> AsyncIterator[Harness]:
    async with running_app(make_settings(tmp_path_factory.mktemp("db"))) as h:
        yield h


def parse_sse(body: str) -> list[dict[str, Any]]:
    """Parse a text/event-stream body into its JSON data payloads."""
    import json

    events = []
    for block in body.strip().split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: ") :]))
    return events
