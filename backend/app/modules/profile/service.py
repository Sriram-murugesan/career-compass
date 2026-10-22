"""BUSINESS LAYER for profiles. Also the public read API other modules use
(chat hands a profile snapshot to the agents)."""

from __future__ import annotations

import uuid
from typing import Any

from app.knowledge.types import ProfileGraphSync
from app.modules.profile.models import Profile
from app.modules.profile.repository import ProfileRepository
from app.modules.profile.schemas import AiPreferences, ProfileOut, ProfileUpdate, Skill


class ProfileService:
    def __init__(
        self, repository: ProfileRepository, graph: ProfileGraphSync | None = None
    ) -> None:
        self.repository = repository
        self.graph = graph  # the shared knowledge graph, rebuilt from the profile on edit

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
        out = _to_out(profile)
        if self.graph is not None and changes.keys() & {"skills", "target_roles", "headline"}:
            await self.graph.sync_user(user_id, out.model_dump())
        return out

    async def snapshot(self, user_id: uuid.UUID) -> dict[str, Any]:
        """Plain-dict view handed to the agents as context."""
        return (await self.get(user_id)).model_dump()

    async def _get_or_create(self, user_id: uuid.UUID) -> Profile:
        return await self.repository.get(user_id) or await self.repository.create(user_id)


def _to_out(profile: Profile) -> ProfileOut:
    work_preference = profile.work_preference or ""
    return ProfileOut(
        headline=profile.headline or "",
        bio=profile.bio or "",
        location=profile.location or "",
        target_salary=profile.target_salary or "",
        work_preference=(
            work_preference if work_preference in ("Remote", "Hybrid", "Onsite") else ""
        ),
        experience_level=profile.experience_level or "",
        target_roles=list(profile.target_roles or []),
        skills=[Skill.model_validate(skill) for skill in profile.skills or []],
        interests=list(profile.interests or []),
        goals=list(profile.goals or []),
        ai_preferences=AiPreferences.model_validate(profile.ai_preferences or {}),
    )
