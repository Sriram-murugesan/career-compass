# Career Compass — Backend (FastAPI)

The backend is one FastAPI process, built as a **modular monolith** with boundaries that a linter enforces. It uses SQLAlchemy 2 (async) with Alembic migrations, and it's ready for **Neon** or **Supabase**. Seven **LangGraph** agents share one state and a three-tier memory, and they reach the LLMs through a **round-robin gateway** over your Groq and/or OpenRouter keys.

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
│   ├── knowledge/              # shared career knowledge graph (all users)
│   │   ├── models.py           # kg_nodes, kg_edges, kg_evidence, kg_user_links
│   │   ├── normalize.py        # "ReactJS" = "react.js" = react; seniority/suffixes off roles
│   │   ├── repository.py       # sync_user, record_postings, neighbours, search, paths (CTE)
│   │   └── store.py            # for the orchestrator: insights_text(), record_postings()
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
6. **Graph module layers.** `modules/graph` is router → dependencies → service; its data layer is the shared `app/knowledge` package.
7. **The knowledge graph stays generic.** `app/knowledge` never imports modules, agents, the orchestrator or the LLM gateway.

Cross-module use goes through a module's `__init__.py`. For example, routes are protected with `from app.modules.auth import CurrentUserId`, and chat reads the profile through `ProfileService`.

## Authentication

| Endpoint | Auth | Result |
| --- | --- | --- |
| `POST /api/auth/sign-up` | none | 201 session + refresh cookie |
| `POST /api/auth/sign-in` | none | session + refresh cookie |
| `POST /api/auth/google` | Google ID token in the body | session + refresh cookie (account created on first use) |
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
- **Rate limits:** sign-up, sign-in, Google sign-in and refresh are limited per IP; the default is 10 per minute.

### Google sign-in

**How it works.**
1. The login page shows Google's own button.
2. When the user picks an account, Google gives the browser a signed **ID token**, which the frontend posts to `POST /api/auth/google`.
3. `app/modules/auth/google.py` verifies the token locally:
   - **Signature:** RS256, checked against Google's public keys, which are fetched and cached.
   - **Audience:** must be one of `GOOGLE_CLIENT_IDS`, so a token issued for another app is rejected.
   - **Issuer:** must be Google.
   - **Expiry:** must not be expired.
   - **Email:** `email_verified` must be true.
4. The backend then issues the same JWT and refresh cookie as password login.

No client secret is involved.

**Which account a Google sign-in uses:**

| Situation | Result |
| --- | --- |
| Google account seen before (same Google `sub`) | Signs in to that account |
| An account already has this email, not yet linked | Google is linked to it. If its email was never verified, its password is **removed** and its sessions are revoked. Anyone could have registered that address, so the verified Google owner takes over (pre-account takeover protection). |
| The email is linked to a *different* Google account | 409 `ACCOUNT_CONFLICT`; the accounts are never merged |
| New email | A verified, password-less account is created |

Google-only accounts can't use password sign-in. They get the same `Invalid email or password` answer as any other failed attempt, so the response doesn't reveal how an account signs in.

