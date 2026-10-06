"""HTTP LAYER for profiles."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app import endpoints as ep
from app.core.responses import Envelope, ok
from app.modules.auth import CurrentUserId
from app.modules.profile.dependencies import get_profile_service
from app.modules.profile.schemas import ProfileOut, ProfileUpdate
from app.modules.profile.service import ProfileService

router = APIRouter(tags=["profile"])

Service = Annotated[ProfileService, Depends(get_profile_service)]


@router.get(ep.PROFILE, response_model=Envelope[ProfileOut])
async def get_profile(user_id: CurrentUserId, service: Service) -> Envelope[ProfileOut]:
    return ok(await service.get(user_id))


@router.patch(ep.PROFILE, response_model=Envelope[ProfileOut])
async def update_profile(
    body: ProfileUpdate, user_id: CurrentUserId, service: Service
) -> Envelope[ProfileOut]:
    return ok(await service.update(user_id, body))
