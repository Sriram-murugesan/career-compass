"""Cross-cutting platform behaviour: config, database URLs, envelopes, security, logging."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.logging import redact
from app.db.session import normalize_database_url
from tests.conftest import VALID_USER, Harness, make_settings, running_app

# ── Config ──────────────────────────────────────────────────────────────────


def test_short_secret_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="at least 32 characters"):
        make_settings(tmp_path, jwt_secret="short")


def test_production_rejects_placeholder_secret_and_sqlite(tmp_path: Path) -> None:
    with pytest.raises(ValidationError) as error:
        make_settings(
            tmp_path,
            environment="production",
            jwt_secret="dev-only-change-me-to-a-long-random-string-please",
        )
    assert "placeholder" in str(error.value) and "SQLite" in str(error.value)


def test_csv_env_values_and_llm_keys_are_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GROQ_API_KEYS", " gsk_one , gsk_two ,,")
    monkeypatch.setenv("CORS_ORIGINS", "http://a.test,http://b.test")
    settings = _from_env(tmp_path)
    assert [key.get_secret_value() for key in settings.groq_api_keys] == ["gsk_one", "gsk_two"]
    assert settings.cors_origins == ["http://a.test", "http://b.test"]
    assert "gsk_one" not in repr(settings)  # SecretStr never prints


def _from_env(tmp_path: Path) -> Settings:
    """Settings read from the (monkeypatched) environment, never from backend/.env."""
    return Settings(
        _env_file=None,
        jwt_secret="x" * 40,
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'c.db').as_posix()}",
    )


# ── Database URLs (Neon / Supabase) ─────────────────────────────────────────


def test_neon_url_is_translated_for_asyncpg() -> None:
    url, args = normalize_database_url(
        "postgresql://u:p@ep-x-pooler.eu.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    )
    assert url == "postgresql+asyncpg://u:p@ep-x-pooler.eu.aws.neon.tech/neondb"
    assert args == {"ssl": "require"}


def test_supabase_and_plain_postgres_urls() -> None:
    url, args = normalize_database_url(
        "postgres://postgres.abc:pw@aws-0-eu.pooler.supabase.com:6543/postgres?sslmode=require"
    )
    assert url.startswith("postgresql+asyncpg://") and ":6543/postgres" in url
    assert args == {"ssl": "require"}
    url, args = normalize_database_url("postgresql://career:career@localhost:5432/career_compass")
    assert url == "postgresql+asyncpg://career:career@localhost:5432/career_compass" and args == {}


# ── HTTP platform ───────────────────────────────────────────────────────────


async def test_health_reports_database_and_llm_pool(harness: Harness) -> None:
    response = await harness.client.get("/api/health")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "ok" and data["database"] == "up" and data["llmEntries"] == []


async def test_unknown_route_is_a_404_envelope(harness: Harness) -> None:
    response = await harness.client.get("/api/nope?x=1")
    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "NOT_FOUND",
        "message": "Route GET /api/nope not found",
        "details": None,
    }


async def test_security_headers_and_cors_allow_list(harness: Harness) -> None:
    response = await harness.client.get("/api/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "default-src 'none'" in response.headers["content-security-policy"]

    preflight = {"access-control-request-method": "POST"}
    allowed = await harness.client.options(
        "/api/auth/sign-in", headers={"origin": "http://localhost:3000", **preflight}
    )
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert allowed.headers["access-control-allow-credentials"] == "true"
    blocked = await harness.client.options(
        "/api/auth/sign-in", headers={"origin": "https://evil.example", **preflight}
    )
    assert "access-control-allow-origin" not in blocked.headers


async def test_logs_never_contain_passwords_tokens_or_cookies(harness: Harness) -> None:
    session = await harness.sign_up(email="logs@example.com")
    token = session["token"]
    await harness.client.get(
        "/api/auth/session", headers={**harness.auth(token), "Cookie": "cc_refresh=abc123secret"}
    )
    logs = harness.logs.getvalue()
    assert "user signed up" in logs  # logging works…
    assert VALID_USER["password"] not in logs  # …secrets never appear
    assert token not in logs
    assert "abc123secret" not in logs


def test_redaction_scrubs_keys_and_patterns() -> None:
    scrubbed = redact(
        {
            "password": "hunter2",
            "nested": {"apiKey": "gsk_live"},
            "note": "Bearer abc.def.ghi and gsk_abcdef and cc_refresh=zzz",
        }
    )
    assert scrubbed["password"] == "[REDACTED]"
    assert scrubbed["nested"]["apiKey"] == "[REDACTED]"
    assert "abc.def" not in scrubbed["note"] and "gsk_abcdef" not in scrubbed["note"]
    assert "zzz" not in scrubbed["note"]


async def test_auth_routes_are_rate_limited(tmp_path: Path) -> None:
    async with running_app(make_settings(tmp_path, auth_rate_limit_per_minute=3)) as h:
        payload = {"email": "a@b.co", "password": "x"}
        statuses = [
            (await h.client.post("/api/auth/sign-in", json=payload)).status_code for _ in range(4)
        ]
        assert statuses == [401, 401, 401, 429]
        limited = await h.client.post("/api/auth/sign-in", json=payload)
        assert limited.json()["error"]["code"] == "RATE_LIMITED"
        assert (await h.client.get("/api/health")).status_code == 200  # other routes unaffected
