from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.dependencies import get_app_settings, get_session
from app.knowledge.repository import GraphRepository
from app.modules.profile.repository import ProfileRepository
from app.modules.profile.service import ProfileService


def get_profile_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> ProfileService:
    # Same session = same transaction: a profile edit and its graph update commit together.
    graph = GraphRepository(session, min_users=settings.graph_min_users)
    return ProfileService(ProfileRepository(session), graph)


def profile_service_for(session: AsyncSession) -> ProfileService:
    """For other modules that already hold a session (e.g. chat's background run)."""
    return ProfileService(ProfileRepository(session))
