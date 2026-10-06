# Career Compass — Backend (FastAPI)

The backend is one FastAPI process, built as a **modular monolith** with boundaries that a linter enforces. It uses SQLAlchemy 2 (async) with Alembic migrations, and it's ready for **Neon** or **Supabase**. Seven **LangGraph** agents share one state and a three-tier memory, and they reach the LLMs through a **round-robin gateway** over your Groq keys.

## Quick start

```bash
cd backend
uv sync                              # creates .venv with all dependencies
cp .env.example .env                 # then edit; .env is git-ignored
uv run uvicorn app.main:create_app --factory --reload --port 4000
```

Then try:
- http://localhost:4000/api/health
- http://localhost:4000/api/docs (interactive Swagger docs)

From the repo root, `npm run dev` starts the frontend and the backend together.

The defaults need nothing installed:
- **Database:** a local SQLite file (`.data/dev.db`), migrated automatically on start.
- **No LLM keys:** every agent falls back to a deterministic offline answer, so the whole pipeline still runs.

| Command (inside `backend/`) | Does |
| --- | --- |
| `uv run pytest` | 43 tests: auth, LLM gateway, agent graph, shared memory, API, platform |
| `uv run ruff check . && uv run ruff format --check .` | Lint + formatting |
| `uv run mypy app tests` | Strict type checking |
| `uv run lint-imports` | **Architecture rules** (see below) |
| `uv run alembic revision --autogenerate -m "msg"` | New migration after editing models |
| `uv run alembic upgrade head` | Apply migrations (uses `DATABASE_DIRECT_URL` if set) |

## Folder structure

```text
backend/
├── app/
│   ├── main.py                 # composition root: create_app() wires every module
│   ├── model_registry.py       # imports all models for Alembic
│   │
│   ├── core/                   # cross-cutting infrastructure (never imports features)
│   │   ├── config.py           # .env → validated Settings (secrets are SecretStr)
│   │   ├── security.py         # Argon2id, JWT, refresh-token primitives (pure functions)
│   │   ├── errors.py           # AppError family (no FastAPI types)
│   │   ├── handlers.py         # every error → standard envelope
│   │   ├── responses.py        # Envelope[T]  { success, data, error, meta.requestId }
│   │   ├── schema.py           # ApiModel: snake_case in Python, camelCase on the wire
│   │   ├── logging.py          # JSON/readable logs + secret redaction
│   │   ├── middleware.py       # request id, access log, security headers (SSE-safe)
│   │   └── rate_limit.py       # sliding-window limiter for auth routes
│   │
│   ├── db/                     # SQLAlchemy plumbing (never imports features)
│   │   ├── base.py             # DeclarativeBase + naming convention, UUID/timestamp mixins
│   │   ├── session.py          # async engine; Neon/Supabase URL handling; unit of work
│   │   ├── migrations.py       # run Alembic from code
│   │   └── dependencies.py     # get_session (one transaction per request)
│   │
│   ├── modules/                # BUSINESS MODULES — each one is layered the same way
│   │   ├── auth/
│   │   │   ├── router.py        # HTTP layer
│   │   │   ├── dependencies.py  # wiring + CurrentUserId (protects any route)
│   │   │   ├── service.py       # business layer  (no FastAPI, no SQLAlchemy)
│   │   │   ├── repository.py    # data layer      (the only SQL)
│   │   │   ├── models.py        # SQLAlchemy tables
│   │   │   ├── schemas.py       # Pydantic request/response models
│   │   │   └── __init__.py      # public interface: the ONLY import path for other modules
│   │   ├── profile/            # same layout
│   │   ├── chat/               # same layout; runs the agents and streams SSE
│   │   └── health/
│   │
│   ├── agents/                 # ONE FOLDER PER AGENT (never import each other)
│   │   ├── base.py             # the contract: AgentSpec, AgentContext → AgentResult
│   │   ├── registry.py         # the list of agents
│   │   ├── job_search/  resume/  validation/  productivity/
│   │   └── roadmap/  advisor/  interview/
│   │       └── (each) agent.py · prompt.py · schema.py · __init__.py
│   │
│   ├── orchestrator/           # LangGraph wiring
│   │   ├── state.py            # CareerState + reducer functions
│   │   ├── planner.py          # supervisor: which agents, in which stages
│   │   ├── graph.py            # the StateGraph
│   │   └── runner.py           # runs a turn, turns the graph stream into UI events
│   │
│   ├── memory/                 # shared memory for agents
│   │   ├── models.py           # agent_memories table (long-term facts per user)
│   │   ├── store.py            # recall() / remember(), deduplicated
│   │   └── context.py          # ContextBuilder: what each agent sees, within a budget
│   │
│   └── llm/                    # round-robin LLM gateway
│       ├── pool.py             # (key, model, tier) entries from .env
│       ├── gateway.py          # rotation, cooldown, failover, circuit breaker
│       └── errors.py
│
├── alembic/                    # migrations (async env; SQLite + Postgres)
├── tests/
├── .env.example
└── pyproject.toml              # deps (uv), ruff, mypy, pytest, import-linter rules
```

