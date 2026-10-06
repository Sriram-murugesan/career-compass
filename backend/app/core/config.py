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

    # ── LLM gateway (round robin over every key) ────────────────────────────
    groq_api_keys: Annotated[list[SecretStr], NoDecode] = []
    groq_base_url: str = "https://api.groq.com/openai/v1"
    llm_model_large: str = "openai/gpt-oss-120b"
    llm_model_fast: str = "openai/gpt-oss-20b"
    llm_timeout_seconds: float = Field(default=30.0, gt=0)

    # ── Agent memory ────────────────────────────────────────────────────────
    memory_recall_limit: int = Field(default=5, ge=0, le=50)
    memory_context_budget_chars: int = Field(default=6000, ge=500)

    @field_validator("cors_origins", "groq_api_keys", mode="before")
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
