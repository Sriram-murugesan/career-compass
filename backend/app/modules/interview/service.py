"""BUSINESS LAYER for mock interview tests.

create   profile + shared-graph insights + past weak topics → LLM test for ONE role/domain
submit   graded by code against the stored key — instant, no LLM — then remembered so
         other agents (roadmap, advisor) know the weak spots

The answer key never leaves this service except inside a graded attempt.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.agents.base import LlmClient
from app.agents.interview.mock_test import MockTestUnavailable, generate_mock_test, grade
from app.agents.interview.schema import MockQuestion
from app.core.errors import NotFound, RateLimited, Unavailable, ValidationFailed
from app.db.base import utcnow
from app.knowledge.normalize import current_role_from_headline
from app.knowledge.repository import GraphRepository
from app.knowledge.store import render_insights
from app.memory.store import NewMemory, SessionMemoryWriter
from app.modules.interview.models import MockTest, MockTestAttempt
from app.modules.interview.repository import InterviewRepository
from app.modules.interview.schemas import (
    AttemptIn,
    AttemptResult,
    AttemptSummary,
    MockTestCreate,
    MockTestOut,
    MockTestSummary,
    QuestionOut,
    QuestionResult,
    TopicScoreOut,
)
from app.modules.profile import ProfileService

DAILY_TEST_LIMIT = 20  # LLM cost guard per user per 24 h


def _questions(test: MockTest) -> list[MockQuestion]:
    return [MockQuestion.model_validate(q) for q in test.questions]


def _summary(attempt: MockTestAttempt) -> AttemptSummary:
    return AttemptSummary(
        id=attempt.id,
        score=attempt.score,
        total=attempt.total,
        percent=attempt.percent,
        created_at=attempt.created_at,
    )


def _public(test: MockTest, attempts: list[MockTestAttempt]) -> MockTestOut:
    return MockTestOut(
        id=test.id,
        role=test.role,
        domain=test.domain,
        difficulty=test.difficulty,
        created_at=test.created_at,
        questions=[
            QuestionOut(
                index=i,
                question=q.question,
                options=q.options,
                topic=q.topic,
                difficulty=q.difficulty,
            )
            for i, q in enumerate(_questions(test))
        ],
        attempts=[_summary(a) for a in attempts],
        best_percent=max((a.percent for a in attempts), default=None),
    )


def _candidate_context(profile: dict[str, object], weak_topics: list[str], graph: str) -> str:
    skills = [
        f"{s['name']} ({s.get('level', 'Intermediate')})"
        for s in profile.get("skills") or []  # type: ignore[attr-defined]
        if isinstance(s, dict) and s.get("name")
    ]
    lines = ["## Candidate"]
    for label, value in (
        ("Headline", profile.get("headline")),
        ("Experience level", profile.get("experience_level")),
        ("Skills", ", ".join(skills)),
        ("Target roles", ", ".join(profile.get("target_roles") or [])),  # type: ignore[arg-type]
        ("Interested domains", ", ".join(profile.get("interests") or [])),  # type: ignore[arg-type]
        ("Goals", ", ".join(profile.get("goals") or [])),  # type: ignore[arg-type]
    ):
        if value:
            lines.append(f"- {label}: {value}")
    if weak_topics:
        lines.append(
            f"- Got these wrong in recent mock tests (revisit some, differently): "
            f"{', '.join(weak_topics)}"
        )
    if graph:
        lines.append(f"\n## Shared career graph\n{graph}")
    return "\n".join(lines)


class InterviewService:
    def __init__(
        self,
        repository: InterviewRepository,
        profiles: ProfileService,
        graph: GraphRepository,
        llm: LlmClient,
        memory: SessionMemoryWriter | None = None,
    ) -> None:
        self.repository = repository
        self.profiles = profiles
        self.graph = graph
        self.llm = llm
        self.memory = memory

    async def create(self, user_id: uuid.UUID, data: MockTestCreate) -> MockTestOut:
        profile = await self.profiles.snapshot(user_id)
        roles = [r for r in profile.get("target_roles") or [] if r.strip()]
        role = (data.role or "").strip() or (roles[0] if roles else "")
        role = role or current_role_from_headline(str(profile.get("headline") or ""))
        if not role:
            raise ValidationFailed("Pick a role, or add a target role to your profile first")
        interests = [i for i in profile.get("interests") or [] if i.strip()]
        domain = (data.domain or "").strip() or (interests[0] if interests else "")

        since = utcnow() - timedelta(hours=24)
        if await self.repository.count_tests_since(user_id, since) >= DAILY_TEST_LIMIT:
            raise RateLimited(f"You can create {DAILY_TEST_LIMIT} mock tests a day; retake one")

        if not await self.graph.has_links(user_id):
            await self.graph.sync_user(user_id, profile)
        insights = await self.graph.insights(user_id)
        context = _candidate_context(
            profile,
            await self.repository.recent_weak_topics(user_id),
            render_insights(insights),
        )
        # What the core questions centre on: the user's skills, then the role's gap skills.
        focus = [str(s["name"]) for s in profile.get("skills") or [] if s.get("name")][:8]
        focus += [
            n.node.label
            for r in insights.roles
            if r.role.label.casefold() == role.casefold()
            for n in r.skills
            if not n.yours
        ][:4]
        try:
            questions = await generate_mock_test(
                self.llm,
                role=role,
                domain=domain,
                difficulty=data.difficulty,
                count=data.count,
                context=context,
                skills=focus,
            )
        except MockTestUnavailable as exc:
            raise Unavailable(str(exc)) from exc

        test = await self.repository.create_test(
            user_id,
            role=role[:120],
            domain=domain[:120],
            difficulty=data.difficulty,
            questions=[q.model_dump() for q in questions],
        )
        return _public(test, [])

    async def get(self, user_id: uuid.UUID, test_id: uuid.UUID) -> MockTestOut:
        test = await self._owned(user_id, test_id)
        return _public(test, await self.repository.attempts([test.id]))

    async def list_tests(self, user_id: uuid.UUID) -> list[MockTestSummary]:
        tests = await self.repository.list_tests(user_id)
        by_test: dict[uuid.UUID, list[MockTestAttempt]] = {}
        for attempt in await self.repository.attempts([t.id for t in tests]):
            by_test.setdefault(attempt.test_id, []).append(attempt)
        return [
            MockTestSummary(
                id=t.id,
                role=t.role,
                domain=t.domain,
                difficulty=t.difficulty,
                question_count=len(t.questions),
                created_at=t.created_at,
                attempts=len(by_test.get(t.id, [])),
                best_percent=max((a.percent for a in by_test.get(t.id, [])), default=None),
                last_percent=by_test[t.id][-1].percent if by_test.get(t.id) else None,
            )
            for t in tests
        ]

    async def submit(
        self, user_id: uuid.UUID, test_id: uuid.UUID, data: AttemptIn
    ) -> AttemptResult:
        test = await self._owned(user_id, test_id)
        questions = _questions(test)
        if len(data.answers) > len(questions):
            raise ValidationFailed("More answers than questions")
        if any(a is not None and not 0 <= a < 4 for a in data.answers):
            raise ValidationFailed("Each answer must be 0-3 or null")
        answers = list(data.answers) + [None] * (len(questions) - len(data.answers))

        result = grade(questions, answers)
        attempt = await self.repository.add_attempt(
            test,
            answers=answers,
            score=result.score,
            total=result.total,
            percent=result.percent,
            time_taken_seconds=data.time_taken_seconds,
            weak_topics=result.weak_topics,
        )
        previous = await self.repository.attempts([test.id])

        if self.memory is not None:
            weak = f"; weakest: {', '.join(result.weak_topics)}" if result.weak_topics else ""
            where = f", {test.domain}" if test.domain else ""
            await self.memory.remember(
                user_id,
                [
                    NewMemory(
                        kind="interview",
                        content=(
                            f"Mock test for {test.role}{where}: {result.score}/{result.total} "
                            f"({result.percent}%){weak}"
                        ),
                        source_agent="interview",
                    )
                ],
            )

        return AttemptResult(
            id=attempt.id,
            test_id=test.id,
            score=result.score,
            total=result.total,
            percent=result.percent,
            grade=result.label,
            topics=[
                TopicScoreOut(topic=t.topic, correct=t.correct, total=t.total, percent=t.percent)
                for t in result.topics
            ],
            weak_topics=result.weak_topics,
            results=[
                QuestionResult(
                    index=i,
                    question=q.question,
                    options=q.options,
                    topic=q.topic,
                    your_answer=answers[i],
                    correct_answer=q.answer_index,
                    correct=result.correct[i],
                    explanation=q.explanation,
                )
                for i, q in enumerate(questions)
            ],
            time_taken_seconds=data.time_taken_seconds,
            attempt_number=len(previous),
            best_percent=max(a.percent for a in previous),
            created_at=attempt.created_at,
        )

    async def _owned(self, user_id: uuid.UUID, test_id: uuid.UUID) -> MockTest:
        test = await self.repository.get_test(user_id, test_id)
        if test is None:  # someone else's test looks exactly like a missing one
            raise NotFound("Mock test not found")
        return test


# ── Read API for other modules (productivity links learning to these scores) ─────────


@dataclass(frozen=True)
class AttemptTopics:
    attempt_id: uuid.UUID
    created_at: datetime
    role: str
    domain: str
    percent: int
    topics: dict[str, tuple[int, int]]  # topic → (correct, total)


class InterviewHistory:
    def __init__(self, repository: InterviewRepository) -> None:
        self.repository = repository

    async def recent(self, user_id: uuid.UUID, limit: int = 20) -> list[AttemptTopics]:
        """The user's graded attempts, newest first, with per-topic results."""
        history = []
        for attempt, test in await self.repository.recent_attempts(user_id, limit):
            result = grade(_questions(test), attempt.answers)
            history.append(
                AttemptTopics(
                    attempt_id=attempt.id,
                    created_at=attempt.created_at,
                    role=test.role,
                    domain=test.domain,
                    percent=attempt.percent,
                    topics={t.topic: (t.correct, t.total) for t in result.topics},
                )
            )
        return history
