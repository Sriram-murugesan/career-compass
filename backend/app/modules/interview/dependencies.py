from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.dependencies import get_app_settings, get_session
from app.knowledge.repository import GraphRepository
from app.memory.store import SessionMemoryWriter
from app.modules.interview.repository import InterviewRepository
from app.modules.interview.service import InterviewHistory, InterviewService
from app.modules.profile import profile_service_for


def get_interview_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> InterviewService:
    return InterviewService(
        InterviewRepository(session),
        profile_service_for(session),
        GraphRepository(session, min_users=settings.graph_min_users),
        request.app.state.llm,
        SessionMemoryWriter(session),  # same transaction as the graded attempt
    )


def interview_history_for(session: AsyncSession) -> InterviewHistory:
    """For other modules that already hold a session (e.g. the productivity tracker)."""
    return InterviewHistory(InterviewRepository(session))
