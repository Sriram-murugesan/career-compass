/**
 * Career Compass — FRONTEND endpoints (single source of truth)
 * =============================================================
 * Every URL the frontend knows about, in one file:
 *
 *   1. PAGE_ROUTES    the app's own pages (Next.js routes in src/app/)
 *   2. API_ENDPOINTS  every backend endpoint the frontend calls
 *
 * Backend counterpart: backend/app/endpoints.py — the routes the API
 * actually serves. Status markers below:
 *   [live]     implemented in the backend today
 *   [planned]  in the roadmap; shape documented in ./api-templates.ts
 *
 * All API paths are relative to NEXT_PUBLIC_API_BASE_URL (see ./api.ts).
 * Every response is wrapped in the envelope:
 *   { success, data, error: null | { code, message, details? }, meta: { requestId } }
 */

/* ======================================================================== */
/* 1. PAGE ROUTES                                                           */
/* ======================================================================== */

export const PAGE_ROUTES = {
  home: "/", // sign in / sign up
  setup: "/setup", // onboarding wizard
  dashboard: "/dashboard", // agent pipeline + orchestrator chat
  profile: "/profile", // profile hub
  graph: "/graph", // shared career knowledge graph
  agent: (agentId: string) => `/agents/${agentId}`, // one agent's workspace
} as const;

/* ======================================================================== */
/* 2. API ENDPOINTS                                                         */
/*    Format:  [status] METHOD  auth  body / query  ->  response data        */
/*    auth:    public | bearer (Authorization: Bearer <token>) | cookie      */
/* ======================================================================== */

export const API_ENDPOINTS = {
  system: {
    health: "/api/health", // [live] GET public -> { status, database, uptimeSeconds, llmEntries }
  },

  // Access token comes back in the body (keep it in memory, send as Bearer).
  // The refresh token is an httpOnly cookie on /api/auth — send with credentials: "include".
  auth: {
    signUp: "/api/auth/sign-up", // [live] POST public { name, email, password } -> AuthSession + cookie
    signIn: "/api/auth/sign-in", // [live] POST public { email, password } -> AuthSession + cookie
    google: "/api/auth/google", // [live] POST public { credential: Google ID token } -> AuthSession + cookie
    refresh: "/api/auth/refresh", // [live] POST cookie -> AuthSession + rotated cookie
    signOut: "/api/auth/sign-out", // [live] POST cookie -> { signedOut: true }
    session: "/api/auth/session", // [live] GET bearer -> { user }
  },

  profile: {
    // Profile: headline, bio, location, targetSalary, workPreference, experienceLevel,
    //          targetRoles, skills, interests, goals, aiPreferences
    get: "/api/profile", // [live] GET bearer -> Profile
    update: "/api/profile", // [live] PATCH bearer Partial<Profile> -> Profile
    completion: "/api/profile/completion", // [planned] GET bearer -> { completionPercentage }
  },

  onboarding: {
    complete: "/api/onboarding/complete", // [planned] POST bearer { skills, interests, goals } -> Profile
  },

  agents: {
    list: "/api/agents", // [live] GET bearer -> [{ id, name, description, reads }]
  },

  chat: {
    conversations: "/api/chat/conversations", // [live] GET bearer -> Conversation[] | POST { title } -> Conversation
    conversation: (id: string) => `/api/chat/conversations/${id}`, // [live] GET bearer -> Conversation + messages | DELETE
    // [live] POST bearer { message, conversationId?, agents?: ["interview"] } -> text/event-stream:
    //   (agents = run exactly these backend agents plus what they require; omit to let the planner pick)
    //   conversation | plan | step (running/completed/failed) | answer | memory | done | error
    orchestrate: "/api/chat/orchestrate",
  },

  // Mock interview tests: generated for one role + domain; the answer key stays on the
  // server and grading an attempt returns the score instantly (no LLM).
  interview: {
    mockTests: "/api/interview/mock-tests", // [live] GET bearer -> MockTestSummary[] | POST { role?, domain?, difficulty, count } -> MockTest
    mockTest: (id: string) => `/api/interview/mock-tests/${id}`, // [live] GET bearer -> MockTest (no answers) + attempts
    attempts: (id: string) => `/api/interview/mock-tests/${id}/attempts`, // [live] POST bearer { answers, timeTakenSeconds } -> AttemptResult
  },

  // Productivity tracker: habits + daily check-ins, no agent run. `today` is the user's
  // LOCAL date (YYYY-MM-DD) so check-ins land on the right day in every time zone.
  productivity: {
    overview: "/api/productivity/overview", // [live] GET bearer ?today= -> { habits, doneToday, weekCompletion, heatmap, learning, scoreTrend }
    habits: "/api/productivity/habits", // [live] POST bearer { name?, category, targetPerWeek, targetMinutes?, linkedTopic? } -> Habit
    habit: (id: string) => `/api/productivity/habits/${id}`, // [live] PATCH { name?, targetPerWeek?, archived? } | DELETE
    log: (id: string, day: string) => `/api/productivity/habits/${id}/logs/${day}`, // [live] PUT ?today= { minutes?, note? } | DELETE
  },

  // Shared knowledge graph: anonymous aggregates from all users (an edge from profiles is
  // shown only when >= minUsers people back it) + real job postings. `me` adds YOUR links.
  graph: {
    me: "/api/graph/me", // [live] GET bearer -> { links, roles, adjacentSkills, minUsers }
    node: (kind: string, key: string) =>
      `/api/graph/nodes/${encodeURIComponent(kind)}/${encodeURIComponent(key)}`, // [live] GET bearer -> { node, groups }
    search: "/api/graph/search", // [live] GET bearer ?q=&kind=skill|role|company -> Node[]
    paths: "/api/graph/paths", // [live] GET bearer ?role= -> { role, paths: Node[][] }
  },

  resume: {
    upload: "/api/resume/upload", // [planned] POST bearer multipart { file } -> RESUME_TEMPLATE
    current: "/api/resume", // [planned] GET bearer -> RESUME_TEMPLATE
    tailoredList: "/api/resume/tailored", // [planned] GET bearer -> TAILORED_RESUME_TEMPLATE[]
    tailoredCreate: "/api/resume/tailored", // [planned] POST bearer { jobTitle, company, location }
    tailoredDelete: (id: string) => `/api/resume/tailored/${id}`, // [planned] DELETE bearer
    export: (id: string) => `/api/resume/tailored/${id}/export`, // [planned] GET bearer ?format=pdf|docx
  },

  jobs: {
    search: "/api/jobs/search", // [planned] GET bearer ?q=&location=&type=&remote= -> JOB_TEMPLATE[]
    detail: (id: string) => `/api/jobs/${id}`, // [planned] GET bearer -> JOB_TEMPLATE
    save: (id: string) => `/api/jobs/${id}/save`, // [planned] POST bearer | DELETE to unsave
    saved: "/api/jobs/saved", // [planned] GET bearer -> JOB_TEMPLATE[]
  },

  activity: {
    list: "/api/activity", // [planned] GET bearer -> ACTIVITY_TEMPLATE[]
    create: "/api/activity", // [planned] POST bearer { type, title, details } -> ACTIVITY_TEMPLATE
  },
} as const;

/**
 * Agent ids differ between the two sides today: the frontend uses kebab-case
 * ("job-search"), the backend snake_case ("job_search"). Map at the boundary.
 */
export const BACKEND_AGENT_ID: Record<string, string> = {
  resume: "resume",
  validation: "validation",
  "job-search": "job_search",
  productivity: "productivity",
  roadmap: "roadmap",
  advisor: "advisor",
  interview: "interview",
};
