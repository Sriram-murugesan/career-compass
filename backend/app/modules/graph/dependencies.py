from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.dependencies import get_app_settings, get_session
from app.knowledge.repository import GraphRepository
from app.modules.graph.service import GraphService
from app.modules.profile import profile_service_for


def get_graph_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> GraphService:
    return GraphService(
        GraphRepository(session, min_users=settings.graph_min_users), profile_service_for(session)
    )
