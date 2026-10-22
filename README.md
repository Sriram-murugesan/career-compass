# Career Compass

Career Compass is an AI career platform. Seven specialist agents work as one pipeline: they find matching roles, tailor your resume, validate it for applicant-tracking systems, plan your roadmap, track your weekly progress, advise you, and run mock interviews.

The repo has two separate apps:

| | Folder | Stack | Runs on |
| --- | --- | --- | --- |
| **Frontend** | [`frontend/`](frontend/) | Next.js 16, React 19, TypeScript, Tailwind CSS 4 | http://localhost:3000 |
| **Backend** | [`backend/`](backend/) | Python 3.11, FastAPI, SQLAlchemy 2 + Alembic, LangGraph | http://localhost:4000 |

> **Status:** the backend boilerplate is complete: auth, profile, chat, and all 7 agents with shared memory. The frontend is wired to the API: sign-in (email/password or Google), profile, chat and live job postings. There is no mock data. See [docs/PROGRESS.md](docs/PROGRESS.md).

---

## 1. Repository structure

```text
career-compass/
├── frontend/                    # every frontend file
│   ├── src/app/                 # pages (Next.js routes): metadata + one view each
│   ├── src/views/               # page components
│   ├── src/components/          # AppShell, agent UIs, shadcn primitives (ui/)
│   ├── src/context/             # auth, profile + chat state (loaded from the API)
│   ├── src/lib/endpoints.ts     # ★ ALL FRONTEND ENDPOINTS: page routes + every backend API call
│   ├── src/lib/api.ts           # fetch client + envelope types
│   ├── src/lib/api-templates.ts # response shapes (incl. planned endpoints)
│   ├── src/lib/schemas/         # form validation (mirrors backend rules)
│   └── .env.example
│
├── backend/                     # every backend file
│   ├── app/endpoints.py         # ★ ALL BACKEND ENDPOINTS: every route the API serves
│   ├── app/main.py              # composition root: wires every module
│   ├── app/core/                # config (.env), security, errors, logging, middleware
│   ├── app/db/                  # SQLAlchemy engine + sessions (Neon / Supabase ready)
│   ├── app/modules/             # auth/ profile/ chat/ graph/ interview/ productivity/ health/ — router → service → repository → models
│   ├── app/agents/              # one folder per agent (7) + registry.py
│   ├── app/orchestrator/        # LangGraph state, reducers, planner, graph, SSE runner
│   ├── app/memory/              # shared long-term memory + context builder
│   ├── app/knowledge/           # shared career knowledge graph (skills, roles, companies)
│   ├── app/llm/                 # round-robin LLM gateway over your API keys
│   ├── alembic/                 # database migrations
│   ├── tests/                   # 103 tests
│   └── .env.example
│
├── docs/
│   ├── ARCHITECTURE.md          # design + implementation plan
│   └── PROGRESS.md              # interim progress log
├── docker-compose.yml           # optional local Postgres + pgvector
└── package.json                 # root scripts (run both apps together)
```

Deeper docs: [backend/README.md](backend/README.md) covers layers, auth, agents, memory, the LLM gateway and the database workflow. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) covers the overall design.

---

## 2. Endpoints

Each side has **one file** that lists every endpoint it owns.

