from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, Request

from app.db.dependencies import get_database
from app.db.session import Database
from app.modules.chat.repository import ChatRepository
from app.modules.chat.service import ChatService, ChatUnitOfWork
from app.modules.profile import profile_service_for
from app.orchestrator import Orchestrator


def get_chat_service(
    request: Request, db: Annotated[Database, Depends(get_database)]
) -> ChatService:
    @asynccontextmanager
    async def unit_of_work() -> AsyncIterator[ChatUnitOfWork]:
        async with db.session() as session:
            yield ChatUnitOfWork(chat=ChatRepository(session), profile=profile_service_for(session))

    orchestrator: Orchestrator = request.app.state.orchestrator
    return ChatService(unit_of_work, orchestrator)
