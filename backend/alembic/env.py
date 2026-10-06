"""Alembic environment — async, and works for SQLite (dev/tests), Docker Postgres, Neon and Supabase.

    uv run alembic revision --autogenerate -m "add jobs table"   # after editing models
    uv run alembic upgrade head                                   # apply

Migrations use DATABASE_DIRECT_URL when set: never run DDL through a
transaction-mode pooler (Neon "-pooler" host, Supabase port 6543).
"""

from __future__ import annotations

import asyncio
import logging.config

from alembic import context
from sqlalchemy.engine import Connection

from app.db.session import Database
from app.model_registry import Base

config = context.config
if config.config_file_name and not config.attributes.get("database_url"):
    # Only when run from the CLI — the app configures its own logging.
    logging.config.fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _database_url() -> str:
    url = config.attributes.get("database_url")
    if url:
        return str(url)
    from app.core.config import get_settings  # CLI run: read backend/.env

    settings = get_settings()
    return settings.database_direct_url or settings.database_url


def _run(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=connection.dialect.name == "sqlite",  # SQLite can't ALTER most things
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_online() -> None:
    database = Database(_database_url(), pool_size=1)
    try:
        async with database.engine.connect() as connection:
            await connection.run_sync(_run)
            await connection.commit()
    finally:
        await database.dispose()


if context.is_offline_mode():
    context.configure(url=_database_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(_run_online())