| File | Lists | Kept honest by |
| --- | --- | --- |
| [`frontend/src/lib/endpoints.ts`](frontend/src/lib/endpoints.ts) | `PAGE_ROUTES` (the app's pages) and `API_ENDPOINTS` (every backend call, marked `[live]` or `[planned]`) | the TypeScript compiler |
| [`backend/app/endpoints.py`](backend/app/endpoints.py) | Every route the API serves, with method, auth and purpose. Routers import their paths from here | a test that fails if the file and the running app ever differ |

### Frontend pages

| Route | Page |
| --- | --- |
| `/` | Sign in / sign up |
| `/setup` | Onboarding wizard |
| `/dashboard` | Agent pipeline + orchestrator chat |
| `/profile` | Profile hub |
| `/graph` | Shared career graph explorer |
| `/agents/[agentId]` | One agent's workspace (7 agents) |

### Backend API (live)

All paths start with `/api`. Interactive docs: **http://localhost:4000/api/docs**.

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/health` | public | Liveness, database, LLM key pool health |
| POST | `/auth/sign-up` | public | Create account → access token + refresh cookie |
| POST | `/auth/sign-in` | public | Sign in → access token + refresh cookie |
| POST | `/auth/google` | public | Sign in / sign up with a Google ID token → access token + refresh cookie |
| POST | `/auth/refresh` | refresh cookie | New access token; rotates the cookie |
| POST | `/auth/sign-out` | refresh cookie | End this session |
| GET | `/auth/session` | bearer | The signed-in user |
| GET / PATCH | `/profile` | bearer | Read / update the career profile |
| GET | `/agents` | bearer | Agent catalogue |
| GET / POST | `/chat/conversations` | bearer | List / start conversations |
| GET / DELETE | `/chat/conversations/{id}` | bearer | One conversation with messages / delete it |
| POST | `/chat/orchestrate` | bearer | Run the agents; **streams** progress (Server-Sent Events). Optional `agents: [...]` runs specific agents (an agent's own page uses this) |
| GET / POST | `/interview/mock-tests` | bearer | Your mock tests / generate one for a role + domain (answer key stays on the server) |
| GET | `/interview/mock-tests/{id}` | bearer | One test (questions, no answers) + your attempts |
| POST | `/interview/mock-tests/{id}/attempts` | bearer | Submit answers → **instant** score, topic breakdown, correct answers + explanations |
| GET | `/productivity/overview?today=` | bearer | Habits with streaks and week progress, 28-day heatmap, mock-test-linked learning, score trend |
| POST / PATCH / DELETE | `/productivity/habits[/{id}]` | bearer | Track a habit (or a mock-test topic) / edit or archive / delete |
| PUT / DELETE | `/productivity/habits/{id}/logs/{day}` | bearer | Check in for a day (optional minutes) / undo |
| GET | `/graph/me` | bearer | Your own links (private) + shared insights around your roles and skills |
| GET | `/graph/nodes/{kind}/{key}` | bearer | A shared skill / role / company and its neighbours |
| GET | `/graph/search?q=&kind=` | bearer | Find shared nodes by name |
| GET | `/graph/paths?role=` | bearer | Career paths from a role (recursive SQL over `leads_to`) |

Planned endpoints (resume upload, jobs, activity, onboarding) are listed in `frontend/src/lib/endpoints.ts`, with their response shapes in `api-templates.ts`.

Every response uses one envelope:

```json
{ "success": true, "data": { }, "error": null, "meta": { "requestId": "…" } }
```

---

## 3. One-time setup

**Prerequisites:**
- [Node.js](https://nodejs.org) 22+
- [uv](https://docs.astral.sh/uv/) (installs and manages Python 3.11 for you)

```bash
git clone https://github.com/KavimugilRajasekar/career-compass-ui.git
cd career-compass-ui

# Frontend dependencies (from the repo root)
npm install

# Backend dependencies (creates backend/.venv)
cd backend && uv sync && cd ..

# Environment files — both are git-ignored; never commit them
cp frontend/.env.example frontend/.env.local
cp backend/.env.example backend/.env
```

Then edit `backend/.env`:

| Setting | What to do |
| --- | --- |
| `JWT_SECRET` | Generate one: `cd backend && uv run python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `GROQ_API_KEYS` / `OPENROUTER_API_KEYS` | Optional. Comma-separated keys for Groq (`gsk_…`), OpenRouter (`sk-or-…`) or both; the gateway rotates across all of them. Without keys, the agents use offline fallbacks |
| `DATABASE_URL` | Leave the SQLite default for local work. For Neon or Supabase, see section 6 |
| `JOB_BOARDS` | Free, keyless job APIs for the Job Search agent's **live postings** (with apply links): `jobicy,remotive` by default. They cover remote jobs |
| `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` | Optional free-tier keys from developer.adzuna.com. They add **local** jobs by city. `JOBS_COUNTRY` defaults to `in` (India) |
| `GOOGLE_CLIENT_IDS` | Optional. Enables "Continue with Google". Put the same Client ID in `frontend/.env.local` as `NEXT_PUBLIC_GOOGLE_CLIENT_ID`. Steps: [backend/README.md → Google sign-in](backend/README.md#google-sign-in) |

---

## 4. Daily workflow

```bash
npm run dev          # frontend :3000 + backend :4000 together
npm run dev:web      # frontend only
npm run dev:api      # backend only (auto-reload)
```

**Before you commit, run the checks:**

| Check | Command |
| --- | --- |
| Frontend types | `npm run typecheck` |
| Frontend lint | `npm run lint` |
| Backend tests | `npm test` (or `cd backend && uv run pytest`) |
| Backend lint + format | `cd backend && uv run ruff check . && uv run ruff format --check .` |
| Backend types | `cd backend && uv run mypy app tests` |
| Backend architecture rules | `cd backend && uv run lint-imports` |
| Frontend production build | `npm run build` |

### How a request flows

```text
Browser (frontend :3000)
  │  fetch(API_ENDPOINTS.chat.orchestrate)  + Authorization: Bearer <token>
  ▼
backend :4000  app/modules/chat/router.py         HTTP layer
  ▼
               app/modules/chat/service.py        save message, load profile + history
  ▼
               app/orchestrator (LangGraph)       supervisor plans → agents run in stages
  │              each agent: app/agents/<name>/   reads shared state, calls LLM gateway
  │              memory: app/memory/              recall + save long-term facts
  │              knowledge: app/knowledge/        shared graph insights in; live postings out
  ▼
  SSE stream back to the browser: plan → step (running/completed) → answer → memory → done
```

---

## 5. How to add things

### A new page (frontend)
1. Add `frontend/src/app/<route>/page.tsx` (metadata) and a view in `frontend/src/views/`.
2. Add the route to `PAGE_ROUTES` in `frontend/src/lib/endpoints.ts`.

### A new backend endpoint
1. Add the path constant and an `Endpoint(...)` row to `backend/app/endpoints.py`.
2. Implement it in the module's layers: `router.py` (HTTP) → `service.py` (rules) → `repository.py` (SQL).
3. Protect it by adding `user_id: CurrentUserId` to the route's parameters.
4. Add or update the entry in `frontend/src/lib/endpoints.ts` and mark it `[live]`.
5. Run `uv run pytest`. The endpoints test fails if steps 1 and 2 disagree.

### A new backend module
1. Create `backend/app/modules/<name>/` with `router.py`, `dependencies.py`, `service.py`, `repository.py`, `models.py`, `schemas.py` and `__init__.py`.
2. Register the router in `app/main.py` and the models in `app/model_registry.py`.
3. Create the migration: `cd backend && uv run alembic revision --autogenerate -m "add <name>"`. Review the generated file, then commit it.
4. Add the module to the layers rule in `pyproject.toml` (`[tool.importlinter]`).

### A new agent
1. Copy any folder in `backend/app/agents/`.
2. Edit its `schema.py`, `prompt.py` and `agent.py`. Keep a `_fallback` that works without an LLM.
3. Add its `SPEC` to `app/agents/registry.py`. The planner, the graph and `/api/agents` pick it up automatically.

---

## 6. Database workflow

| Stage | `DATABASE_URL` in `backend/.env` |
| --- | --- |
| Local (default) | `sqlite+aiosqlite:///./.data/dev.db`, created and migrated on start |
| Local Postgres | `docker compose up -d db`, then `postgresql://career:career@localhost:5432/career_compass` |
| Neon | Paste the **pooled** URL; set `DB_PGBOUNCER=true` and `DATABASE_DIRECT_URL` = the non-pooler URL |
| Supabase | Paste the **pooler** URL (port 6543); set `DB_PGBOUNCER=true` and `DATABASE_DIRECT_URL` = the port 5432 URL |

To change the schema:
1. Edit `models.py`.
2. Run `uv run alembic revision --autogenerate -m "…"`.
3. Commit the migration.
4. In production, run `uv run alembic upgrade head` before starting the new version, with `DB_AUTO_MIGRATE=false`.

---

## 7. Git workflow

| Branch | Purpose |
| --- | --- |
| `main` | Connected to Lovable; still the original single-app frontend |
| `backend-boiler-template` | This layout: Next.js frontend + FastAPI backend boilerplate |

- Branch from `backend-boiler-template` for new work, run the checks in section 4, then open a pull request.
- **Never commit** `.env` files. They're git-ignored, and only the `*.example` templates are tracked.
- **Lovable:** `main` is synced with [Lovable](https://lovable.dev). Lovable can't edit this Next.js + FastAPI layout, so merging into `main` ends Lovable editing for this project. Don't force-push or rewrite pushed history on `main`.
