"""Application settings, loaded from backend/.env (python-dotenv via pydantic-settings).

Every value is validated at startup: a missing or weak secret stops the server
before it serves a single request. Secrets are SecretStr, so they print as
'**********' in logs, tracebacks and reprs.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_PLACEHOLDER = re.compile(r"change[-_]?me|replace[-_]?me|example|dev-only", re.IGNORECASE)


def _split_csv(value: object) -> object:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── App ─────────────────────────────────────────────────────────────────
    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    trust_proxy: bool = False

    # ── Database ────────────────────────────────────────────────────────────
    # sqlite+aiosqlite:///./.data/dev.db       zero-setup local dev
    # postgresql://…                           Docker / Neon / Supabase (driver added automatically)
    database_url: str = "sqlite+aiosqlite:///./.data/dev.db"
    # Unpooled URL for migrations (Neon host without "-pooler", Supabase port 5432).
    database_direct_url: str | None = None
    # true behind a transaction-mode pooler (Supabase :6543, Neon "-pooler", PgBouncer).
    db_pgbouncer: bool = False
    db_pool_size: int = Field(default=5, ge=1, le=50)
    # Apply Alembic migrations on startup. Convenient locally; run them as a deploy step in prod.
    db_auto_migrate: bool = True

    # ── Auth ────────────────────────────────────────────────────────────────
    jwt_secret: SecretStr
    access_token_ttl_seconds: int = Field(default=900, ge=60, le=3600)
    refresh_token_ttl_days: int = Field(default=30, ge=1, le=90)
    cookie_secure: bool | None = None  # defaults to True in production
    auth_rate_limit_per_minute: int = Field(default=10, ge=1)
    # Google sign-in: OAuth "Web application" Client ID(s) from Google Cloud Console.
    # Not a secret — used to check the ID token was issued for THIS app. Empty = Google off.
    google_client_ids: Annotated[list[str], NoDecode] = []

    # ── LLM gateway (round robin over every key of every provider) ──────────
    # Groq
    groq_api_keys: Annotated[list[SecretStr], NoDecode] = []
    groq_base_url: str = "https://api.groq.com/openai/v1"
    llm_model_large: str = "openai/gpt-oss-120b"  # Groq model ids
    llm_model_fast: str = "openai/gpt-oss-20b"
    # OpenRouter (OpenAI-compatible; model ids from openrouter.ai/models)
    openrouter_api_keys: Annotated[list[SecretStr], NoDecode] = []
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model_large: str = "openai/gpt-oss-120b"
    openrouter_model_fast: str = "openai/gpt-oss-20b"
    # Optional attribution headers OpenRouter shows in its dashboard and rankings.
    openrouter_site_url: str | None = None
    openrouter_app_name: str = "Career Compass"
    llm_timeout_seconds: float = Field(default=30.0, gt=0)

    # ── Live job listings (Job Search agent) ────────────────────────────────
    # Free, keyless remote-job APIs to search (comma-separated; empty = none).
    job_boards: Annotated[list[Literal["jobicy", "remotive"]], NoDecode] = ["jobicy", "remotive"]
    # Optional Adzuna developer keys (https://developer.adzuna.com, free tier) — adds
    # local, city-level listings on top of the free boards.
    adzuna_app_id: str = ""
    adzuna_app_key: SecretStr = SecretStr("")
    # Adzuna country code: in, gb, us, ca, au, de, fr, … (where to search)
    jobs_country: str = Field(default="in", min_length=2, max_length=2)

    # ── Shared knowledge graph ──────────────────────────────────────────────
    # An edge built from user profiles is shown to others only when at least this many
    # distinct users back it (edges backed by a real job posting are always shown).
    graph_min_users: int = Field(default=3, ge=1)

    # ── Agent memory ────────────────────────────────────────────────────────
    memory_recall_limit: int = Field(default=5, ge=0, le=50)
    memory_context_budget_chars: int = Field(default=6000, ge=500)

    @field_validator(
        "cors_origins",
        "groq_api_keys",
        "openrouter_api_keys",
        "google_client_ids",
        "job_boards",
        mode="before",
    )
    @classmethod
    def _csv(cls, value: object) -> object:
        return _split_csv(value)

    @field_validator("jwt_secret")
    @classmethod
    def _secret_length(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return value

    @model_validator(mode="after")
    def _production_guards(self) -> Settings:
        if self.environment != "production":
            return self
        problems = []
        if _PLACEHOLDER.search(self.jwt_secret.get_secret_value()):
            problems.append("JWT_SECRET is a placeholder; generate one (see README)")
        if self.database_url.startswith("sqlite"):
            problems.append("SQLite is for local development only; use Neon or Supabase")
        if problems:
            raise ValueError("; ".join(problems))
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def secure_cookies(self) -> bool:
        return self.cookie_secure if self.cookie_secure is not None else self.is_production


@lru_cache
def get_settings() -> Settings:
    return Settings()  # values come from the environment / .env
