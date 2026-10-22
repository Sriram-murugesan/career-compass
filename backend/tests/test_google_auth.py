"""Google sign-in: ID-token verification, account creation/linking, and takeover protection.

Tokens are real RS256 JWTs signed with a test key that stands in for Google's,
so the whole verification path (signature, audience, issuer, expiry,
email_verified) runs exactly as in production, without the network.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from tests.conftest import Harness, make_settings, running_app

CLIENT_ID = "test-client.apps.googleusercontent.com"
GOOGLE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
ATTACKER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class FakeGoogleKeys:
    """Plays Google's JWKS endpoint: always hands back Google's (test) public key."""

    def get_signing_key_from_jwt(self, token: str) -> Any:
        return SimpleNamespace(key=GOOGLE_KEY.public_key())


def google_token(
    *,
    sub: str = "google-sub-1",
    email: str = "ada@gmail.com",
    key: Any = GOOGLE_KEY,
    algorithm: str = "RS256",
    **overrides: Any,
) -> str:
    now = int(time.time())
    claims = {
        "iss": "https://accounts.google.com",
        "aud": CLIENT_ID,
        "sub": sub,
        "email": email,
        "email_verified": True,
        "name": "Ada Lovelace",
        "picture": "https://lh3.googleusercontent.com/a/ada",
        "iat": now,
        "exp": now + 3600,
        **overrides,
    }
    return jwt.encode(claims, key, algorithm=algorithm, headers={"kid": "test-kid"})


@pytest.fixture(scope="module")
async def h(tmp_path_factory: pytest.TempPathFactory) -> AsyncIterator[Harness]:
    settings = make_settings(tmp_path_factory.mktemp("google"), google_client_ids=[CLIENT_ID])
    async with running_app(settings, google_keys=FakeGoogleKeys()) as harness:
        yield harness


async def google_sign_in(h: Harness, credential: str) -> httpx.Response:
    h.client.cookies.clear()
    return await h.client.post("/api/auth/google", json={"credential": credential})


# ── Happy paths ─────────────────────────────────────────────────────────────


async def test_first_google_sign_in_creates_a_verified_passwordless_account(h: Harness) -> None:
    response = await google_sign_in(h, google_token())
    assert response.status_code == 200, response.text
    user = response.json()["data"]["user"]
    assert user["email"] == "ada@gmail.com"
    assert user["name"] == "Ada Lovelace"
    assert user["avatarUrl"] == "https://lh3.googleusercontent.com/a/ada"
    assert user["googleLinked"] is True and user["hasPassword"] is False
    assert response.cookies.get("cc_refresh")  # same session model as password login

    token = response.json()["data"]["token"]
    session = await h.client.get("/api/auth/session", headers=h.auth(token))
    assert session.json()["data"]["user"]["id"] == user["id"]


async def test_signing_in_again_returns_the_same_account(h: Harness) -> None:
    first = (await google_sign_in(h, google_token(sub="repeat", email="repeat@gmail.com"))).json()
    again = (await google_sign_in(h, google_token(sub="repeat", email="repeat@gmail.com"))).json()
    assert first["data"]["user"]["id"] == again["data"]["user"]["id"]


async def test_google_only_account_cannot_use_password_sign_in(h: Harness) -> None:
    await google_sign_in(h, google_token(sub="gonly", email="gonly@gmail.com"))
    response = await h.client.post(
        "/api/auth/sign-in", json={"email": "gonly@gmail.com", "password": "anything123"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"  # same answer as any miss


# ── Token verification ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "credential",
    [
        google_token(aud="someone-elses-app.apps.googleusercontent.com"),  # minted for another app
        google_token(iss="https://evil.example"),  # not Google
        google_token(exp=int(time.time()) - 3600, iat=int(time.time()) - 7200),  # expired
        google_token(key=ATTACKER_KEY),  # forged signature
        google_token(key="a-shared-secret-attacker-knows-xx", algorithm="HS256"),  # alg swap
        google_token(email_verified=False),  # unverified email
        "not.a.jwt.at.all.but.long.enough",
    ],
    ids=["wrong-audience", "wrong-issuer", "expired", "forged", "hs256", "unverified", "garbage"],
)
async def test_invalid_google_tokens_are_rejected(h: Harness, credential: str) -> None:
    response = await google_sign_in(h, credential)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "GOOGLE_TOKEN_INVALID"


# ── Account linking ─────────────────────────────────────────────────────────


async def test_google_takes_over_a_preregistered_account_and_locks_out_the_squatter(
    h: Harness,
) -> None:
    # An attacker registers the victim's address with a password (we never verified it)…
    squat = await h.sign_up(email="victim@gmail.com", password="attacker-password", name="X")
    squat_cookie = None
    h.client.cookies.clear()
    signed_in = await h.client.post(
        "/api/auth/sign-in", json={"email": "victim@gmail.com", "password": "attacker-password"}
    )
    squat_cookie = signed_in.cookies.get("cc_refresh")
    assert squat_cookie

    # …then the real owner signs in with Google.
    owner = await google_sign_in(h, google_token(sub="victim-sub", email="victim@gmail.com"))
    assert owner.status_code == 200
    linked = owner.json()["data"]["user"]
    assert linked["id"] == squat["user"]["id"]  # same account, now owned via Google
    assert linked["googleLinked"] is True and linked["hasPassword"] is False

    # The attacker's password and existing session no longer work.
    h.client.cookies.clear()
    password_again = await h.client.post(
        "/api/auth/sign-in", json={"email": "victim@gmail.com", "password": "attacker-password"}
    )
    assert password_again.status_code == 401
    h.client.cookies.clear()
    refresh = await h.client.post(
        "/api/auth/refresh", headers={"Cookie": f"cc_refresh={squat_cookie}"}
    )
    assert refresh.status_code == 401


async def test_email_already_linked_to_another_google_account_is_a_conflict(h: Harness) -> None:
    await google_sign_in(h, google_token(sub="owner-a", email="shared@gmail.com"))
    response = await google_sign_in(h, google_token(sub="owner-b", email="shared@gmail.com"))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ACCOUNT_CONFLICT"


# ── Configuration ───────────────────────────────────────────────────────────


async def test_google_sign_in_is_off_without_a_client_id(tmp_path: Path) -> None:
    async with running_app(make_settings(tmp_path)) as plain:
        response = await plain.client.post("/api/auth/google", json={"credential": google_token()})
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "GOOGLE_SIGN_IN_DISABLED"
