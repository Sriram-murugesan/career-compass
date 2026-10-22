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
AUTH_GOOGLE = "/auth/google"
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

# ── Interview: mock tests ────────────────────────────────────────────────────
INTERVIEW_MOCK_TESTS = "/interview/mock-tests"
INTERVIEW_MOCK_TEST = "/interview/mock-tests/{test_id}"
INTERVIEW_MOCK_TEST_ATTEMPTS = "/interview/mock-tests/{test_id}/attempts"

# ── Productivity tracker ─────────────────────────────────────────────────────
PRODUCTIVITY_OVERVIEW = "/productivity/overview"
PRODUCTIVITY_HABITS = "/productivity/habits"
PRODUCTIVITY_HABIT = "/productivity/habits/{habit_id}"
PRODUCTIVITY_HABIT_LOG = "/productivity/habits/{habit_id}/logs/{day}"

# ── Shared knowledge graph ───────────────────────────────────────────────────
GRAPH_ME = "/graph/me"
GRAPH_NODE = "/graph/nodes/{kind}/{key}"
GRAPH_SEARCH = "/graph/search"
GRAPH_PATHS = "/graph/paths"


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
    Endpoint(
        "POST",
        AUTH_GOOGLE,
        "public",
        "Sign in / sign up with a Google ID token → access token + refresh cookie",
    ),
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
    Endpoint("DELETE", CHAT_CONVERSATION, "bearer", "Delete a conversation and its messages"),
    Endpoint(
        "POST",
        CHAT_ORCHESTRATE,
        "bearer",
        "Run the agents for a message; streams SSE: plan, step, answer, memory, done",
    ),
    # Interview: mock tests
    Endpoint(
        "POST",
        INTERVIEW_MOCK_TESTS,
        "bearer",
        "Generate a multiple-choice mock test for a role + domain (answers kept server-side)",
    ),
    Endpoint("GET", INTERVIEW_MOCK_TESTS, "bearer", "Your mock tests with best / last scores"),
    Endpoint(
        "GET", INTERVIEW_MOCK_TEST, "bearer", "One mock test (questions, no answers) + attempts"
    ),
    Endpoint(
        "POST",
        INTERVIEW_MOCK_TEST_ATTEMPTS,
        "bearer",
        "Submit answers → instant score, topic breakdown, correct answers + explanations",
    ),
    # Productivity tracker
    Endpoint(
        "GET",
        PRODUCTIVITY_OVERVIEW,
        "bearer",
        "Habits with streaks + week progress, 28-day heatmap, mock-test-linked learning (?today=)",
    ),
    Endpoint(
        "POST", PRODUCTIVITY_HABITS, "bearer", "Track a habit (or a mock-test topic to learn)"
    ),
    Endpoint("PATCH", PRODUCTIVITY_HABIT, "bearer", "Rename / retarget / archive a habit"),
    Endpoint("DELETE", PRODUCTIVITY_HABIT, "bearer", "Delete a habit and its check-ins"),
    Endpoint("PUT", PRODUCTIVITY_HABIT_LOG, "bearer", "Check in for a day ({ minutes?, note? })"),
    Endpoint("DELETE", PRODUCTIVITY_HABIT_LOG, "bearer", "Undo a day's check-in"),
    # Shared knowledge graph
    Endpoint(
        "GET",
        GRAPH_ME,
        "bearer",
        "Your links (private) + shared insights around your roles and skills",
    ),
    Endpoint("GET", GRAPH_NODE, "bearer", "A shared node (skill/role/company) and its neighbours"),
    Endpoint("GET", GRAPH_SEARCH, "bearer", "Find shared nodes by name (?q=&kind=)"),
    Endpoint("GET", GRAPH_PATHS, "bearer", "Career paths from a role along leads_to (?role=)"),
)
