from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_session
from app.modules.interview import interview_history_for
from app.modules.productivity.repository import ProductivityRepository
from app.modules.productivity.service import ProductivityService


def get_productivity_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProductivityService:
    return ProductivityService(ProductivityRepository(session), interview_history_for(session))
