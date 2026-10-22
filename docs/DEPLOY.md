# Deploying Career Compass — Vercel (frontend) + Render (backend)

```text
Browser ──► https://<app>.vercel.app            Next.js (Vercel)
               │  /api/*  is proxied (rewrite) ──► https://<api>.onrender.com/api/*   FastAPI (Render)
               ▼                                                    │
            same origin: the refresh cookie stays first-party       ▼
                                                              Neon Postgres
```

The browser only ever talks to the Vercel domain, and Vercel forwards `/api/*` to Render (`frontend/next.config.ts`). The two hosts are different sites (`vercel.app` and `onrender.com`). If the browser called Render directly, the login cookie (`SameSite=Lax`) would not be sent and users would be logged out after 15 minutes.

Do it in this order: **Render first** (to get its URL), then **Vercel**, then go back to Render and Google with the Vercel URL.

---

## 0. Before you start

- The code is on GitHub (`main`), including `render.yaml` and `frontend/next.config.ts`.
- **Neon:** rotate the database password (Neon console → Roles → `neondb_owner` → Reset password), because the old one was shared in chat. Then copy both connection strings from Connect:
  - **Pooled** (host contains `-pooler`): becomes `DATABASE_URL`.
  - **Direct** (the same host without `-pooler`): becomes `DATABASE_DIRECT_URL`.
- Have your **OpenRouter key** and **Google OAuth Client ID** ready.

## 1. Backend on Render

1. Go to https://dashboard.render.com → **New** → **Blueprint**, connect GitHub, and pick `Sriram-murugesan/career-compass` (branch `main`). Render reads `render.yaml`.
2. Render asks for the `sync: false` values:

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | Neon **pooled** URL, e.g. `postgresql://neondb_owner:<pw>@ep-…-pooler.c-4.ap-southeast-1.aws.neon.tech/neondb?sslmode=require` |
| `DATABASE_DIRECT_URL` | Neon **direct** URL (the same, without `-pooler`) |
| `CORS_ORIGINS` | For now `https://placeholder.vercel.app`. Set the real Vercel URL in step 3. |
| `GOOGLE_CLIENT_IDS` | `…apps.googleusercontent.com` (same as local) |
| `OPENROUTER_API_KEYS` | `sk-or-v1-…` (comma-separate several keys for round robin) |

   Set automatically by `render.yaml`: `PYTHON_VERSION=3.11.9`, `ENVIRONMENT=production`, `LOG_LEVEL=INFO`, `JWT_SECRET` (random, generated once), `DB_PGBOUNCER=true`, `DB_AUTO_MIGRATE=true`, `JOB_BOARDS=jobicy,remotive`, `JOBS_COUNTRY=in`, `GRAPH_MIN_USERS=3`.

3. Click **Apply**. The build runs `pip install uv && uv sync --frozen --no-dev`. On start, the app applies the Alembic migrations and then serves on `$PORT`.
4. When it shows **Live**, open `https://<your-service>.onrender.com/api/health`. You should see `"status":"ok"` and `"database":"up"`.

**Optional** (add under the service's **Environment** tab, then redeploy): `GROQ_API_KEYS`, `OPENROUTER_SITE_URL=https://<app>.vercel.app`, `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`.

**Without the Blueprint:** New → Web Service → the repo, then:
- Root Directory `backend`, Runtime Python 3, Region Singapore.
- Build Command: `pip install uv && uv sync --frozen --no-dev`
- Start Command: `.venv/bin/uvicorn app.main:create_app --factory --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"`
- Health Check Path `/api/health`.
- All the variables above, plus a `JWT_SECRET` generated with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

## 2. Frontend on Vercel

1. Go to https://vercel.com/new → import `Sriram-murugesan/career-compass`.
2. **Root Directory:** `frontend`. The framework is detected as Next.js; keep the default build and install commands.
3. **Environment Variables** (apply to Production and Preview):

| Variable | Value |
| --- | --- |
| `BACKEND_URL` | `https://<your-service>.onrender.com` (no trailing slash). Server-side only; used by the `/api` rewrite. |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | the same Google Client ID |
| `NEXT_PUBLIC_API_BASE_URL` | **do not set** (empty = same-origin `/api`, through the proxy) |

4. **Deploy.** Note the production URL, e.g. `https://career-compass.vercel.app`.

> Rewrites are fixed at build time. If you change `BACKEND_URL`, **redeploy** the frontend.

## 3. Point Render and Google at the Vercel URL

1. **Render** → service → Environment: set `CORS_ORIGINS=https://career-compass.vercel.app` (your exact URL, no trailing slash). Optionally also set `OPENROUTER_SITE_URL` to the same URL. Save, which redeploys.
2. **Google Cloud Console** → APIs & Services → Credentials → your OAuth 2.0 Web client → **Authorized JavaScript origins** → add `https://career-compass.vercel.app`. Keep `http://localhost:3000` for local development. It can take a few minutes to take effect.

## 4. Check it

- Open `https://<app>.vercel.app/api/health` (through the proxy). You should see `"status":"ok"`.
- Sign up with email/password, reload the page, and confirm you're still signed in (the refresh cookie works).
- Click "Continue with Google".
- Run the Job Search agent, create a mock test, and check in a habit.

## Things to know

- **Render free plan** sleeps after 15 minutes idle, and the first request then takes about 30–60 s to wake it. Upgrade to Starter for an always-on instance, or accept the cold start.
- **Migrations** run on startup (`DB_AUTO_MIGRATE=true`), which is fine for one instance. If you scale to several instances, set it to `false` and run `uv run alembic upgrade head` as a Render **Pre-Deploy Command** (paid plans).
- **Agent conversation state** (LangGraph checkpoints) lives in memory and resets on each deploy or restart. Messages, profiles, tests and habits are stored in Neon and are not affected.
- **Secrets** live only in the Render and Vercel dashboards. `backend/.env` and `frontend/.env.local` are git-ignored, so never commit them.
- **Local development is unchanged:** `npm run dev`, with `NEXT_PUBLIC_API_BASE_URL=http://localhost:4000` and no `BACKEND_URL`.
