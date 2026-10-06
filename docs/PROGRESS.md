# Career Compass — Interim Progress Log

Newest entry first. Each entry says what changed, how it was verified, and what is waiting on you.

---

## 2026-10-06 (latest) — One endpoints file per side, README workflow, branch pushed

- **Frontend:** `frontend/src/lib/endpoints.ts` holds every page route (`PAGE_ROUTES`) and every backend call (`API_ENDPOINTS`), each marked `[live]` or `[planned]`.
- **Backend:** `backend/app/endpoints.py` holds every served route. The routers import their paths from it, and `tests/test_endpoints.py` fails if the file and the running app differ. A second test checks that every bearer endpoint rejects anonymous calls.
- **Shared package removed:** `packages/contracts` was dropped because the backend is Python. Its response templates moved to `frontend/src/lib/api-templates.ts` and its auth schemas to `frontend/src/lib/schemas/`.
- **README:** rewritten around the workflow: structure, endpoints, setup, daily checks, how to add pages, endpoints, modules and agents, the database workflow, and the git workflow.
- **Verified:**
  - backend: 45/45 tests pass; strict mypy, ruff and lint-imports are clean;
  - frontend: typecheck clean, production build passes.
- **Git:** committed to the new branch `backend-boiler-template`.

---

## 2026-10-06 (later) — Backend rebuilt in Python: FastAPI + SQLAlchemy + LangGraph agents

**Status:** done and verified locally. Not committed — waiting for your review.

**Replaces the TypeScript backend below.** You wanted FastAPI, but the plan's decision table had recommended TypeScript and that was taken as approved. The TypeScript version is removed from `backend/`. A copy is kept outside the repo for this session only.

### What changed

| Area | Change |
| --- | --- |
| Stack | Python 3.11, FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic, LangGraph 1.2, httpx; managed with `uv` |
| Modular monolith | `app/modules/{auth,profile,chat,health}`, each split into router → dependencies → service → repository → models, plus Pydantic schemas and a public `__init__.py` |
| Enforced boundaries | `lint-imports`: 5 rules (module layers; services have no FastAPI/SQL; core never imports features; agents never import each other; agents never touch DB/HTTP) |
| Auth (separate module) | Sign-up/in/refresh/sign-out/session; Argon2id; 15-min JWT; rotating httpOnly refresh cookie with theft detection; per-IP rate limit; `CurrentUserId` protects any route |
| Agents | 7 agent folders (`agent.py`, `prompt.py`, `schema.py`, `__init__.py`) + `registry.py`. Each uses the LLM when available and a deterministic fallback otherwise |
| Orchestrator | LangGraph `StateGraph`: load_memory → supervisor (plans stages by dependency) → parallel agent stages via a `dispatch` join → respond → save_memory. Streams SSE: plan / step / answer / memory / done |
| Shared memory | **Working** (graph state + reducers), **conversation** (checkpointer per conversation + messages in DB), **long-term** (`agent_memories` table, per user, deduplicated); `ContextBuilder` budgets what each agent sees |
| LLM gateway | Round robin over `GROQ_API_KEYS`; 429 cooldown, 401 disable, circuit breaker, JSON-schema validation with one retry; keys are `SecretStr`, never logged |
| Database | SQLite file by default (zero setup); Neon / Supabase / Docker Postgres by changing `DATABASE_URL`. Their URLs are translated for asyncpg (TLS, pooler-safe statements); migrations use `DATABASE_DIRECT_URL` |
| Secrets | `backend/.env` (git-ignored), validated at startup; production refuses placeholder secrets and SQLite |
| Logging | Request id on every line and response; secrets redacted (passwords, tokens, cookies, `gsk_` keys, JWTs) |
| API surface | `/api/health`, `/api/auth/*`, `/api/profile`, `/api/agents`, `/api/chat/conversations`, `/api/chat/orchestrate` (SSE); Swagger at `/api/docs` |

### How it was verified

