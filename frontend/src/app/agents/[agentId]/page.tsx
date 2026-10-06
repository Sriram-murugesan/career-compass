import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { agents, getAgent } from "@/lib/agents";
import { AgentPage } from "@/views/AgentView";

type Params = Promise<{ agentId: string }>;

export function generateStaticParams() {
  return agents.map((agent) => ({ agentId: agent.id }));
}

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const agent = getAgent((await params).agentId);
  const title = `${agent?.name ?? "Agent"} — Career Compass`;
  const description = agent?.summary ?? "Career Compass agent workspace.";
  return { title, description, openGraph: { title, description } };
}

export default async function Page({ params }: { params: Params }) {
  const { agentId } = await params;
  if (!getAgent(agentId)) notFound();
  return <AgentPage agentId={agentId} />;
}