**Setup (one time, about 5 minutes):**
1. Go to [Google Cloud Console](https://console.cloud.google.com) → **APIs & Services** → **OAuth consent screen**. Choose **External**, enter the app name and support email, and add yourself as a test user.
2. Go to **Credentials** → **Create credentials** → **OAuth client ID** → **Web application**.
3. Under **Authorized JavaScript origins**, add `http://localhost:3000`, plus your production URL later. No redirect URI is needed.
4. Copy the **Client ID** (`….apps.googleusercontent.com`) into **both**:
   - `backend/.env`: `GOOGLE_CLIENT_IDS=<client id>`
   - `frontend/.env.local`: `NEXT_PUBLIC_GOOGLE_CLIENT_ID=<client id>`
5. Restart `npm run dev`. The **Continue with Google** button appears on the login page.

The Client ID isn't secret: Google publishes it in every login page that uses it. Without it, Google sign-in returns `503 GOOGLE_SIGN_IN_DISABLED` and the button stays hidden.

### Frontend session handling

`frontend/src/context/AuthContext.tsx` manages the session in the browser:
- **Access token:** kept only in memory, never in `localStorage`.
- **On page load:** it restores the session by calling `/api/auth/refresh` with the httpOnly cookie.
- **Before expiry:** it refreshes about one minute before the access token expires.
- **No false theft alarms:** refreshes run one at a time, both within a tab and across tabs (Web Locks), so a parallel refresh can't trigger reuse detection and sign the user out.

Every signed-in page is wrapped in `RequireAuth` through `AppShell`. Signed-out visitors go to `/?next=<page>`, and are sent back to that page after signing in.

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

## Productivity tracker (no agent run)

The code is in `app/modules/productivity/`. It is plain rules, with no LLM involved: check-ins save the moment you tap them.

- **Habits:** gym, cardio, learning, career or anything else, with a weekly target (7 = daily) and optional minutes per session.
- **Check-ins:** one per habit per day, with optional minutes and a note. You can backfill up to 60 days back; future days aren't allowed.
- **Local dates:** days are your *local* dates. The browser sends `today`, and the server only checks it is within a day of UTC.
- **Streaks:** daily habits count days in a row (an unfinished today doesn't break the streak); weekly targets count weeks that met the target.
- **Overview:**
  - today's progress and this week's completion %;
  - the last 7 days per habit;
  - a 28-day heatmap.
- **Linked to mock tests** (read through `app.modules.interview.InterviewHistory`):
  - Topics you scored below 80% on become learning suggestions. "Track" creates a "Learn {topic}" habit tied to that topic.
  - Each tracked topic counts the sessions and minutes logged **after** it was last tested (timestamps, so studying and retesting on the same day work). The status moves through not started → studying → **ready to retest** (3 sessions or 90 min) → **improved** once a retake beats the previous score.
  - The score trend lists each attempt's score next to the learning minutes logged between it and the previous attempt.

## Mock interview tests (Interview Preparation)

The test is multiple choice, written for **one role and one domain**, and scored the moment you submit. The code is in `app/agents/interview/mock_test.py` (generation and grading logic) and `app/modules/interview/` (tables and API).

1. **What the test is built from:**
   - the role you pick (default: your first target role) and the domain (default: your first interest);
   - your skills with their levels, your experience level and your goals;
   - the shared career graph's skills for that role, especially your gaps;
   - the topics you got wrong in recent mock tests.
2. **Written in parallel batches** of up to 4 questions each, using the large model:
   - about 50% core knowledge, with your skills spread across the batches;
   - about 30% scenarios in the chosen domain;
   - about 20% problem-solving and situational judgement.

   A 10-question test takes about as long as one batch (typically 12–20 s). A batch that comes back short gets one top-up round.
3. **Validated in code:**
   - exactly 4 distinct options, a valid answer and no "all/none of the above";
   - exact and near-duplicate questions (by word overlap) are dropped across batches;
   - options are shuffled, because models tend to put the right answer first.
4. **The answer key stays on the server.** Only questions and options are sent to the browser.
5. **Instant scoring with no LLM:**
   - `POST …/attempts` grades the answers against the stored key and returns the score, a grade, a per-topic breakdown (weakest first), and the correct answer and explanation for every question.
   - The result is saved as a long-term memory **in the same transaction**, so the Roadmap and Advisor agents know your weak spots, and your next test revisits them.

Tests are private: another user's test returns 404. Each user can create up to 20 tests per 24 hours, as an LLM cost guard, and can retake any test as often as they like.

## Shared career knowledge graph

One graph for all users, stored in Postgres (Neon; SQLite in tests): `app/knowledge/`.

| Table | Holds | Who sees it |
| --- | --- | --- |
| `kg_nodes` | skills, roles, companies — one row per normalised key ("ReactJS" = "react.js" = `react`; "Senior Frontend Engineer - UK" = `frontend engineer`) | everyone (only nodes with a public edge are findable) |
| `kg_edges` | `role_skill` (role → skill), `skill_pair` (skill ↔ skill), `leads_to` (role → role), `hires_for` (company → role) | everyone, **if public** |
| `kg_evidence` | who backs each edge: a user, or a job posting (sha256 of its URL) | nobody directly; only counts |
| `kg_user_links` | your `has_skill`, `targets_role`, `current_role` | **only you** |

**Where the edges come from:**
- **Your profile.** Saving skills, target roles or headline rebuilds your links and evidence in the same transaction as the profile edit. It adds role → skill for each target role × skill, skill ↔ skill pairs (up to 15 skills), and current role (from your headline) → each target role.
- **Live job postings.** After a run, the Job Search agent's matches add company → role and role → skill. Skills are recorded only when the posting actually names them.
- **Existing profiles** join automatically the first time you open `/graph` or run the agents.

**The privacy rule:**
- An edge built from profiles is public only when **`GRAPH_MIN_USERS`** (default 3) different users back it. An edge backed by a real posting is always public.
- A user count below the threshold is shown as 0, even on an edge that a posting made public.
- Support is counted live from `kg_evidence`. Editing your profile withdraws your old contribution, and deleting your account cascades.
- Unknown and private nodes both return 404, so the API never reveals whether a private-only node exists.

**What the graph is used for:**
- **Agents:** `load_memory` adds a "Shared career graph" block to every agent's context: the skills most associated with your target roles (marked "has it" or "GAP"), companies hiring and next roles.
- **API:** `/api/graph/*` (see `app/endpoints.py`).
- **UI:** the `/graph` page shows a radial graph, a search box, and career paths computed with a recursive CTE.

## Live job search (Job Search agent)

Live search works **out of the box, with no keys**. The Job Search agent works with **real postings**:

1. **Plan:** the LLM turns your request and profile into 1–2 job-title queries and a location, such as "react developer" in "Chennai". Without an LLM, it uses your target roles and location.
2. **Fetch:** every board in `JOB_BOARDS` is searched in parallel by `app/jobs/multi.py`. Results are interleaved and de-duplicated. If one board is down, the others still answer.

   | Board | Key | Covers | How it's called |
   | --- | --- | --- | --- |
   | `jobicy` (`app/jobs/jobicy.py`) | none | Remote jobs, worldwide | Keyword search; cached 30 min |
   | `remotive` (`app/jobs/remotive.py`) | none | Remote jobs (small feed, 24 h delay) | Whole feed fetched once per 6 h, filtered locally. Remotive asks for at most ~4 calls a day |
   | `adzuna` (`app/jobs/adzuna.py`) | free tier, optional | **Local** jobs by city/country | Added automatically when `ADZUNA_APP_ID`/`ADZUNA_APP_KEY` are set; cached 10 min; key never logged |

3. **Pre-rank (code):** every posting is scored on title match with the target roles, profile skills it mentions, and freshness. The best 25 go to the model, so it reads the strongest pool rather than whatever arrived first.
4. **Re-rank (LLM, large model):** the model sees the 25 as a numbered list and may only refer to them **by number**. For up to 8 it scores a rubric of 0–100 for **skills**, **experience level**, **location** and **goals**. It also gives an eligibility verdict (`eligible` / `check` / `unlikely`), matched skills, missing skills, a one-sentence reason and a concrete **next step**.
   - **The final score is computed in code, not by the model:** 40% skills, 25% level, 20% location, 15% goals, plus a recency adjustment (+3 if 3 days old or less, −3 or −8 if stale). Postings the user can't apply to from their region are capped at 45. Matches scoring below 35 are dropped, and the top 5 are kept.
   - **Verified, not trusted:** "matched skills" must be on the profile, and "missing skills" must appear in the posting text. Numbers that don't exist, and repeats, are ignored.
   - **Without an LLM:** the pre-rank order is used, explained by the skills each posting mentions.
5. **Return:** the company, location, salary, posting date and **apply link** come from the posting itself, so the model can't invent an employer or a link. Every card says which board it came from ("via jobicy"); both free boards require this credit and a link back to their page, and the apply link is that page.

| Setting | Meaning |
| --- | --- |
| `JOB_BOARDS` | Free boards to search, comma-separated: `jobicy,remotive` (default). Empty = none |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | Optional free keys from https://developer.adzuna.com for local (non-remote) jobs |
| `JOBS_COUNTRY` | Adzuna country code: `in` (India, default), `gb`, `us`, `ca`, `au`, … |

**When there are no live postings:**
- **No boards configured, or every board unreachable:** the agent returns role-type **suggestions**, labelled `mode: "suggested"` with a notice. Any links the model writes are removed.
- **No matches:** the result is an honest empty list with a hint to broaden the search.
- **Check your setup:** `/api/health` shows `jobBoard`, for example `"jobicy+remotive"` or `"adzuna+jobicy+remotive"`.

## LLM gateway

- **Providers:** Groq, OpenRouter, or both. Any OpenAI-compatible provider fits, because the gateway only sends standard `/chat/completions` requests.

  ```env
  GROQ_API_KEYS=gsk_a,gsk_b                 # models: LLM_MODEL_LARGE / LLM_MODEL_FAST
  OPENROUTER_API_KEYS=sk-or-v1-a            # models: OPENROUTER_MODEL_LARGE / _FAST (ids from openrouter.ai/models)
  ```

- **Tiers:** every key serves both tiers. `large` (default `openai/gpt-oss-120b`) is for drafting; `fast` (default `openai/gpt-oss-20b`) is for checks and planning.
- **Rotation:** calls go round robin across **every key of every provider**. Providers are interleaved (`groq-1`, `openrouter-1`, `groq-2`, …), so if one provider goes down or hits a rate limit, the next call goes to the other.
- **OpenRouter extras:** requests carry `X-Title` (`OPENROUTER_APP_NAME`) and, if set, `HTTP-Referer` (`OPENROUTER_SITE_URL`) for attribution in your OpenRouter dashboard. All OpenRouter keys on one account share that account's credit.
- **Failover rules** (they apply to every provider the same way):

| Event | Action |
| --- | --- |
| 429 | Cool that key for `Retry-After` (else 2 s doubling, max 60 s); retry on the next key at once |
| 5xx / timeout | Next key; 3 failures in a row open the circuit for 30 s |
| 401 / 403 | Disable that key until restart; log a warning (key id only) |
| Other 4xx | No retry — the request itself is wrong |
| All keys exhausted | `LlmUnavailable` → the agent returns its offline fallback; the run still completes |

**Secrets:** keys are `SecretStr` values. They never appear in `/api/health`, in `repr()` or in any log line. The log redaction filter also scrubs Groq (`gsk_…`) and OpenRouter (`sk-or-…`) keys, database passwords in connection URLs, JWTs, bearer tokens and the refresh cookie.

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
