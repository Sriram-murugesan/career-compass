from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.core.schema import ApiModel

Category = Literal["fitness", "learning", "career", "wellbeing", "other"]


class HabitCreate(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)  # default for topics
    category: Category = "other"
    target_per_week: int = Field(default=7, ge=1, le=7)  # 7 = every day
    target_minutes: int | None = Field(default=None, ge=5, le=600)
    linked_topic: str | None = Field(default=None, min_length=1, max_length=60)  # mock-test topic


class HabitUpdate(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    category: Category | None = None
    target_per_week: int | None = Field(default=None, ge=1, le=7)
    target_minutes: int | None = Field(default=None, ge=5, le=600)
    archived: bool | None = None


class LogIn(ApiModel):
    minutes: int | None = Field(default=None, ge=1, le=1440)
    note: str = Field(default="", max_length=200)


class HabitOut(ApiModel):
    id: uuid.UUID
    name: str
    category: str
    target_per_week: int
    target_minutes: int | None
    linked_topic: str | None
    created_at: datetime


class LogOut(ApiModel):
    habit_id: uuid.UUID
    day: date
    minutes: int | None
    note: str


class HabitStatus(ApiModel):
    habit: HabitOut
    done_today: bool
    minutes_today: int | None
    week_count: int  # check-ins this week (Mon-Sun)
    streak: int
    streak_unit: Literal["days", "weeks"]  # daily habits count days, weekly targets weeks
    last7: list[bool]  # oldest → today
    total_sessions: int
    total_minutes: int


class DayActivity(ApiModel):
    day: date
    completed: int  # habits checked in that day


class LearningTopic(ApiModel):
    """A mock-test topic and the study done for it."""

    topic: str
    role: str  # the test it came from
    latest_percent: int
    previous_percent: int | None
    delta: int | None  # latest - previous (positive = improved)
    last_tested: datetime
    habit_id: uuid.UUID | None  # the learning habit tracking it, if any
    sessions_since_test: int
    minutes_since_test: int
    status: Literal["untracked", "not_started", "studying", "ready_to_retest", "improved"]


class ScorePoint(ApiModel):
    attempt_id: uuid.UUID
    taken_at: datetime
    percent: int
    role: str
    learning_sessions_before: int  # learning check-ins since the previous attempt
    learning_minutes_before: int


class Overview(ApiModel):
    today: date
    habits: list[HabitStatus]
    done_today: int
    week_completion: int  # % of this week's targets met so far
    heatmap: list[DayActivity]  # last 28 days, oldest first
    learning: list[LearningTopic]  # weakest mock-test topics first
    score_trend: list[ScorePoint]  # oldest first
