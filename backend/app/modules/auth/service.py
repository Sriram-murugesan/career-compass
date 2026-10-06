"""BUSINESS LAYER — the auth rules: who may sign in, how sessions start, rotate
and end. No FastAPI and no SQLAlchemy here (checked by lint-imports): it talks
to the repository and returns plain objects."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from app.core import security
from app.core.errors import Conflict, Unauthorized
from app.modules.auth.models import User
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import AuthSession, AuthUser, SignInRequest, SignUpRequest


@dataclass(frozen=True)
class AuthSettings:
    jwt_secret: str
    access_token_ttl_seconds: int
    refresh_token_ttl_days: int


@dataclass(frozen=True)
class ClientInfo:
    user_agent: str | None = None
    ip: str | None = None


@dataclass(frozen=True)
class IssuedSession:
    session: AuthSession
    refresh_token: str  # goes into the httpOnly cookie — never a response body or a log
    refresh_expires_at: datetime


class SessionRejected(Unauthorized):
    """Refresh refused. `reason` lets the HTTP layer log REUSE_DETECTED as a security event."""

    def __init__(self, reason: Literal["MISSING", "UNKNOWN", "EXPIRED", "REUSE_DETECTED"]) -> None:
        super().__init__("Your session has ended — please sign in again", code="SESSION_EXPIRED")
        self.reason = reason


def _invalid_credentials() -> Unauthorized:
    return Unauthorized("Invalid email or password", code="INVALID_CREDENTIALS")


def to_auth_user(user: User) -> AuthUser:
    """Public shape of a user — never includes the password hash."""
    return AuthUser(id=user.id, name=user.name, email=user.email, is_onboarded=user.is_onboarded)


class AuthService:
    def __init__(self, repository: AuthRepository, settings: AuthSettings) -> None:
        self.repository = repository
        self.settings = settings

    async def sign_up(self, data: SignUpRequest, client: ClientInfo) -> IssuedSession:
        user = await self.repository.create_user(
            name=data.name, email=data.email, password_hash=security.hash_password(data.password)
        )
        if user is None:
            raise Conflict("An account with this email already exists", code="EMAIL_TAKEN")
        return await self._start_session(user, uuid.uuid4(), client)

    async def sign_in(self, data: SignInRequest, client: ClientInfo) -> IssuedSession:
        user = await self.repository.find_user_by_email(data.email)
        if user is None:
            # Same work, same answer as a wrong password: no "this email exists" signal.
            security.burn_password_check(data.password)
            raise _invalid_credentials()
        if not security.verify_password(user.password_hash, data.password):
            raise _invalid_credentials()
        return await self._start_session(user, uuid.uuid4(), client)

    async def refresh(self, raw_token: str | None, client: ClientInfo) -> IssuedSession:
        """Swap a refresh token for a new access token AND a new refresh token (rotation)."""
        if not raw_token:
            raise SessionRejected("MISSING")
        record = await self.repository.find_refresh_token(security.hash_refresh_token(raw_token))
        if record is None:
            raise SessionRejected("UNKNOWN")
        if record.revoked_at is not None:
            # A rotated-away token came back: someone else holds this session. End all of it.
            await self.repository.revoke_family(record.family_id)
            raise SessionRejected("REUSE_DETECTED")
        if _aware(record.expires_at) <= datetime.now(UTC):
            raise SessionRejected("EXPIRED")

        user = await self.repository.find_user_by_id(record.user_id)
        if user is None:
            await self.repository.revoke_family(record.family_id)
            raise SessionRejected("UNKNOWN")

        new_id = uuid.uuid4()
        if not await self.repository.retire_refresh_token(record.id, replaced_by=new_id):
            # Lost a race with another refresh of the same token — treat as reuse.
            await self.repository.revoke_family(record.family_id)
            raise SessionRejected("REUSE_DETECTED")
        return await self._start_session(user, record.family_id, client, token_id=new_id)

    async def sign_out(self, raw_token: str | None) -> None:
        """Ends this device's session. Idempotent."""
        if not raw_token:
            return
        record = await self.repository.find_refresh_token(security.hash_refresh_token(raw_token))
        if record is not None:
            await self.repository.revoke_family(record.family_id)

    async def get_user(self, user_id: uuid.UUID) -> User:
        user = await self.repository.find_user_by_id(user_id)
        if user is None:
            raise Unauthorized("Account no longer exists", code="TOKEN_INVALID")
        return user

    async def _start_session(
        self,
        user: User,
        family_id: uuid.UUID,
        client: ClientInfo,
        *,
        token_id: uuid.UUID | None = None,
    ) -> IssuedSession:
        refresh_token = security.generate_refresh_token()
        refresh_expires_at = datetime.now(UTC) + timedelta(
            days=self.settings.refresh_token_ttl_days
        )
        await self.repository.add_refresh_token(
            token_id=token_id,
            user_id=user.id,
            family_id=family_id,
            token_hash=security.hash_refresh_token(refresh_token),
            expires_at=refresh_expires_at,
            user_agent=client.user_agent,
            ip=client.ip,
        )
        access = security.create_access_token(
            user.id,
            secret=self.settings.jwt_secret,
            ttl_seconds=self.settings.access_token_ttl_seconds,
        )
        session = AuthSession(
            token=access.token, expires_at=access.expires_at, user=to_auth_user(user)
        )
        return IssuedSession(
            session=session, refresh_token=refresh_token, refresh_expires_at=refresh_expires_at
        )


def _aware(value: datetime) -> datetime:
    """SQLite returns naive datetimes; Postgres returns aware ones. Compare in UTC either way."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)
