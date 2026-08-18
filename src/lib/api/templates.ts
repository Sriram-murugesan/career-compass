/**
 * Career Compass — TEMPLATED RESPONSES
 * ------------------------------------
 * Exact JSON shapes the frontend expects from each endpoint.
 * These act as (a) contract documentation for the backend team and
 * (b) static fallbacks while the app runs without a backend.
 *
 * Every payload is wrapped by the standard envelope:
 *   { success: boolean, data: <below>, error: null | { code, message } }
 */

import type { ApiEnvelope } from "./config";

export const envelope = <T,>(data: T): ApiEnvelope<T> => ({
  success: true,
  data,
  error: null,
});

/* ------------------------------- AUTH -------------------------------- */
export const AUTH_SESSION_TEMPLATE = {
  token: "jwt.token.here",
  expiresAt: "2026-12-31T23:59:59.000Z",
  user: {
    id: "usr_00000000",
    name: "Ada Lovelace",
    email: "ada.lovelace@example.com",
    isOnboarded: true,
  },
};

/* ------------------------------ PROFILE ------------------------------ */
export const PROFILE_TEMPLATE = {
  id: "usr_00000000",
  name: "Ada Lovelace",
  email: "ada.lovelace@example.com",
  title: "Senior Full-Stack Engineer",
  bio: "Short professional summary.",
  location: "San Francisco, CA (Remote)",
  experienceLevel: "Senior (6+ years)",
  targetRoles: ["Senior Software Engineer"],
  targetSalary: "$160,000 - $195,000 / yr",
  workPreference: "Remote", // "Remote" | "Hybrid" | "Onsite"
  skills: [
    { name: "TypeScript", category: "Technical", level: "Expert" }, // category: Technical | Soft Skills | Tools
  ],
  interests: ["AI tooling"],
  goals: ["Senior engineer"],
  aiPreferences: {
    tone: "Ambitious", // "Professional" | "Concise" | "Ambitious"
    focusArea: "High-growth tech startups",
    autoRunAgents: true,
  },
  completionPercentage: 92,
};

/* ------------------------------ RESUME ------------------------------- */
export const RESUME_TEMPLATE = {
  fileName: "Ada_Lovelace_CV_2026.pdf",
  fileUrl: "https://cdn.example.com/resumes/usr_00000000.pdf",
  uploadedAt: "2026-08-12T10:04:00.000Z",
  atsScore: 92,
  parsedSkillsCount: 14,
  summary: "Parsed summary of the resume.",
};

export const TAILORED_RESUME_TEMPLATE = {
  id: "tres_0001",
  jobTitle: "Senior Frontend Engineer",
  company: "Kepler Systems",
  location: "London · Hybrid",
  createdAt: "2026-08-16T09:00:00.000Z",
  atsScore: 96,
  matchedKeywords: ["TypeScript", "System Design"],
  summary: "Tailored professional summary.",
  bullets: ["Impact bullet with a metric."],
};

/* -------------------------------- JOBS -------------------------------- */
export const JOB_TEMPLATE = {
  id: "job_0001",
  role: "Senior Frontend Engineer",
  co: "Kepler Systems",
  loc: "London · Hybrid",
  type: "Full-time",
  match: 96, // 0-100 match score computed server-side
  salary: "£95k - £115k",
  keywords: ["TypeScript", "Micro-frontends"],
  desc: "Role description.",
  saved: false,
  postedAt: "2026-08-14T08:00:00.000Z",
  applyUrl: "https://example.com/apply/job_0001",
};

/* ------------------------------- AGENTS ------------------------------- */
export const VALIDATION_TEMPLATE = [
  { label: "Contact block parsable", state: "pass", note: "Email and phone detected" }, // state: pass | warn | fail
];

export const ROADMAP_TEMPLATE = [
  { title: "Sharpen system design", when: "Weeks 1–3", note: "Two design reviews per week." },
];

export const INTERVIEW_TEMPLATE = {
  questions: ["Walk me through a system you designed end to end."],
  sessionId: "int_0001",
};

export const PRODUCTIVITY_TEMPLATE = {
  applicationsPerWeek: [2, 4, 3, 6, 5, 7, 8],
  streakDays: 12,
  responseRate: 0.34,
};

export const ADVISOR_TEMPLATE = {
  answer: "Advisor guidance text.",
  citations: [] as string[],
};

/* -------------------------------- CHAT -------------------------------- */
export const CONVERSATION_TEMPLATE = {
  id: "conv_0001",
  title: "Senior Role Exploration",
  lastUpdated: "2026-08-17T18:20:00.000Z",
  messages: [
    {
      id: "msg_0001",
      sender: "assistant", // "user" | "assistant"
      text: "Message body (markdown allowed).",
      timestamp: "2026-08-17T18:20:00.000Z",
      isOrchestration: true,
      orchestration: {
        isComplete: true,
        activeStepIndex: 1,
        steps: [
          {
            agentId: "job-search",
            agentName: "Job Search Agent",
            status: "completed", // idle | running | completed
            details: "Queried matching roles",
          },
        ],
        resultType: "jobs", // jobs | validation | roadmap | advice | interview | text
        resultData: [] as unknown[], // shape depends on resultType (see templates above)
      },
    },
  ],
};

/* ------------------------------ ACTIVITY ------------------------------ */
export const ACTIVITY_TEMPLATE = {
  id: "act_0001",
  type: "resume_generated", // resume_generated | job_searched | profile_updated | interview_practiced
  title: "Generated Tailored Resume for Kepler Systems",
  timestamp: "2026-08-17T18:20:00.000Z",
  details: "Tailored for Senior Frontend Engineer with 96% ATS match.",
  targetCompany: "Kepler Systems",
  atsScore: 96,
};

/* ------------------------------- ERRORS ------------------------------- */
export const ERROR_TEMPLATE = {
  success: false,
  data: null,
  error: { code: "VALIDATION_ERROR", message: "Human readable message." },
};
