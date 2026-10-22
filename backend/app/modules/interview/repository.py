"""DATA LAYER for mock tests. Every read is scoped to the owning user."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.interview.models import MockTest, MockTestAttempt


class InterviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_test(
        self,
        user_id: uuid.UUID,
        *,
        role: str,
        domain: str,
        difficulty: str,
        questions: list[dict[str, Any]],
    ) -> MockTest:
        test = MockTest(
            user_id=user_id, role=role, domain=domain, difficulty=difficulty, questions=questions
        )
        self.session.add(test)
        await self.session.flush()
        return test

    async def get_test(self, user_id: uuid.UUID, test_id: uuid.UUID) -> MockTest | None:
        test = await self.session.get(MockTest, test_id)
        return test if test is not None and test.user_id == user_id else None

    async def list_tests(self, user_id: uuid.UUID, limit: int = 20) -> list[MockTest]:
        result = await self.session.execute(
            select(MockTest)
            .where(MockTest.user_id == user_id)
            .order_by(MockTest.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_tests_since(self, user_id: uuid.UUID, since: datetime) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(MockTest)
            .where(MockTest.user_id == user_id, MockTest.created_at >= since)
        )
        return int(result.scalar_one())

    async def add_attempt(
        self,
        test: MockTest,
        *,
        answers: list[int | None],
        score: int,
        total: int,
        percent: int,
        time_taken_seconds: int | None,
        weak_topics: list[str],
    ) -> MockTestAttempt:
        attempt = MockTestAttempt(
            test_id=test.id,
            user_id=test.user_id,
            answers=answers,
            score=score,
            total=total,
            percent=percent,
            time_taken_seconds=time_taken_seconds,
            weak_topics=weak_topics,
        )
        self.session.add(attempt)
        await self.session.flush()
        return attempt

    async def recent_weak_topics(self, user_id: uuid.UUID, limit: int = 3) -> list[str]:
        result = await self.session.execute(
            select(MockTestAttempt.weak_topics)
            .where(MockTestAttempt.user_id == user_id)
            .order_by(MockTestAttempt.created_at.desc())
            .limit(limit)
        )
        topics: list[str] = []
        for row in result.scalars().all():
            topics.extend(t for t in row or [] if t not in topics)
        return topics[:6]

    async def recent_attempts(
        self, user_id: uuid.UUID, limit: int = 20
    ) -> list[tuple[MockTestAttempt, MockTest]]:
        """Newest first, each with its test (for per-topic score history)."""
        result = await self.session.execute(
            select(MockTestAttempt, MockTest)
            .join(MockTest, MockTest.id == MockTestAttempt.test_id)
            .where(MockTestAttempt.user_id == user_id)
            .order_by(MockTestAttempt.created_at.desc())
            .limit(limit)
        )
        return [(attempt, test) for attempt, test in result.all()]

    async def attempts(self, test_ids: list[uuid.UUID]) -> list[MockTestAttempt]:
        if not test_ids:
            return []
        result = await self.session.execute(
            select(MockTestAttempt)
            .where(MockTestAttempt.test_id.in_(test_ids))
            .order_by(MockTestAttempt.created_at)
        )
        return list(result.scalars().all())
