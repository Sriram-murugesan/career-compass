"""Productivity tracker: habits (gym, cardio, learn a topic …) and one check-in per day."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UuidPrimaryKey, utcnow


class Habit(UuidPrimaryKey, Base):
    __tablename__ = "habits"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(60))
    # fitness | learning | career | wellbeing | other
    category: Mapped[str] = mapped_column(String(20))
    target_per_week: Mapped[int] = mapped_column(Integer, default=7)  # 7 = daily
    target_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)  # per session
    # A learning habit can be tied to a mock-test topic: its study time is set against
    # that topic's score before and after.
    linked_topic: Mapped[str | None] = mapped_column(String(60), nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class HabitLog(UuidPrimaryKey, Base):
    __tablename__ = "habit_logs"
    __table_args__ = (UniqueConstraint("habit_id", "day"),)

    habit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("habits.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    day: Mapped[date] = mapped_column(Date)  # the user's local calendar day
    minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
