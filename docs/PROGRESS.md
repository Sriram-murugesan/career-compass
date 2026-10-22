# Career Compass — Interim Progress Log

Newest entry first. Each entry says what changed, how it was verified, and what is waiting on you.

---

## 2026-10-22 (latest) — Productivity tracker linked to mock-test scores

**Status:** done; verified with tests. Neon is migrated to `fd68b422160b`. Not committed yet.

- **No agent run:** the Productivity page is now a tracker. It runs on plain rules and data, with no LLM.
- **Habits and check-ins:**
  - Habits with weekly targets and optional minutes, plus presets (Gym 3×/wk, Cardio, Learn a new topic, Apply to jobs, Mock interview practice, Sleep).
  - One tap checks in; you can edit the minutes, undo, archive or delete.
  - Streaks are counted in days or weeks, with a 7-day strip per habit, week completion %, and a 28-day heatmap.
- **Linked to mock tests:**
  - Weak topics (below 80%) from graded attempts are suggested; one tap tracks one as a learning habit.
  - Study logged since the last test drives the status: not started → studying → ready to retest → improved.
  - The "Scores vs learning" section has two aligned single-measure charts (no dual axis), hover tooltips and a table view.
- **New:**
  - Tables `habits` and `habit_logs`.
  - Routes under `/api/productivity/*`.
  - `InterviewHistory`, the interview module's public read API (per-topic results per attempt).
- **Fixed:** autogenerate rendered the boolean `archived` default as `0`, which Postgres rejects. It is now `sa.false()`. The migration had rolled back cleanly and was then re-applied.
- **Checks:**
  - **103 tests pass** (5 new: daily and weekly streaks; habits, check-ins and overview; dates and ownership; the full weak-topic → study → retake → improved chain with the score trend).
  - ruff, mypy and 7 import contracts pass; the frontend tsc, eslint and build pass.

## 2026-10-22 — Mock interview tests with instant scoring

**Status:** done; verified with tests and live generation (OpenRouter). Neon is migrated to `f136bfade304`. Not committed yet.

- **Relevance:**
  - Each test targets one role and one domain (defaults: your first target role and first interest).
  - It's tuned to your skills and levels, your experience, the graph's gap skills for that role, and your recent weak topics.
  - The live sample (Frontend Engineer, Fintech) produced React, TypeScript, Next.js and Tailwind questions, fintech scenarios (balances, transaction tables, card masking, currency rounding) and situational questions.
- **Speed:**
  - Generation runs as parallel batches of at most 4 questions (core, domain, judgement), with one top-up round for short batches.
  - 10 questions took 12–21 s, compared with 83 s as a single call (which was over the 30 s LLM timeout).
- **Quality guards:** 4 distinct options, a valid key, no "all/none of the above", exact and near-duplicate questions dropped across batches, and options shuffled (answer positions came out well spread).
- **Scoring:**
  - The answer key never leaves the server.
  - Grading is instant, deterministic and uses no LLM: score, a grade (Interview-ready / Strong / Developing / Needs practice), topic breakdown, weak topics, and the correct answer and explanation for each question.
  - Attempts and best scores are stored. The result is written to long-term memory in the same transaction as the attempt.
- **New:**
  - Tables `mock_tests` and `mock_test_attempts`.
  - Routes `/api/interview/mock-tests` (GET, POST), `/{id}` (GET) and `/{id}/attempts` (POST).
  - `SessionMemoryWriter`, which writes memories inside the caller's transaction (this also fixes a SQLite lock).
  - UI: the Interview Preparation page now opens with the Mock test (setup with role and domain chips, difficulty and question count; taking with a progress bar and timer; results with a score ring, topic bars and a full review; history with retakes). The practice questions follow below.
- **Checks:**
  - **98 tests pass** (8 new: validation and shuffling, grading, batch planning, a failed batch, near-duplicates, end-to-end API, privacy and input checks, no LLM keys).
  - ruff, mypy and 7 import contracts pass; the frontend tsc, eslint and build pass.

## 2026-10-19 — Shared career knowledge graph (Postgres on Neon)

**Status:** done; verified with tests and on Neon (migration applied; graph queries run in a rolled-back transaction). Not committed yet.

