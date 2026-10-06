"""DATA LAYER for profiles."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.profile.models import Profile


class ProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: uuid.UUID) -> Profile | None:
        return await self.session.get(Profile, user_id)

    async def create(self, user_id: uuid.UUID) -> Profile:
        profile = Profile(user_id=user_id, ai_preferences={})
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def update(self, profile: Profile, changes: dict[str, Any]) -> Profile:
        for field, value in changes.items():
            setattr(profile, field, value)
        await self.session.flush()
        return profile