## Layers and the rules that enforce them

```text
router.py ──▶ service.py ──▶ repository.py ──▶ models.py ──▶ database
  HTTP          business        data access       tables
                rules only      (all SQL)
```

`uv run lint-imports` fails the build if any of these break:

1. **Layers.** Inside a module, imports only point downward: router → dependencies → service → repository → models.
2. **Clean business layer.** `service.py` never imports FastAPI or SQLAlchemy.
3. **Core stays generic.** `core/` and `db/` never import modules, agents, the orchestrator, memory or the LLM gateway.
4. **Agents don't talk to each other.** No agent imports another agent.
5. **Agents don't touch infrastructure.** Agents never import the database, SQLAlchemy, FastAPI or any module.

Cross-module use goes through a module's `__init__.py`. For example, routes are protected with `from app.modules.auth import CurrentUserId`, and chat reads the profile through `ProfileService`.

## Authentication

| Endpoint | Auth | Result |
| --- | --- | --- |
| `POST /api/auth/sign-up` | none | 201 session + refresh cookie |
| `POST /api/auth/sign-in` | none | session + refresh cookie |
| `POST /api/auth/refresh` | refresh cookie | new session + **rotated** cookie |
| `POST /api/auth/sign-out` | refresh cookie | session revoked, cookie cleared |
| `GET /api/auth/session` | Bearer token | current user |

Any route becomes protected by adding `user_id: CurrentUserId` to its parameters.

How it protects users:

- **Passwords:** Argon2id with the OWASP parameters.
- **Access tokens:** 15-minute HS256 JWTs. Verification is pinned to HS256, so unsigned `alg: none` tokens are rejected.
- **Refresh tokens:** 256 random bits in an `httpOnly`, `SameSite=Lax` cookie scoped to `/api/auth`. Only a SHA-256 hash is stored in the database.
- **Rotation with theft detection:** every refresh replaces the refresh token. If an already-used token comes back, every token from that sign-in is revoked and a warning is logged.
- **No account probing:** a wrong password and an unknown email return the same 401 after the same amount of work.
- **Rate limits:** sign-up, sign-in and refresh are limited per IP; the default is 10 per minute.

## The agents and their shared memory

```text
POST /api/chat/orchestrate {"message": "tailor my resume for a role and validate it"}

  load_memory → supervisor → dispatch ─▶ [job_search] ─▶ dispatch ─▶ [resume] ─▶ dispatch
                                       ─▶ [validation] ─▶ dispatch ─▶ respond → save_memory
```

- **Agents never call each other.** Each one is a node that reads `CareerState` and returns a partial update.
- **Reducers merge the updates:**
  - `agent_outputs` merges dictionaries.
  - `steps`, `memory_writes` and `errors` are appended to.
