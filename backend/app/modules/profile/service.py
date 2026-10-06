"""BUSINESS LAYER for profiles. Also the public read API other modules use
(chat hands a profile snapshot to the agents)."""

from __future__ import annotations

import uuid
from typing import Any

from app.modules.profile.models import Profile
from app.modules.profile.repository import ProfileRepository
from app.modules.profile.schemas import AiPreferences, ProfileOut, ProfileUpdate, Skill


class ProfileService:
    def __init__(self, repository: ProfileRepository) -> None:
        self.repository = repository

    async def get(self, user_id: uuid.UUID) -> ProfileOut:
        return _to_out(await self._get_or_create(user_id))

    async def update(self, user_id: uuid.UUID, data: ProfileUpdate) -> ProfileOut:
        profile = await self._get_or_create(user_id)
        changes = data.model_dump(exclude_unset=True)
        # Normalise list fields: trim, drop blanks and duplicates, keep order.
        for field in ("target_roles", "interests", "goals"):
            if field in changes and changes[field] is not None:
                changes[field] = list(dict.fromkeys(v.strip() for v in changes[field] if v.strip()))
        await self.repository.update(profile, {k: v for k, v in changes.items() if v is not None})
        return _to_out(profile)

    async def snapshot(self, user_id: uuid.UUID) -> dict[str, Any]:
        """Plain-dict view handed to the agents as context."""
        return (await self.get(user_id)).model_dump()

    async def _get_or_create(self, user_id: uuid.UUID) -> Profile:
        return await self.repository.get(user_id) or await self.repository.create(user_id)


def _to_out(profile: Profile) -> ProfileOut:
    return ProfileOut(
        headline=profile.headline or "",
        location=profile.location or "",
        experience_level=profile.experience_level or "",
        target_roles=list(profile.target_roles or []),
        skills=[Skill.model_validate(skill) for skill in profile.skills or []],
        interests=list(profile.interests or []),
        goals=list(profile.goals or []),
        ai_preferences=AiPreferences.model_validate(profile.ai_preferences or {}),
    )
