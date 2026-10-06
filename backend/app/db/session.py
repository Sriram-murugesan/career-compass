"""Async engine + session management, ready for Neon and Supabase.

One DATABASE_URL decides where data lives; nothing else in the code changes:

    sqlite+aiosqlite:///./.data/dev.db                     local, zero setup
    postgresql://career:career@localhost:5432/career_compass   Docker
    postgresql://…@ep-x-pooler.….neon.tech/db?sslmode=require  Neon   (DB_PGBOUNCER=true)
    postgresql://…@….pooler.supabase.com:6543/postgres?sslmode=require  Supabase (DB_PGBOUNCER=true)

asyncpg doesn't understand libpq URL options like `sslmode` / `channel_binding`
(which Neon and Supabase put in their connection strings), so they are
translated here into driver arguments.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_SSL_MODES_REQUIRING_TLS = {"require", "verify-ca", "verify-full"}


def normalize_database_url(raw_url: str) -> tuple[str, dict[str, Any]]:
    """Return (sqlalchemy_url, connect_args) for any supported connection string."""
    url = make_url(raw_url)
    connect_args: dict[str, Any] = {}

    if url.drivername in ("postgres", "postgresql", "postgresql+psycopg", "postgresql+psycopg2"):
        url = url.set(drivername="postgresql+asyncpg")

    if url.drivername == "postgresql+asyncpg":
        query = dict(url.query)
        sslmode = query.pop("sslmode", None)
        query.pop("channel_binding", None)  # libpq-only; asyncpg negotiates SCRAM itself
        if sslmode in _SSL_MODES_REQUIRING_TLS:
            connect_args["ssl"] = "require"
        url = url.set(query=query)

    if url.drivername.startswith("sqlite") and url.database not in (None, "", ":memory:"):
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)

    return url.render_as_string(hide_password=False), connect_args


class Database:
    """Owns the engine and hands out sessions. One instance per process (app.state.db)."""

    def __init__(self, raw_url: str, *, pool_size: int = 5, pgbouncer: bool = False) -> None:
        url, connect_args = normalize_database_url(raw_url)
        engine_args: dict[str, Any] = {"pool_pre_ping": True}

        if url.startswith("postgresql+asyncpg"):
            engine_args.update(pool_size=pool_size, max_overflow=pool_size, pool_recycle=300)
            if pgbouncer:
                # Transaction-mode poolers can't keep prepared statements between transactions.
                connect_args.update(
                    statement_cache_size=0,
                    prepared_statement_name_func=lambda: f"__asyncpg_{uuid.uuid4()}__",
                )

        self.url = url
        self.is_sqlite = url.startswith("sqlite")
        self.engine: AsyncEngine = create_async_engine(
            url, connect_args=connect_args, **engine_args
        )
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Unit of work: commit on success, roll back on any error."""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except BaseException:
                await session.rollback()
                raise

    async def ping(self) -> bool:
        try:
            async with self.engine.connect() as connection:
                await connection.execute(text("select 1"))
            return True
        except Exception:
            return False

    async def dispose(self) -> None:
        await self.engine.dispose()
