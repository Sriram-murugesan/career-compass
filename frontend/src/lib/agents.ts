import {
  FileText,
  ShieldCheck,
  Search,
  Activity,
  Route as RouteIcon,
  Compass,
  MessagesSquare,
  type LucideIcon,
} from "lucide-react";

export type Agent = {
  /** Frontend route id: /agents/<id> */
  id: string;
  /** The backend agent id (backend/app/agents/registry.py) */
  backendId: string;
  name: string;
  short: string;
  phase: "foundation" | "growth";
  icon: LucideIcon;
  summary: string;
  /** What the "Run" button asks for when the user types nothing. */
  defaultRequest: string;
};

export const agents: Agent[] = [
  {
    id: "resume",
    backendId: "resume",
    name: "Resume Agent",
    short: "Resume",
    phase: "foundation",
    icon: FileText,
    summary: "Drafts an ATS-friendly resume from your profile, tailored to a target role.",
    defaultRequest: "Draft a resume tailored to my target role.",
  },
  {
    id: "validation",
    backendId: "validation",
    name: "Validation Agent",
    short: "Validation",
    phase: "foundation",
    icon: ShieldCheck,
    summary: "Audits a resume draft for structure, keywords and impact before you apply.",
    defaultRequest: "Draft my resume and check it for ATS readiness.",
  },
  {
    id: "job-search",
    backendId: "job_search",
    name: "Job Search Agent",
    short: "Job Search",
    phase: "foundation",
    icon: Search,
    summary:
      "Searches live job postings and ranks them against your skills, goals and preferences.",
    defaultRequest: "Find open roles that fit my profile.",
  },
  {
    id: "productivity",
    backendId: "productivity",
    name: "Productivity Tracker",
    short: "Tracker",
    phase: "foundation",
    icon: Activity,
    summary:
      "Track daily habits (gym, cardio, learning) with streaks, linked to your mock-test scores.",
    defaultRequest: "Plan my focus and actions for this week.",
  },
  {
    id: "roadmap",
    backendId: "roadmap",
    name: "Personalized Roadmap",
    short: "Roadmap",
    phase: "growth",
    icon: RouteIcon,
    summary: "Sequences the skills and milestones between where you are and your goal.",
    defaultRequest: "Build a milestone roadmap to my goal.",
  },
  {
    id: "advisor",
    backendId: "advisor",
    name: "Career Advisor",
    short: "Advisor",
    phase: "growth",
    icon: Compass,
    summary: "Answers career questions and suggests the next deliberate move.",
    defaultRequest: "What should my next career move be?",
  },
  {
    id: "interview",
    backendId: "interview",
    name: "Interview Preparation",
    short: "Interview",
    phase: "growth",
    icon: MessagesSquare,
    summary:
      "Mock tests for your target role and domain, scored instantly, plus practice questions.",
    defaultRequest: "Give me practice interview questions for my target role.",
  },
];

export const getAgent = (id: string) => agents.find((a) => a.id === id);

/** Look up by the backend's id ("job_search") — used when rendering agent runs. */
export const getAgentByBackendId = (backendId: string) =>
  agents.find((a) => a.backendId === backendId);
