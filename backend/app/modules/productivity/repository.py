"""DATA LAYER for the productivity tracker. Every query is scoped to the owning user."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.productivity.models import Habit, HabitLog


class ProductivityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def habits(self, user_id: uuid.UUID, *, include_archived: bool = False) -> list[Habit]:
        statement = select(Habit).where(Habit.user_id == user_id).order_by(Habit.created_at)
        if not include_archived:
            statement = statement.where(Habit.archived.is_(False))
        return list((await self.session.execute(statement)).scalars().all())

    async def get_habit(self, user_id: uuid.UUID, habit_id: uuid.UUID) -> Habit | None:
        habit = await self.session.get(Habit, habit_id)
        return habit if habit is not None and habit.user_id == user_id else None

    async def create_habit(self, user_id: uuid.UUID, **fields: Any) -> Habit:
        habit = Habit(user_id=user_id, **fields)
        self.session.add(habit)
        await self.session.flush()
        return habit

    async def update_habit(self, habit: Habit, changes: dict[str, Any]) -> Habit:
        for field, value in changes.items():
            setattr(habit, field, value)
        await self.session.flush()
        return habit

    async def delete_habit(self, habit: Habit) -> None:
        await self.session.delete(habit)
        await self.session.flush()

    async def logs(self, user_id: uuid.UUID, since: date, until: date) -> list[HabitLog]:
        result = await self.session.execute(
            select(HabitLog)
            .where(HabitLog.user_id == user_id, HabitLog.day >= since, HabitLog.day <= until)
            .order_by(HabitLog.day)
        )
        return list(result.scalars().all())

    async def get_log(self, habit_id: uuid.UUID, day: date) -> HabitLog | None:
        result = await self.session.execute(
            select(HabitLog).where(HabitLog.habit_id == habit_id, HabitLog.day == day)
        )
        return result.scalar_one_or_none()

    async def put_log(self, habit: Habit, day: date, *, minutes: int | None, note: str) -> HabitLog:
        log = await self.get_log(habit.id, day)
        if log is None:
            log = HabitLog(habit_id=habit.id, user_id=habit.user_id, day=day)
            self.session.add(log)
        log.minutes, log.note = minutes, note
        await self.session.flush()
        return log

    async def delete_log(self, habit_id: uuid.UUID, day: date) -> None:
        await self.session.execute(
            delete(HabitLog).where(HabitLog.habit_id == habit_id, HabitLog.day == day)
        )
