from typing import Literal

from pydantic import BaseModel, Field


class InterviewOutput(BaseModel):
    focus: str
    questions: list[str] = Field(max_length=10)


# ── Mock test (multiple choice, graded by code) ─────────────────────────────

Difficulty = Literal["easy", "medium", "hard"]


class MockQuestionDraft(BaseModel):
    """What the model writes. Loose on purpose: bad items are dropped in code, so one
    malformed question doesn't throw away the whole test."""

    question: str
    options: list[str]
    answer_index: int
    explanation: str = ""
    topic: str = "General"
    difficulty: str = "medium"


class MockTestDraft(BaseModel):
    questions: list[MockQuestionDraft]


class MockQuestion(BaseModel):
    """A validated question, options shuffled; `answer_index` never leaves the server."""

    question: str
    options: list[str] = Field(min_length=4, max_length=4)
    answer_index: int = Field(ge=0, le=3)
    explanation: str
    topic: str
    difficulty: Difficulty
