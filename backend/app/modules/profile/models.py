"""Career profile: what the agents know about the user's goals and skills."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow


class Profile(Base):
    __tablename__ = "profiles"

    # 1:1 with users. The FK points at the auth module's table by name only;
    # no Python import crosses the module boundary.
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    headline: Mapped[str] = mapped_column(String(200), default="")
    bio: Mapped[str] = mapped_column(String(1000), default="", server_default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    target_salary: Mapped[str] = mapped_column(String(100), default="", server_default="")
    # "Remote" | "Hybrid" | "Onsite" | "" (not set)
    work_preference: Mapped[str] = mapped_column(String(20), default="", server_default="")
    experience_level: Mapped[str] = mapped_column(String(100), default="")
    target_roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    skills: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    interests: Mapped[list[str]] = mapped_column(JSON, default=list)
    goals: Mapped[list[str]] = mapped_column(JSON, default=list)
    ai_preferences: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
