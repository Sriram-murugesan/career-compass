"""Credential primitives — pure functions, no database, no HTTP.

- Passwords: Argon2id with the OWASP minimum parameters (19 MiB, t=2, p=1).
- Access tokens: HS256 JWT, short-lived, algorithm pinned on verify.
- Refresh tokens: 256 random bits; only their SHA-256 hash is ever stored.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_ISSUER = "career-compass-api"
_AUDIENCE = "career-compass-web"
_hasher = PasswordHasher(time_cost=2, memory_cost=19_456, parallelism=1)
_DUMMY_HASH = _hasher.hash("timing-equalizer-not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def burn_password_check(password: str) -> None:
    """Spend the same time as a real verify — used when the account doesn't exist."""
    verify_password(_DUMMY_HASH, password)


@dataclass(frozen=True)
class AccessToken:
    token: str
    expires_at: datetime


def create_access_token(user_id: uuid.UUID, *, secret: str, ttl_seconds: int) -> AccessToken:
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=ttl_seconds)
    token = jwt.encode(
        {
            "sub": str(user_id),
            "iss": _ISSUER,
            "aud": _AUDIENCE,
            "iat": now,
            "exp": expires_at,
            "jti": str(uuid.uuid4()),
        },
        secret,
        algorithm="HS256",
    )
    return AccessToken(token=token, expires_at=expires_at)


def decode_access_token(token: str, *, secret: str) -> uuid.UUID | None:
    """User id from a valid token; None for anything invalid, expired, tampered or unsigned."""
    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],  # pinned: rejects "none" and algorithm-confusion tokens
            audience=_AUDIENCE,
            issuer=_ISSUER,
            options={"require": ["sub", "exp", "iat"]},
        )
        return uuid.UUID(claims["sub"])
    except (jwt.InvalidTokenError, ValueError):
        return None


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    # SHA-256 suffices: the token is 256 bits of randomness, not a guessable password.
    return hashlib.sha256(token.encode()).hexdigest()