- **Decisions (yours):** a shared knowledge graph rather than shared profiles, stored as tables in the existing Neon database instead of a separate graph database.
- **New package `app/knowledge/`:**
  - Tables: `kg_nodes`, `kg_edges`, `kg_evidence`, `kg_user_links`.
  - Name normalization (skill aliases; seniority and suffixes stripped from roles).
  - A repository (upserts that work on both Postgres and SQLite; public-edge aggregation; neighbours, search, and career paths through a recursive CTE with cycle protection) and an orchestrator store.
- **Privacy:**
  - Profile-derived edges are public only when ≥ `GRAPH_MIN_USERS` (default 3) users back them; edges backed by a posting are always public.
  - User counts below the threshold are hidden.
  - Search and node lookups only reach nodes that have a public edge.
  - Your own links are returned only to you.
- **Writes:**
  - A profile edit syncs the graph in the same transaction.
  - Job Search postings are recorded after each run.
  - The Job Search agent now requires a "matched skill" to appear in the posting, so the graph only learns real requirements.
- **Reads:**
  - Agents get a "Shared career graph" context block.
  - New `/api/graph/me`, `/nodes/{kind}/{key}`, `/search` and `/paths` routes.
  - New `/graph` page: radial graph, search, career paths, skills paired with yours.
- **Checks:**
  - **90 tests pass** (7 new: normalization, the threshold, no cross-user leak, contribution withdrawn on edit, postings plus hidden small counts, recursive paths, agent context).
  - ruff, mypy and **7** import contracts pass; the frontend tsc, eslint and build pass.
- **Migration:** `d0315b58d43c` has been applied to Neon.

## 2026-10-12 — LLM re-ranking of live job postings

**Status:** done; verified with tests and a live run (real boards and OpenRouter). Not committed yet.

- **Pipeline:**
  - Retrieve a wide pool (20 per query per board).
  - Pre-rank it in code (role and skill relevance, freshness) and keep the top 25.
  - The large model scores a rubric (skills, level, location, goals), gives an eligibility verdict, and lists matched and missing skills, a reason and a next step.
  - Code computes the final score (weighted, plus recency, with a cap of 45 for region-locked postings and a floor of 35) and keeps the top 5.
- **Anti-hallucination:** matched skills must be on the profile; missing skills must be in the posting; postings are referenced by number only.
- **Output:** new fields `fit`, `eligibility`, `matchedSkills`, `missingSkills`, `nextStep`, plus `ranking` ("ai" / "keyword") and `considered`. A notice appears when few postings fit. A planned location of "Remote" is treated as no location.
- **UI:** each job card shows fit bars, "You have" and "Gaps" chips, an eligibility line and the next step; the header reads "Top N of M postings, re-ranked by AI".
- **Tests:** 83 pass. New tests cover the code-computed score and ordering, skill verification, the region cap with the weak-match floor, and pre-ranking (the model sees relevant postings first, capped at 25).
- **Live run** (sample Chennai frontend profile): 30 postings were considered and 3 returned. The India-eligible role ranked first (83); an Australia-only role was capped at 45 and flagged.

## 2026-10-12 — Free, keyless job boards (Jobicy + Remotive)

**Status:** done and verified, including a real search against both APIs. Not committed yet.

- **Why:** live postings shouldn't need a sign-up. Adzuna stays, but it's optional.
- **New:**
  - `app/jobs/jobicy.py`: keyword search, no key, 30-minute cache.
  - `app/jobs/remotive.py`: Remotive's public feed ignores `search` and asks for at most ~4 calls a day. So the whole feed is fetched once per 6 hours (one shared fetch, even for parallel searches) and filtered locally by title and tag keywords.
  - `app/jobs/multi.py`: searches every board in parallel, interleaves the results and de-duplicates them by title and company. One board failing is logged and skipped; all of them failing falls back to suggestions.
  - `app/jobs/factory.py`: builds boards from `JOB_BOARDS` (default `jobicy,remotive`) and adds Adzuna first when its keys are set.
  - `app/jobs/text.py`: a shared HTML cleaner (Adzuna uses it too).