- **Parallel stages are safe.** Agents in the same stage run at once. A single `dispatch` join routes after each stage, so it always sees the merged state.
- **Dependencies set the order.** An agent declares what it reads (`reads=("resume",)`), and the planner schedules it after those agents.
- **Planning:** with LLM keys configured, the LLM plans from the agents' descriptions. Without keys, keyword rules decide.
- **Live progress:** the run streams to the browser as Server-Sent Events: `plan`, `step` (running, completed or failed), `answer`, `memory` and `done`.

**Three memory tiers, all shared by every agent:**

| Tier | Where | Lifetime | Example |
| --- | --- | --- | --- |
| Working | `CareerState` (reducers) | one run | Resume reads Job Search's match in the same run |
| Conversation | LangGraph checkpointer (thread = conversation id) + messages in the DB | the conversation | Turn 2's interview prep uses turn 1's job search |
| Long-term | `agent_memories` table | the user, across all conversations | "Exploring roles: Data Engineer" recalled in a new chat |

`ContextBuilder` assembles each agent's prompt in priority order within `MEMORY_CONTEXT_BUDGET_CHARS`: the request, then the profile, then outputs from agents it reads, then recalled memories, then recent messages.

**Adding an agent:**
1. Copy any folder in `app/agents/`.
2. Edit its `schema.py`, `prompt.py` and `agent.py`. Every agent needs a `_fallback` that works without an LLM.
3. Add its `SPEC` to `registry.py`. The graph, the planner and `/api/agents` pick it up automatically.

## LLM gateway

- **Keys:** `GROQ_API_KEYS=gsk_a,gsk_b,gsk_c` in `.env`. Each key serves both tiers: `large` uses gpt-oss-120b and `fast` uses gpt-oss-20b.
- **Rotation:** calls go round robin across the keys, with the following failover rules.

| Event | Action |
| --- | --- |
| 429 | Cool that key for `Retry-After` (else 2 s doubling, max 60 s); retry on the next key at once |
| 5xx / timeout | Next key; 3 failures in a row open the circuit for 30 s |
| 401 / 403 | Disable that key until restart; log a warning (key id only) |
| Other 4xx | No retry — the request itself is wrong |
| All keys exhausted | `LlmUnavailable` → the agent returns its offline fallback; the run still completes |

**Secrets:** keys are `SecretStr` values. They never appear in `/api/health`, in `repr()` or in any log line. The log redaction filter also scrubs `gsk_…`, JWTs, bearer tokens and the refresh cookie.

## Database workflow (local → Neon / Supabase)

| Stage | `DATABASE_URL` | Also set |
| --- | --- | --- |
| Local, zero setup | `sqlite+aiosqlite:///./.data/dev.db` | — |
| Local Docker | `postgresql://career:career@localhost:5432/career_compass` (`docker compose up -d db` from repo root) | — |
| Neon | pooled URL (host has `-pooler`) `?sslmode=require` | `DB_PGBOUNCER=true`, `DATABASE_DIRECT_URL` = non-pooler URL |
| Supabase | pooler URL on port **6543** `?sslmode=require` | `DB_PGBOUNCER=true`, `DATABASE_DIRECT_URL` = port **5432** URL |

**Provider connection strings work as pasted.** `app/db/session.py` translates them for asyncpg: it removes `sslmode`/`channel_binding`, enables TLS, and turns off prepared statements behind a pooler.

**Schema changes:**
1. Edit a module's `models.py`.
2. Run `uv run alembic revision --autogenerate -m "…"`, review the generated file in `alembic/versions/`, and commit it.
3. In production, run `alembic upgrade head` as a deploy step. Set `DB_AUTO_MIGRATE=false` there and always migrate over the direct URL.

**Next for memory:** Phase 3 swaps two pieces behind the existing interfaces, so no agent code changes:
- the in-process checkpointer becomes `AsyncPostgresSaver`;
- keyword recall becomes pgvector similarity search.
