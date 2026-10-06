import type { Metadata } from "next";
import { Dashboard } from "@/views/DashboardView";

export const metadata: Metadata = {
  title: "Agent Dashboard — Career Compass",
  description:
    "Seven AI agents in one pipeline: resume, validation, job search, tracking, roadmap, advice and interview prep.",
  openGraph: {
    title: "Agent Dashboard — Career Compass",
    description: "Follow the pipeline from resume to interview readiness.",
  },
};

export default function Page() {
  return <Dashboard />;
}