- **Ranking prompt:** remote postings show the regions they hire from. The ranker is told to score postings outside the user's region low and to say why.
- **Tests:** test settings default to `job_boards=[]`, so no test touches the network. There are 5 new tests (Jobicy parsing and caching, Remotive single fetch and local filtering, multi-board merge and failure handling, factory, and an end-to-end orchestrate run with both boards). **81 pass**; ruff, mypy and the 5 import contracts are clean.
- **Live check:** "react developer" returned real Jobicy postings dated today and Remotive postings, with jobicy.com / remotive.com apply links.
- **Limit to know:** both free boards are **remote-only**, and many roles hire only from the US or EU. For local Indian jobs, add free Adzuna keys.

## 2026-10-12 — Job Search agent uses real postings (Adzuna)

**Status:** done and verified with simulated Adzuna responses. Waiting for your Adzuna keys to go live. Not committed yet.

- **New:** `app/jobs/adzuna.py`, the Adzuna client.
  - Strips HTML tags, formats salaries (₹ for India), and drops postings without a link.
  - Caches identical searches for 10 minutes; errors never include the key.
- **Agent pipeline:** plan the search, fetch real postings, have the LLM rank them **by number only**, and take company, location, salary, date and apply link from the posting.
  - Falls back to keyword ranking without an LLM.
  - Falls back to clearly labelled role suggestions without keys, or when Adzuna is down.
