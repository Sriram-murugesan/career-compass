import type { Metadata } from "next";
import { Entry } from "@/views/EntryView";

export const metadata: Metadata = {
  title: "Career Compass — AI multi-agent career platform",
  description:
    "Sign in to Career Compass: seven AI agents that build your resume, validate it, find jobs, and prepare you for interviews.",
  openGraph: {
    title: "Career Compass — AI multi-agent career platform",
    description: "Seven specialized AI agents guiding your career from resume to offer.",
  },
};

export default function Page() {
  return <Entry />;
}
