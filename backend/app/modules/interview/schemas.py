from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field

from app.core.schema import ApiModel

TestDifficulty = Literal["easy", "medium", "hard", "mixed"]


class MockTestCreate(ApiModel):
    """Omit role / domain to use the profile's first target role / interest."""

    role: str | None = Field(default=None, max_length=120)
    domain: str | None = Field(default=None, max_length=120)
    difficulty: TestDifficulty = "mixed"
    count: int = Field(default=10, ge=5, le=20)


class QuestionOut(ApiModel):
    index: int
    question: str
    options: list[str]
    topic: str
    difficulty: str
    # No answer here: answers are only revealed by grading an attempt.


class AttemptSummary(ApiModel):
    id: uuid.UUID
    score: int
    total: int
    percent: int
    created_at: datetime


class MockTestOut(ApiModel):
    id: uuid.UUID
    role: str
    domain: str
    difficulty: str
    created_at: datetime
    questions: list[QuestionOut]
    attempts: list[AttemptSummary]
    best_percent: int | None


class MockTestSummary(ApiModel):
    id: uuid.UUID
    role: str
    domain: str
    difficulty: str
    question_count: int
    created_at: datetime
    attempts: int
    best_percent: int | None
    last_percent: int | None


class AttemptIn(ApiModel):
    # One entry per question, in order: the chosen option index (0-3) or null if skipped.
    answers: list[int | None] = Field(max_length=20)
    time_taken_seconds: int | None = Field(default=None, ge=0, le=36_000)


class QuestionResult(ApiModel):
    index: int
    question: str
    options: list[str]
    topic: str
    your_answer: int | None
    correct_answer: int
    correct: bool
    explanation: str


class TopicScoreOut(ApiModel):
    topic: str
    correct: int
    total: int
    percent: int


class AttemptResult(ApiModel):
    id: uuid.UUID
    test_id: uuid.UUID
    score: int
    total: int
    percent: int
    grade: str  # Interview-ready | Strong | Developing | Needs practice
    topics: list[TopicScoreOut]  # weakest first
    weak_topics: list[str]
    results: list[QuestionResult]
    time_taken_seconds: int | None
    attempt_number: int
    best_percent: int
    created_at: datetime
