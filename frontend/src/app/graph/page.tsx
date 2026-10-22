import type { Metadata } from "next";
import { GraphPage } from "@/views/GraphView";

export const metadata: Metadata = {
  title: "Career Graph — Career Compass",
  description:
    "Explore the shared career graph: skills associated with roles, companies hiring, and where people move next.",
  openGraph: { title: "Career Graph — Career Compass" },
};

export default function Page() {
  return <GraphPage />;
}
