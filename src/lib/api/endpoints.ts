/**
 * Career Compass — single source of truth for every backend endpoint
 * the frontend expects. Paths only; no requests are made from here.
 * Human-readable contract: docs/API_ENDPOINTS.txt
 */

export const ENDPOINTS = {
  auth: {
    signIn: "/api/auth/sign-in", // POST
    signUp: "/api/auth/sign-up", // POST
    signOut: "/api/auth/sign-out", // POST
    session: "/api/auth/session", // GET
  },

  profile: {
    get: "/api/profile", // GET
    update: "/api/profile", // PATCH
    completion: "/api/profile/completion", // GET
    skills: "/api/profile/skills", // GET | PUT
    skill: (name: string) => `/api/profile/skills/${encodeURIComponent(name)}`, // DELETE
    interests: "/api/profile/interests", // PUT
    goals: "/api/profile/goals", // PUT
    preferences: "/api/profile/ai-preferences", // PUT
  },

  onboarding: {
    complete: "/api/onboarding/complete", // POST
  },

  resume: {
    upload: "/api/resume/upload", // POST (multipart/form-data)
    current: "/api/resume", // GET
    parse: "/api/resume/parse", // POST
    tailoredList: "/api/resume/tailored", // GET
    tailoredCreate: "/api/resume/tailored", // POST
    tailoredDelete: (id: string) => `/api/resume/tailored/${id}`, // DELETE
    export: (id: string) => `/api/resume/tailored/${id}/export`, // GET (pdf/docx)
  },

  jobs: {
    search: "/api/jobs/search", // GET  ?q=&location=&type=&remote=
    detail: (id: string) => `/api/jobs/${id}`, // GET
    save: (id: string) => `/api/jobs/${id}/save`, // POST
    unsave: (id: string) => `/api/jobs/${id}/save`, // DELETE
    saved: "/api/jobs/saved", // GET
  },

  agents: {
    list: "/api/agents", // GET
    detail: (agentId: string) => `/api/agents/${agentId}`, // GET
    run: (agentId: string) => `/api/agents/${agentId}/run`, // POST
    validation: "/api/agents/validation/run", // POST
    roadmap: "/api/agents/roadmap", // GET
    advisor: "/api/agents/advisor/ask", // POST
    interviewQuestions: "/api/agents/interview/questions", // GET
    interviewSubmit: "/api/agents/interview/answer", // POST
    productivity: "/api/agents/productivity/metrics", // GET
  },

  chat: {
    conversations: "/api/chat/conversations", // GET | POST
    conversation: (id: string) => `/api/chat/conversations/${id}`, // GET | DELETE
    messages: (id: string) => `/api/chat/conversations/${id}/messages`, // GET | POST
    orchestrate: "/api/chat/orchestrate", // POST (SSE stream of agent steps)
  },

  activity: {
    list: "/api/activity", // GET
    create: "/api/activity", // POST
  },
} as const;
