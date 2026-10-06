"""Authentication: sign-up, sign-in, protected routes, refresh rotation, sign-out."""

from __future__ import annotations

import base64
import json

import httpx

from tests.conftest import VALID_USER, Harness

REFRESH = "cc_refresh"


async def _sign_in(h: Harness) -> httpx.Response:
    h.client.cookies.clear()
    return await h.client.post(
        "/api/auth/sign-in", json={"email": VALID_USER["email"], "password": VALID_USER["password"]}
    )


async def _refresh(h: Harness, token: str | None) -> httpx.Response:
    h.client.cookies.clear()
    headers = {"Cookie": f"{REFRESH}={token}"} if token else {}
    return await h.client.post("/api/auth/refresh", headers=headers)


def _cookie(response: httpx.Response) -> str | None:
    return response.cookies.get(REFRESH)


async def test_sign_up_returns_session_and_httponly_cookie(harness: Harness) -> None:
    harness.client.cookies.clear()
    response = await harness.client.post("/api/auth/sign-up", json=VALID_USER)
    assert response.status_code == 201

    body = response.json()
    assert body["success"] is True and body["error"] is None
    assert body["meta"]["requestId"] == response.headers["x-request-id"]
    assert body["data"]["token"].count(".") == 2
    assert body["data"]["user"] == {
        "id": body["data"]["user"]["id"],
        "name": "Ada Lovelace",
        "email": "ada@example.com",  # normalised to lower case
        "isOnboarded": False,
    }
    assert "password" not in response.text.lower()

    set_cookie = response.headers["set-cookie"].lower()
    assert (
        "httponly" in set_cookie and "samesite=lax" in set_cookie and "path=/api/auth" in set_cookie
    )


async def test_duplicate_email_any_case_is_409(harness: Harness) -> None:
    response = await harness.client.post(
        "/api/auth/sign-up", json={**VALID_USER, "email": "ADA@example.com"}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_TAKEN"


async def test_validation_errors_are_per_field(harness: Harness) -> None:
    response = await harness.client.post(
        "/api/auth/sign-up", json={"name": "", "email": "not-an-email", "password": "short"}
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert set(error["details"]) == {"name", "email", "password"}


async def test_malformed_json_is_a_400_envelope(harness: Harness) -> None:
    response = await harness.client.post(
        "/api/auth/sign-up", content="{not json", headers={"content-type": "application/json"}
    )
    assert response.status_code == 400
    assert response.json()["success"] is False


async def test_sign_in_and_identical_errors_for_bad_password_and_unknown_email(
    harness: Harness,
) -> None:
    ok = await _sign_in(harness)
    assert ok.status_code == 200 and _cookie(ok)

    wrong_password = await harness.client.post(
        "/api/auth/sign-in", json={"email": VALID_USER["email"], "password": "nope-nope"}
    )
    unknown_email = await harness.client.post(
        "/api/auth/sign-in", json={"email": "nobody@example.com", "password": "whatever123"}
    )
    for response in (wrong_password, unknown_email):
        assert response.status_code == 401
        assert response.json()["error"] == {
            "code": "INVALID_CREDENTIALS",
            "message": "Invalid email or password",
            "details": None,
        }


async def test_session_requires_a_valid_token(harness: Harness) -> None:
    token = (await _sign_in(harness)).json()["data"]["token"]
    ok = await harness.client.get("/api/auth/session", headers=harness.auth(token))
    assert ok.status_code == 200
    assert ok.json()["data"]["user"]["email"] == "ada@example.com"

    header, payload, signature = token.split(".")
    tampered = f"{header}.{payload}.{signature[:-2]}xx"
    missing = await harness.client.get("/api/auth/session")
    assert missing.json()["error"]["code"] == "TOKEN_MISSING"
    for bad in ("garbage", tampered):
        response = await harness.client.get("/api/auth/session", headers=harness.auth(bad))
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "TOKEN_INVALID"


async def test_unsigned_alg_none_token_is_rejected(harness: Harness) -> None:
    def b64(value: dict[str, str]) -> str:
        return base64.urlsafe_b64encode(json.dumps(value).encode()).rstrip(b"=").decode()

    header = b64({"alg": "none", "typ": "JWT"})
    claims = b64({"sub": "00000000-0000-0000-0000-000000000000"})
    forged = f"{header}.{claims}."  # no signature at all
    response = await harness.client.get("/api/auth/session", headers=harness.auth(forged))
    assert response.status_code == 401


async def test_refresh_rotates_the_token(harness: Harness) -> None:
    first = _cookie(await _sign_in(harness))
    response = await _refresh(harness, first)
    assert response.status_code == 200
    assert response.json()["data"]["token"]
    second = _cookie(response)
    assert second and second != first


async def test_replaying_a_rotated_token_revokes_the_whole_session(harness: Harness) -> None:
    original = _cookie(await _sign_in(harness))
    rotated = _cookie(await _refresh(harness, original))

    replay = await _refresh(harness, original)  # an attacker replays the stolen, used token
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "SESSION_EXPIRED"
    assert "refresh token reuse detected" in harness.logs.getvalue()

    victim = await _refresh(harness, rotated)  # the legitimate holder is signed out too
    assert victim.status_code == 401


async def test_refresh_rejects_missing_or_unknown_tokens(harness: Harness) -> None:
    assert (await _refresh(harness, None)).status_code == 401
    assert (await _refresh(harness, "not-a-real-token")).status_code == 401


async def test_sign_out_revokes_and_clears_cookie(harness: Harness) -> None:
    cookie = _cookie(await _sign_in(harness))
    harness.client.cookies.clear()
    response = await harness.client.post(
        "/api/auth/sign-out", headers={"Cookie": f"{REFRESH}={cookie}"}
    )
    assert response.status_code == 200
    assert response.json()["data"] == {"signedOut": True}
    assert 'cc_refresh=""' in response.headers["set-cookie"]
    assert (await _refresh(harness, cookie)).status_code == 401

    harness.client.cookies.clear()
    assert (await harness.client.post("/api/auth/sign-out")).status_code == 200  # idempotent
