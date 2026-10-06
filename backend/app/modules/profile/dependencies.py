from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_session
from app.modules.profile.repository import ProfileRepository
from app.modules.profile.service import ProfileService


def get_profile_service(session: Annotated[AsyncSession, Depends(get_session)]) -> ProfileService:
    return ProfileService(ProfileRepository(session))


def profile_service_for(session: AsyncSession) -> ProfileService:
    """For other modules that already hold a session (e.g. chat's background run)."""
    return ProfileService(ProfileRepository(session))
