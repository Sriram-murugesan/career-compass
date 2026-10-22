"""Google sign-in: verify the ID token the "Sign in with Google" button returns.

The browser gets a signed JWT (the "credential") from Google and posts it to
POST /api/auth/google. We trust it only after checking, locally:
  - signature: RS256, against Google's published public keys (JWKS, cached)
  - aud:       one of OUR client ids, so a token minted for another app is useless here
  - iss:       accounts.google.com
  - exp / iat: not expired (60 s clock leeway)
  - email_verified: true, because we link accounts by email
No client secret is involved, so there is no secret to leak.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Protocol

import jwt

GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")


@dataclass(frozen=True)
class GoogleIdentity:
    sub: str  # Google's stable user id — never changes, unlike the email
    email: str
    name: str
    picture: str | None


class GoogleTokenInvalid(Exception):
    """The credential is not a valid Google ID token for this app."""


class SigningKeySource(Protocol):
    """Where public keys come from (Google's JWKS in production, a test key in tests)."""

    def get_signing_key_from_jwt(self, token: str) -> Any: ...


class GoogleTokenVerifier:
    def __init__(self, client_ids: list[str], keys: SigningKeySource | None = None) -> None:
        self.client_ids = client_ids
        # PyJWKClient caches Google's keys and refetches when a new key id appears.
        self._keys: SigningKeySource = keys or jwt.PyJWKClient(
            GOOGLE_JWKS_URL, cache_keys=True, lifespan=3600, timeout=10
        )

    @property
    def enabled(self) -> bool:
        return bool(self.client_ids)

    async def verify(self, credential: str) -> GoogleIdentity:
        # The JWKS fetch is blocking I/O (only on a cache miss): keep it off the event loop.
        return await asyncio.to_thread(self._verify_sync, credential)

    def _verify_sync(self, credential: str) -> GoogleIdentity:
        try:
            signing_key = self._keys.get_signing_key_from_jwt(credential)
            claims: dict[str, Any] = jwt.decode(
                credential,
                signing_key.key,
                algorithms=["RS256"],  # pinned: Google signs ID tokens with RS256 only
                audience=self.client_ids,
                issuer=GOOGLE_ISSUERS,
                leeway=60,
                options={"require": ["sub", "email", "exp", "iat", "aud", "iss"]},
            )
        except (jwt.PyJWTError, ValueError) as exc:
            raise GoogleTokenInvalid(str(exc)) from exc

        if claims.get("email_verified") is not True:
            raise GoogleTokenInvalid("Google account email is not verified")
        email = str(claims["email"]).strip().lower()
        return GoogleIdentity(
            sub=str(claims["sub"]),
            email=email,
            name=str(claims.get("name") or email.split("@")[0])[:100],
            picture=claims.get("picture"),
        )
