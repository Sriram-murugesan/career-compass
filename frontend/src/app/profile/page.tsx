import type { Metadata } from "next";
import { ProfilePage } from "@/views/ProfileView";

export const metadata: Metadata = {
  title: "User Profile — Career Compass",
  description:
    "Manage your professional profile, verified skills, career goals, resume ATS analysis, and AI agent context.",
  openGraph: { title: "User Profile — Career Compass" },
};

export default function Page() {
  return <ProfilePage />;
}
