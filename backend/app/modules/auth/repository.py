"""DATA LAYER — the only code that touches the auth tables. No business rules."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.modules.auth.models import RefreshToken, User


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_user_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def find_user_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def find_user_by_google_sub(self, google_sub: str) -> User | None:
        result = await self.session.execute(select(User).where(User.google_sub == google_sub))
        return result.scalar_one_or_none()

    async def create_user(
        self,
        *,
        name: str,
        email: str,
        password_hash: str | None = None,
        google_sub: str | None = None,
        avatar_url: str | None = None,
        email_verified: bool = False,
    ) -> User | None:
        """Returns None when the email (or Google account) is already registered."""
        user = User(
            name=name,
            email=email,
            password_hash=password_hash,
            google_sub=google_sub,
            avatar_url=avatar_url,
            email_verified=email_verified,
        )
        try:
            async with self.session.begin_nested():  # savepoint: a duplicate doesn't poison the txn
                self.session.add(user)
                await self.session.flush()
        except IntegrityError:
            return None
        return user

    async def link_google_account(
        self, user: User, *, google_sub: str, avatar_url: str | None, drop_password: bool
    ) -> User:
        user.google_sub = google_sub
        user.email_verified = True
        if drop_password:
            user.password_hash = None
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
        await self.session.flush()
        return user

    async def revoke_all_sessions(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=utcnow())
        )

    async def add_refresh_token(
        self,
        *,
        user_id: uuid.UUID,
        family_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        user_agent: str | None,
        ip: str | None,
        token_id: uuid.UUID | None = None,
    ) -> RefreshToken:
        record = RefreshToken(
            id=token_id or uuid.uuid4(),
            user_id=user_id,
            family_id=family_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip=ip,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def find_refresh_token(self, token_hash: str) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def retire_refresh_token(self, token_id: uuid.UUID, replaced_by: uuid.UUID) -> bool:
        """Revoke a token only if still active. False = someone else already used it.

        The conditional UPDATE makes two concurrent refreshes race safely:
        exactly one sees rowcount 1.
        """
        result = await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.id == token_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=utcnow(), replaced_by_id=replaced_by)
        )
        return bool(result.rowcount)  # type: ignore[attr-defined]

    async def revoke_family(self, family_id: uuid.UUID) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=utcnow())
        )
