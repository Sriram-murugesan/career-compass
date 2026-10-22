"""HTTP LAYER for the productivity tracker."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app import endpoints as ep
from app.core.responses import Envelope, ok
from app.modules.auth import CurrentUserId
from app.modules.productivity.dependencies import get_productivity_service
from app.modules.productivity.schemas import (
    HabitCreate,
    HabitOut,
    HabitUpdate,
    LogIn,
    LogOut,
    Overview,
)
from app.modules.productivity.service import ProductivityService

router = APIRouter(tags=["productivity"])

Service = Annotated[ProductivityService, Depends(get_productivity_service)]
Today = Annotated[date, Query(description="The user's local date, YYYY-MM-DD")]


@router.get(ep.PRODUCTIVITY_OVERVIEW, response_model=Envelope[Overview])
async def overview(user_id: CurrentUserId, service: Service, today: Today) -> Envelope[Overview]:
    return ok(await service.overview(user_id, today))


@router.post(ep.PRODUCTIVITY_HABITS, response_model=Envelope[HabitOut], status_code=201)
async def create_habit(
    body: HabitCreate, user_id: CurrentUserId, service: Service
) -> Envelope[HabitOut]:
    return ok(await service.create(user_id, body))


@router.patch(ep.PRODUCTIVITY_HABIT, response_model=Envelope[HabitOut])
async def update_habit(
    habit_id: uuid.UUID, body: HabitUpdate, user_id: CurrentUserId, service: Service
) -> Envelope[HabitOut]:
    return ok(await service.update(user_id, habit_id, body))


@router.delete(ep.PRODUCTIVITY_HABIT, response_model=Envelope[dict[str, bool]])
async def delete_habit(
    habit_id: uuid.UUID, user_id: CurrentUserId, service: Service
) -> Envelope[dict[str, bool]]:
    await service.delete(user_id, habit_id)
    return ok({"deleted": True})


@router.put(ep.PRODUCTIVITY_HABIT_LOG, response_model=Envelope[LogOut])
async def check_in(
    habit_id: uuid.UUID,
    day: date,
    body: LogIn,
    user_id: CurrentUserId,
    service: Service,
    today: Today,
) -> Envelope[LogOut]:
    return ok(await service.check_in(user_id, habit_id, day, today, body))


@router.delete(ep.PRODUCTIVITY_HABIT_LOG, response_model=Envelope[dict[str, bool]])
async def undo_check_in(
    habit_id: uuid.UUID, day: date, user_id: CurrentUserId, service: Service
) -> Envelope[dict[str, bool]]:
    await service.undo(user_id, habit_id, day)
    return ok({"deleted": True})
