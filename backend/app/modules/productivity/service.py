"""BUSINESS LAYER for the productivity tracker — plain rules, no LLM, no agent run.

Dates are the user's LOCAL calendar days: the browser sends `today`, and the server only
checks it is within a day of UTC (time zones), so check-ins land on the right day.

The link to mock tests: weak topics from graded attempts become learning suggestions; a
learning habit tied to a topic counts the study since that topic was last tested, and the
score trend shows learning time between consecutive attempts.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from app.core.errors import Conflict, NotFound, ValidationFailed
from app.db.base import utcnow
from app.modules.interview import AttemptTopics, InterviewHistory
from app.modules.productivity.models import Habit, HabitLog
from app.modules.productivity.repository import ProductivityRepository
from app.modules.productivity.schemas import (
    DayActivity,
    HabitCreate,
    HabitOut,
    HabitStatus,
    HabitUpdate,
    LearningTopic,
    LogIn,
    LogOut,
    Overview,
    ScorePoint,
)

LOOKBACK_DAYS = 182  # streaks and totals look back ~6 months
HEATMAP_DAYS = 28
BACKFILL_DAYS = 60  # check-ins can be added for missed days up to this far back
MAX_HABITS = 30
WEAK_TOPIC = 80  # topic scores below this are suggested for study
READY_SESSIONS, READY_MINUTES = 3, 90  # enough study to retest a topic


def _out(habit: Habit) -> HabitOut:
    return HabitOut(
        id=habit.id,
        name=habit.name,
        category=habit.category,
        target_per_week=habit.target_per_week,
        target_minutes=habit.target_minutes,
        linked_topic=habit.linked_topic,
        created_at=habit.created_at,
    )


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())  # Monday


def _streak(days: set[date], today: date, target_per_week: int) -> tuple[int, str]:
    if target_per_week >= 7:
        # Consecutive days; today not done yet doesn't break it (the day isn't over).
        cursor = today if today in days else today - timedelta(days=1)
        streak = 0
        while cursor in days:
            streak += 1
            cursor -= timedelta(days=1)
        return streak, "days"
    # Weekly targets: consecutive weeks meeting the target; this week counts once met.
    week = _week_start(today)

    def met(start: date) -> bool:
        return sum(1 for d in days if start <= d < start + timedelta(days=7)) >= target_per_week

    streak = 1 if met(week) else 0
    week -= timedelta(days=7)
    while met(week):
        streak += 1
        week -= timedelta(days=7)
    return streak, "weeks"


def _aware(moment: datetime) -> datetime:
    """SQLite hands back naive datetimes; everything here is UTC."""
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def _topic_key(topic: str) -> str:
    return " ".join(topic.split()).casefold()


class ProductivityService:
    def __init__(self, repository: ProductivityRepository, interviews: InterviewHistory) -> None:
        self.repository = repository
        self.interviews = interviews

    # ── Days ────────────────────────────────────────────────────────────────

    @staticmethod
    def check_today(today: date) -> date:
        utc_today = utcnow().date()
        if abs((today - utc_today).days) > 1:
            raise ValidationFailed("`today` must be your current local date")
        return today

    def _check_day(self, day: date, today: date) -> None:
        if day > today:
            raise ValidationFailed("You can't check in for a future day")
        if (today - day).days > BACKFILL_DAYS:
            raise ValidationFailed(f"Check-ins can be added up to {BACKFILL_DAYS} days back")

    # ── Habits ──────────────────────────────────────────────────────────────

    async def create(self, user_id: uuid.UUID, data: HabitCreate) -> HabitOut:
        active = await self.repository.habits(user_id)
        if len(active) >= MAX_HABITS:
            raise ValidationFailed(f"You can track up to {MAX_HABITS} habits; archive one first")
        topic = " ".join(data.linked_topic.split()) if data.linked_topic else None
        if topic and any(
            h.linked_topic and _topic_key(h.linked_topic) == _topic_key(topic) for h in active
        ):
            raise Conflict(f"You're already tracking {topic}")
        name = (data.name or "").strip() or (f"Learn {topic}" if topic else "")
        if not name:
            raise ValidationFailed("Give the habit a name")
        habit = await self.repository.create_habit(
            user_id,
            name=name,
            category="learning" if topic else data.category,
            target_per_week=data.target_per_week,
            target_minutes=data.target_minutes,
            linked_topic=topic,
        )
        return _out(habit)

    async def update(self, user_id: uuid.UUID, habit_id: uuid.UUID, data: HabitUpdate) -> HabitOut:
        habit = await self._owned(user_id, habit_id)
        changes = data.model_dump(exclude_unset=True)
        if "name" in changes and changes["name"] is not None:
            changes["name"] = changes["name"].strip()
        await self.repository.update_habit(habit, changes)
        return _out(habit)

    async def delete(self, user_id: uuid.UUID, habit_id: uuid.UUID) -> None:
        await self.repository.delete_habit(await self._owned(user_id, habit_id))

    async def check_in(
        self, user_id: uuid.UUID, habit_id: uuid.UUID, day: date, today: date, data: LogIn
    ) -> LogOut:
        self._check_day(day, self.check_today(today))
        habit = await self._owned(user_id, habit_id)
        log = await self.repository.put_log(
            habit, day, minutes=data.minutes, note=data.note.strip()
        )
        return LogOut(habit_id=habit.id, day=log.day, minutes=log.minutes, note=log.note)

    async def undo(self, user_id: uuid.UUID, habit_id: uuid.UUID, day: date) -> None:
        habit = await self._owned(user_id, habit_id)
        await self.repository.delete_log(habit.id, day)

    # ── The dashboard ───────────────────────────────────────────────────────

    async def overview(self, user_id: uuid.UUID, today: date) -> Overview:
        today = self.check_today(today)
        habits = await self.repository.habits(user_id)
        logs = await self.repository.logs(user_id, today - timedelta(days=LOOKBACK_DAYS), today)
        by_habit: dict[uuid.UUID, dict[date, HabitLog]] = defaultdict(dict)
        for log in logs:
            by_habit[log.habit_id][log.day] = log

        statuses: list[HabitStatus] = []
        week_start = _week_start(today)
        met = target = 0
        for habit in habits:
            entries = by_habit.get(habit.id, {})
            days = set(entries)
            week_count = sum(1 for d in days if week_start <= d <= today)
            streak, unit = _streak(days, today, habit.target_per_week)
            met += min(week_count, habit.target_per_week)
            target += habit.target_per_week
            statuses.append(
                HabitStatus(
                    habit=_out(habit),
                    done_today=today in days,
                    minutes_today=entries[today].minutes if today in entries else None,
                    week_count=week_count,
                    streak=streak,
                    streak_unit=unit,
                    last7=[today - timedelta(days=i) in days for i in range(6, -1, -1)],
                    total_sessions=len(days),
                    total_minutes=sum(e.minutes or 0 for e in entries.values()),
                )
            )

        active_ids = {h.id for h in habits}
        per_day: dict[date, int] = defaultdict(int)
        for log in logs:
            if log.habit_id in active_ids:
                per_day[log.day] += 1
        heatmap = [
            DayActivity(day=today - timedelta(days=i), completed=per_day[today - timedelta(days=i)])
            for i in range(HEATMAP_DAYS - 1, -1, -1)
        ]

        history = await self.interviews.recent(user_id)
        return Overview(
            today=today,
            habits=statuses,
            done_today=sum(1 for s in statuses if s.done_today),
            week_completion=round(100 * met / target) if target else 0,
            heatmap=heatmap,
            learning=self._learning(history, habits, by_habit),
            score_trend=self._trend(history, habits, logs),
        )

    def _learning(
        self,
        history: list[AttemptTopics],
        habits: list[Habit],
        by_habit: dict[uuid.UUID, dict[date, HabitLog]],
    ) -> list[LearningTopic]:
        # topic → [(attempt, percent)] newest first
        results: dict[str, list[tuple[AttemptTopics, int]]] = defaultdict(list)
        labels: dict[str, str] = {}
        for attempt in history:
            for topic, (correct, total) in attempt.topics.items():
                key = _topic_key(topic)
                labels.setdefault(key, topic)
                results[key].append((attempt, round(100 * correct / total) if total else 0))
        tracked = {_topic_key(h.linked_topic): h for h in habits if h.linked_topic is not None}

        topics: list[LearningTopic] = []
        for key, scores in results.items():
            latest_attempt, latest = scores[0]
            habit = tracked.get(key)
            if latest >= WEAK_TOPIC and habit is None:
                continue  # strong and not being studied: nothing to suggest
            previous = scores[1][1] if len(scores) > 1 else None
            delta = latest - previous if previous is not None else None
            # Study logged AFTER the latest test of this topic (by time, so studying and
            # retesting on the same day is attributed correctly).
            tested_at = _aware(latest_attempt.created_at)
            since = (
                [
                    log
                    for log in by_habit.get(habit.id, {}).values()
                    if _aware(log.created_at) > tested_at
                ]
                if habit
                else []
            )
            minutes = sum(log.minutes or 0 for log in since)
            if habit is None:
                status = "untracked"
            elif not since:
                status = "improved" if delta is not None and delta > 0 else "not_started"
            elif len(since) >= READY_SESSIONS or minutes >= READY_MINUTES:
                status = "ready_to_retest"
            else:
                status = "studying"
            topics.append(
                LearningTopic(
                    topic=labels[key],
                    role=latest_attempt.role,
                    latest_percent=latest,
                    previous_percent=previous,
                    delta=delta,
                    last_tested=latest_attempt.created_at,
                    habit_id=habit.id if habit else None,
                    sessions_since_test=len(since),
                    minutes_since_test=minutes,
                    status=status,
                )
            )
        topics.sort(key=lambda t: (t.latest_percent, t.topic))
        return topics[:8]

    def _trend(
        self, history: list[AttemptTopics], habits: list[Habit], logs: list[HabitLog]
    ) -> list[ScorePoint]:
        learning_ids = {h.id for h in habits if h.category == "learning"}
        learning = [log for log in logs if log.habit_id in learning_ids]
        attempts = list(reversed(history[:10]))  # oldest first
        points: list[ScorePoint] = []
        previous_at: datetime | None = None
        for attempt in attempts:
            taken_at = _aware(attempt.created_at)
            window = [
                log
                for log in learning
                if (previous_at is None or _aware(log.created_at) > previous_at)
                and _aware(log.created_at) <= taken_at
            ]
            points.append(
                ScorePoint(
                    attempt_id=attempt.attempt_id,
                    taken_at=attempt.created_at,
                    percent=attempt.percent,
                    role=attempt.role,
                    learning_sessions_before=len(window),
                    learning_minutes_before=sum(log.minutes or 0 for log in window),
                )
            )
            previous_at = taken_at
        return points

    async def _owned(self, user_id: uuid.UUID, habit_id: uuid.UUID) -> Habit:
        habit = await self.repository.get_habit(user_id, habit_id)
        if habit is None:
            raise NotFound("Habit not found")
        return habit
