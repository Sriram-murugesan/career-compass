import type { Metadata } from "next";
import { Setup } from "@/views/SetupView";

export const metadata: Metadata = {
  title: "Profile Setup — Career Compass",
  description: "Tell Career Compass your skills, interests and goals so the agents can begin.",
  openGraph: {
    title: "Profile Setup — Career Compass",
    description: "A short three-step flow: skills, interests, goals.",
  },
};

export default function Page() {
  return <Setup />;
}
