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
  id: string;
  name: string;
  short: string;
  status: string;
  phase: "foundation" | "growth";
  icon: LucideIcon;
  summary: string;
};

export const agents: Agent[] = [
  {
    id: "resume",
    name: "Resume Agent",
    short: "Resume",
    status: "Resume ready · v4",
    phase: "foundation",
    icon: FileText,
    summary: "Drafts and maintains an ATS-friendly resume from your profile.",
  },
  {
    id: "validation",
    name: "Validation Agent",
    short: "Validation",
    status: "2 items to review",
    phase: "foundation",
    icon: ShieldCheck,
    summary: "Audits structure, keywords and formatting before you apply.",
  },
  {
    id: "job-search",
    name: "Job Search Agent",
    short: "Job Search",
    status: "3 new matches",
    phase: "foundation",
    icon: Search,
    summary: "Surfaces roles aligned to your skills, interests and goals.",
  },
  {
    id: "productivity",
    name: "Productivity Tracker",
    short: "Tracker",
    status: "9-day streak",
    phase: "foundation",
    icon: Activity,
    summary: "Tracks applications, practice sessions and weekly momentum.",
  },
  {
    id: "roadmap",
    name: "Personalized Roadmap",
    short: "Roadmap",
    status: "Updated 2d ago",
    phase: "growth",
    icon: RouteIcon,
    summary: "Sequences the skills and milestones between here and the goal.",
  },
  {
    id: "advisor",
    name: "Career Advisor",
    short: "Advisor",
    status: "4 recommendations",
    phase: "growth",
    icon: Compass,
    summary: "Explains trade-offs and suggests the next deliberate move.",
  },
  {
    id: "interview",
    name: "Interview Preparation",
    short: "Interview",
    status: "12 of 30 questions",
    phase: "growth",
    icon: MessagesSquare,
    summary: "Runs mock interviews and grades your answers over time.",
  },
];

export const getAgent = (id: string) => agents.find((a) => a.id === id);
