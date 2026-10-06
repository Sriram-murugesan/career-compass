"""Auth tables: identity + credentials, and refresh-token sessions."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UuidPrimaryKey, utcnow


class User(UuidPrimaryKey, Timestamps, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(100))
    # Stored lower-cased (normalised by the request schema); unique index enforces one account.
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_onboarded: Mapped[bool] = mapped_column(Boolean, default=False)


class RefreshToken(UuidPrimaryKey, Base):
    """One row per issued refresh token; only the SHA-256 hash is stored.

    Tokens from one sign-in share a family_id. Rotating revokes the old row and
    points it at its replacement. A revoked token presented again means it was
    copied → the whole family is revoked.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    family_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, default=None)
    user_agent: Mapped[str | None] = mapped_column(String(256), default=None)
    ip: Mapped[str | None] = mapped_column(String(64), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