| Check | Result |
| --- | --- |
| `uv run pytest` | **43 / 43 pass**: auth (incl. token replay, `alg: none`), LLM gateway (rotation, 429 failover, key disable, circuit breaker, JSON retry), orchestrator (dependency ordering, parallel stage merge, agents reading each other's outputs, cross-turn and cross-conversation memory, failure isolation, LLM-backed path), API (SSE stream, conversation persistence, privacy), platform (config guards, Neon/Supabase URLs, CORS, headers, rate limit, log redaction) |
| `uv run mypy app tests` (strict) | clean, 93 files |
| `uv run ruff check` + `ruff format --check` | clean |
| `uv run lint-imports` | 5 / 5 architecture contracts kept |
| Live server | sign-up → profile → `POST /api/chat/orchestrate` streamed job_search → resume → validation with real hand-offs and saved 2 memories |

### Bugs found and fixed during verification

- **Parallel agents ran twice.** In LangGraph, a per-node router only sees its own node's write, so routing after each agent re-scheduled its parallel siblings. Fixed with a single `dispatch` join node. Covered by a test.
- **Stolen-token revocation was rolled back.** Raising the 401 rolled back the transaction that had just revoked the session family. The refresh route now returns the 401 instead, so the revocation commits. Covered by a test.
- **Logging crashed on Windows.** The `→` in the access log couldn't be encoded by the Windows console. Log messages are now ASCII, and the console stream degrades unknown characters instead of failing.

### Waiting on you

- [ ] Review `backend/README.md` (structure, layers, agents, memory, gateway, DB workflow)
- [ ] Add real Groq keys to `backend/.env` to see the agents use the LLM
- [ ] Decide when to commit (branch `nextjs-migration`, uncommitted)
- [ ] Next step options: connect the frontend to the API, or Phase 3 (durable Postgres checkpointer + pgvector memory)

---

## 2026-10-06 — Backend boilerplate (TypeScript, superseded by the entry above)

**Status:** replaced by the Python backend.

### What changed

| Area | Change |
| --- | --- |
| Repo layout | Split into `frontend/` (Next.js app, moved unchanged), `backend/` (new API) and `packages/contracts/` (shared contract), as npm workspaces |
| Contract | `src/lib/api.ts` moved to `packages/contracts/src/api.ts` (still the single endpoints file); added `auth.refresh`, `system.health`, and zod auth schemas in `schemas/auth.ts`. Frontend keeps `src/lib/api.ts` as a thin client that re-exports it |
| Backend structure | Fastify modular monolith: `platform/` (shared infrastructure) + `modules/` (auth, health). Each module is split into `routes` (HTTP) → `service` (business) → `repository` (data) |
| Layer enforcement | ESLint rules fail the build if a service imports Fastify or Drizzle, a route touches the database, platform imports a module, or one module reaches into another's internals |
| Authentication | Sign-up, sign-in, refresh, sign-out, session. Argon2id passwords, 15-min JWT access tokens, rotating refresh tokens in an httpOnly cookie with theft detection, per-IP rate limits |
| Database | Drizzle ORM + first migration (`users`, `refresh_tokens`). One `DATABASE_URL` switches between embedded PGlite (default, no setup), Docker Postgres, Neon and Supabase |
| Secrets | `backend/.env` (git-ignored) validated at startup by zod; `.env.example` templates for both apps. `GROQ_API_KEYS` parsed into the LLM round-robin pool for Phase 2 |
| Logging | Structured pino logs with a request id on every line and in the `x-request-id` header; passwords, tokens, cookies and API keys are redacted |
| Security headers | helmet (strict CSP), CORS allow-list with credentials, 1 MiB body limit |
| Tooling | Root scripts `dev` (both apps), `build`, `typecheck`, `lint`, `test`; `docker-compose.yml` with Postgres 16 + pgvector |

### How it was verified

| Check | Result |
| --- | --- |
| Backend tests (vitest, in-memory Postgres) | **23 / 23 pass**: sign-up, duplicate email, validation errors, bad JSON, sign-in, identical errors for wrong password vs unknown email, tampered and `alg: none` tokens rejected, refresh rotation, stolen-token replay revokes the session, sign-out, health, 404 envelope, CORS allow/deny, security headers, rate limiting, config validation, **no secrets in logs** |
| Typecheck (frontend, backend, contracts) | clean |
| Backend lint | clean; a deliberate layer violation was caught with the right message |
| Live server | `npm run dev` on port 4000: full sign-up → session → refresh → sign-out over real HTTP; dev log contains zero passwords or tokens |
| Production build | `npm run build` bundles to `backend/dist/` |
| Frontend | builds all 13 pages from `frontend/` using the shared contract |

### Known issues and notes

- **Frontend lint:** still reports 7 issues that were already in the code before this work (6 uses of `any`, 1 hook warning). Not touched.
- **Docker:** installed on this machine, but its daemon isn't running. That's why embedded PGlite is the default for local development.
- **Frontend still uses mocks:** it isn't wired to the backend yet and runs on `localStorage` data. Wiring sign-in to the real API is the next step.
- **Local `.env` created:** `backend/.env` was copied from the template and has only placeholder values. Set a real secret with `npm run secret -w backend`.
- **Data lost during the move:** none. A folder lock interrupted the move of `public/`; it was restored from git, and all files were confirmed identical to the originals.

### Waiting on you

- [ ] Review the folder structure and the auth design (`backend/README.md`)
- [ ] Decide when to commit. Everything is on branch `nextjs-migration`, uncommitted
- [ ] Next step options: wire the frontend sign-in to the API, or start Phase 2 (LLM gateway)

---

## 2026-10-05 — Next.js migration + architecture plan

- **Next.js migration:** moved the frontend from TanStack Start to Next.js 16 (App Router) with no visual change. All 11 pages verified in a real browser with no hydration errors.
- **Single endpoints file:** merged every endpoint into one file (`src/lib/api.ts`, now `packages/contracts/src/api.ts`).
- **Architecture plan:** wrote `docs/ARCHITECTURE.md`, approved with "the plan is just okay".
