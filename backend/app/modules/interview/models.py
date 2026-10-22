"""Mock interview tests and attempts.

`questions` holds the full test INCLUDING the answer key; it is only ever read by the
service, which strips answers before anything goes to the browser.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UuidPrimaryKey, utcnow


class MockTest(UuidPrimaryKey, Base):
    __tablename__ = "mock_tests"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(120))
    domain: Mapped[str] = mapped_column(String(120), default="")
    difficulty: Mapped[str] = mapped_column(String(10))  # easy | medium | hard | mixed
    questions: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )


class MockTestAttempt(UuidPrimaryKey, Base):
    __tablename__ = "mock_test_attempts"

    test_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("mock_tests.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    answers: Mapped[list[int | None]] = mapped_column(JSON)
    score: Mapped[int] = mapped_column(Integer)
    total: Mapped[int] = mapped_column(Integer)
    percent: Mapped[int] = mapped_column(Integer)
    time_taken_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weak_topics: Mapped[list[str]] = mapped_column(JSON, default=list)  # feeds the next test
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
