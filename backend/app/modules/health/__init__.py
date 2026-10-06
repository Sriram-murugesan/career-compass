"""Health check for uptime monitors and deploy gates."""

from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app import endpoints as ep
from app.core.responses import Envelope, ok
from app.core.schema import ApiModel
from app.db.dependencies import get_database
from app.db.session import Database

router = APIRouter(tags=["system"])
_STARTED = time.monotonic()


class LlmEntryStatus(ApiModel):
    id: str
    model: str
    healthy: bool


class Health(ApiModel):
    status: str
    database: str
    uptime_seconds: int
    llm_entries: list[LlmEntryStatus]


@router.get(ep.HEALTH, response_model=Envelope[Health])
async def health(
    request: Request, response: Response, db: Annotated[Database, Depends(get_database)]
) -> Envelope[Health]:
    database_up = await db.ping()
    response.status_code = 200 if database_up else 503
    return ok(
        Health(
            status="ok" if database_up else "degraded",
            database="up" if database_up else "down",
            uptime_seconds=int(time.monotonic() - _STARTED),
            llm_entries=[LlmEntryStatus(**entry) for entry in request.app.state.llm.status()],
        )
    )