- **Agents stay HTTP-free:** the job board is injected into agents the same way as the LLM client.
- **Settings:** `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `JOBS_COUNTRY` (default `in`). `/api/health` shows `jobBoard`.
- **UI:** job cards show **Apply** (external link), posting date, salary and source, plus a notice when results are suggestions.
- **JSearch not built yet:** its response fields couldn't be confirmed from official docs. It can be added behind the same interface once verified.
- **Verified:**
  - 76/76 backend tests pass (9 new):
    - the Adzuna request and parsing;
    - the search cache;
    - no key leaks in errors or logs;
    - the model unable to invent postings or links;
    - keyword ranking without an LLM;
    - honest empty results;
    - suggestions labelled and stripped of links;
    - the full API path returning `applyUrl` and `postedAt`.
  - mypy, ruff and lint-imports are clean; frontend typecheck and lint are clean.

---

## 2026-10-12 — All mock data removed; every screen uses real data

**Status:** done and verified. Not committed yet.

### What was mock, and what replaced it

| Screen | Before (mock) | Now |
| --- | --- | --- |
| Profile data | "Ada Lovelace", fake skills, fake resume with a random ATS score | Account name/email + `GET/PATCH /api/profile`; empty for a new account |
| Chat | 2 canned conversations, a fake keyword "orchestration" with hard-coded jobs | Real conversations (`/api/chat/conversations`), real runs streamed live from `/api/chat/orchestrate` |
| Agent pages (7) | Hard-coded jobs, checks, milestones, questions, charts | "Run agent" calls the real agent; shows its real output; last result restored from the backend |
| Dashboard | Fake statuses ("9-day streak", "Resume ready · v4"), fixed "Good afternoon" | Agent descriptions, real greeting by time of day, real skill / target-role counts |
| Profile page | Fake 92%/95%/88% ATS breakdown, simulated "re-parse" | Real completeness; resume upload shown as "coming soon" with links to the real Resume/Validation agents |
| Setup wizard | Pre-ticked fake interests/goals | Starts from the user's own saved choices |
| Activity log / saved resumes | Fake history | Empty until the user acts; stored in this browser per user (no backend endpoints yet) |

### Backend additions
- **Profile fields:** `bio`, `target_salary` and `work_preference`, with a migration applied to Neon.
- **`DELETE /api/chat/conversations/{id}`:** owner only.
- **Running specific agents:** `POST /api/chat/orchestrate` accepts `agents: [...]` to run specific agents plus what they *require*. Validation requires a resume draft; the other agents use earlier outputs only when they're available, so running the Advisor no longer runs all seven.

### Bugs found and fixed during verification
- **Wrong page after sign-up:** a new account went to the dashboard instead of setup, because the login page's "already signed in" redirect raced the sign-up redirect.
- **Live run wiped from the chat:** the conversation list arriving from Neon (about 4 s) replaced a conversation whose run was already streaming, so the live steps disappeared. The list now merges with what's on screen.
- **Reloads on token refresh:** profile and chat reloaded on every token refresh (a new user object for the same account); they now reload only when the account changes.

### Verified
- **Backend:** 67/67 tests pass; mypy, ruff and lint-imports are clean.
- **Frontend:** typecheck clean, lint 0 problems (the old `any`/hook issues went away with the mock code), production build passes.
- **Browser (new account, against Neon + OpenRouter):** 19/19 checks pass: no mock markers on any screen, profile round-trip through the database, Interview agent run and result restored after reload, chat streaming a real Job Search run, conversations stored.
- **Neon:** test accounts deleted; only the real Google-sign-in account remains.

---

## 2026-10-12 (later) — Real login: Google sign-in + email/password, JWT sessions

**Status:** done and verified. Not committed yet.

### Backend
- **Google sign-in:** `POST /api/auth/google` verifies the Google ID token locally (RS256 signature against Google's cached public keys, audience, issuer, expiry, `email_verified`), then issues the existing JWT and rotating refresh cookie.
- **Account linking:** sign-ins match by Google `sub`, then by verified email. Linking to an unverified password account removes that password and revokes its sessions (pre-account takeover protection). An email already tied to another Google account returns 409.
- **Database:** `users` gains `google_sub` (unique), `avatar_url` and `email_verified`, and `password_hash` becomes optional.
  - The migration is tested upgrade → downgrade → upgrade, including a table that already has users.
  - It's applied to Neon.
- **New setting:** `GOOGLE_CLIENT_IDS`. When it's empty, Google sign-in is off and the endpoint returns 503.

### Frontend
- **`AuthContext`:**
  - The access token stays in memory only.
  - On page load, the session is restored from the httpOnly refresh cookie.
  - The token is refreshed automatically before it expires.
  - Refreshes are serialised per tab and across tabs, so rotation never raises a false theft alarm.
- **Login page:** wired to the real API, with "Continue with Google" (shown only once a Client ID is set), error messages and a loading state. The "skip to dashboard" link is removed.
- **Protected pages:** every signed-in page goes through `RequireAuth`. Signed-out visitors go to `/?next=…` and are sent back after login.
- **Sign out:** now revokes the session; the Google avatar is shown when available.

### Verified
- **Backend:** 64/64 tests pass (13 new for Google: 7 forged or invalid token cases rejected, account creation, linking, takeover protection, conflict, disabled mode). Strict mypy, ruff and lint-imports are clean.
- **Browser (headless Edge, against Neon):** 11/11 login-flow checks pass: redirect when signed out, sign-up, session surviving reload, protected navigation, sign-out, wrong-password message, sign-in. Exactly one refresh per page load, and no reuse alarms.
- **Frontend:** typecheck clean; no new lint issues.
- **Neon:** test accounts deleted afterwards; Neon is empty.

### Waiting on you
- [ ] Create a Google OAuth Client ID (steps in `backend/README.md → Google sign-in`) and put it in `backend/.env` and `frontend/.env.local`
- [ ] Reset the Neon password (it was shared in chat)
- [ ] Commit and push when you're happy

---

## 2026-10-12 — OpenRouter support + Neon database

**Status:** done and verified. Not committed yet.

- **OpenRouter in the LLM gateway:**
  - New settings `OPENROUTER_API_KEYS`, `OPENROUTER_BASE_URL` and `OPENROUTER_MODEL_LARGE/FAST`, plus optional `OPENROUTER_SITE_URL` and `OPENROUTER_APP_NAME` attribution headers.
  - Groq and OpenRouter keys share one round-robin pool, interleaved by provider, so an outage or rate limit on one provider fails over to the other.
  - Existing Groq settings are unchanged.
- **Log redaction:** now also scrubs OpenRouter keys (`sk-or-…`) and database passwords inside connection URLs.
- **Neon:** `backend/.env` (git-ignored) uses the Neon pooled URL with `DB_PGBOUNCER=true`, and `DATABASE_DIRECT_URL` (non-pooler host) for migrations. The initial migration has been applied to Neon.
- **Verified:**
  - Neon: connection and all 6 tables confirmed through the pooled connection.
  - Live API on Neon: sign-up → agent run → saved conversation all work. The smoke-test account was deleted afterwards.
  - Backend: 50/50 tests pass, and strict mypy, ruff and lint-imports are clean.
- **Action for you:** the Neon password was shared in chat. Reset it in the Neon console and update `backend/.env`.

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
