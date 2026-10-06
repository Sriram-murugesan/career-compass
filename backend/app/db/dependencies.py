"""FastAPI dependencies for the database and settings — the request's unit of work."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.session import Database


def get_database(request: Request) -> Database:
    db: Database = request.app.state.db
    return db


def get_app_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """One session per request: committed if the handler succeeds, rolled back otherwise."""
    async with get_database(request).session() as session:
        yield session
