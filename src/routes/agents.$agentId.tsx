import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { OutlineIcon } from "@/components/OutlineIcon";
import { getAgent } from "@/lib/agents";
import { AgentBody } from "@/components/agents/AgentBody";

export const Route = createFileRoute("/agents/$agentId")({
  loader: ({ params }) => {
    const agent = getAgent(params.agentId);
    if (!agent) throw notFound();
    return { name: agent.name, summary: agent.summary };
  },
  head: ({ loaderData }) => ({
    meta: [
      { title: `${loaderData?.name ?? "Agent"} — Career Compass` },
      { name: "description", content: loaderData?.summary ?? "Career Compass agent workspace." },
      { property: "og:title", content: `${loaderData?.name ?? "Agent"} — Career Compass` },
      {
        property: "og:description",
        content: loaderData?.summary ?? "Career Compass agent workspace.",
      },
    ],
  }),
  component: AgentPage,
});

function AgentPage() {
  const { agentId } = Route.useParams();
  const agent = getAgent(agentId);
  if (!agent) return null;

  return (
    <AppShell>
      <Link
        to="/dashboard"
        className="draw-icon inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors duration-300 hover:text-ink"
      >
        <ArrowLeft size={15} strokeWidth={1.5} />
        All agents
      </Link>

      <header className="mt-8 flex items-start gap-4 border-b border-border pb-8">
        <span className="group rounded-md border border-border p-2.5">
          <OutlineIcon icon={agent.icon} size={22} />
        </span>
        <div>
          <h1 className="text-xl font-medium tracking-tight">{agent.name}</h1>
          <p className="mt-1 max-w-lg text-sm leading-relaxed text-muted-foreground">
            {agent.summary}
          </p>
        </div>
        <span className="ml-auto text-xs text-muted-foreground">{agent.status}</span>
      </header>

      <div className="rise-in mt-10">
        <AgentBody id={agent.id} />
      </div>
    </AppShell>
  );
}
