"""Career Compass — BACKEND endpoints (single source of truth).

Every route the API serves is declared here, and the routers import their
paths from this file, so it cannot drift from the real app. A test
(tests/test_endpoints.py) fails if a route exists that isn't listed in
ENDPOINTS, or the other way round.

Frontend counterpart: frontend/src/lib/endpoints.ts (also lists planned endpoints).
Interactive docs for everything below: http://localhost:4000/api/docs
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

API_PREFIX = "/api"

# ── System ───────────────────────────────────────────────────────────────────
HEALTH = "/health"

# ── Auth ─────────────────────────────────────────────────────────────────────
AUTH_SIGN_UP = "/auth/sign-up"
AUTH_SIGN_IN = "/auth/sign-in"
AUTH_REFRESH = "/auth/refresh"
AUTH_SIGN_OUT = "/auth/sign-out"
AUTH_SESSION = "/auth/session"
AUTH_COOKIE_PATH = f"{API_PREFIX}/auth"  # the refresh cookie is only sent to auth routes

# ── Profile ──────────────────────────────────────────────────────────────────
PROFILE = "/profile"

# ── Agents & chat ────────────────────────────────────────────────────────────
AGENTS = "/agents"
CHAT_CONVERSATIONS = "/chat/conversations"
CHAT_CONVERSATION = "/chat/conversations/{conversation_id}"
CHAT_ORCHESTRATE = "/chat/orchestrate"


@dataclass(frozen=True)
class Endpoint:
    method: Literal["GET", "POST", "PATCH", "PUT", "DELETE"]
    path: str  # relative to API_PREFIX
    auth: Literal["public", "bearer", "refresh-cookie"]
    summary: str

    @property
    def url(self) -> str:
        return f"{API_PREFIX}{self.path}"


ENDPOINTS: tuple[Endpoint, ...] = (
    # System
    Endpoint("GET", HEALTH, "public", "Liveness, database status, LLM key pool health"),
    # Auth
    Endpoint("POST", AUTH_SIGN_UP, "public", "Create account → access token + refresh cookie"),
    Endpoint("POST", AUTH_SIGN_IN, "public", "Sign in → access token + refresh cookie"),
    Endpoint("POST", AUTH_REFRESH, "refresh-cookie", "Rotate refresh cookie → new access token"),
    Endpoint("POST", AUTH_SIGN_OUT, "refresh-cookie", "Revoke this session, clear the cookie"),
    Endpoint("GET", AUTH_SESSION, "bearer", "The signed-in user"),
    # Profile
    Endpoint("GET", PROFILE, "bearer", "Career profile (created empty on first read)"),
    Endpoint("PATCH", PROFILE, "bearer", "Update any profile fields"),
    # Agents & chat
    Endpoint("GET", AGENTS, "bearer", "The agent catalogue (id, name, description, reads)"),
    Endpoint("GET", CHAT_CONVERSATIONS, "bearer", "The user's conversations, newest first"),
    Endpoint("POST", CHAT_CONVERSATIONS, "bearer", "Start an empty conversation"),
    Endpoint("GET", CHAT_CONVERSATION, "bearer", "One conversation with its messages"),
    Endpoint(
        "POST",
        CHAT_ORCHESTRATE,
        "bearer",
        "Run the agents for a message; streams SSE: plan, step, answer, memory, done",
    ),
)
