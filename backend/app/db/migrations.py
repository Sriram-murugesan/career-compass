"""Run Alembic migrations from code (used on startup when DB_AUTO_MIGRATE=true)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.attributes["database_url"] = database_url
    return config


async def upgrade_to_head(database_url: str) -> None:
    # alembic/env.py runs its own event loop, so it gets a worker thread.
    await asyncio.to_thread(command.upgrade, alembic_config(database_url), "head")
