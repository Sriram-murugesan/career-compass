"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { OutlineIcon } from "@/components/OutlineIcon";
import { getAgent } from "@/lib/agents";
import { AgentBody } from "@/components/agents/AgentBody";

export function AgentPage({ agentId }: { agentId: string }) {
  const agent = getAgent(agentId);
  if (!agent) return null;

  return (
    <AppShell>
      <Link
        href="/dashboard"
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
          <h1
            className="text-xl font-medium tracking-tight"
            style={{ fontFamily: "var(--font-display)" }}
          >
            {agent.name}
          </h1>
          <p className="mt-1 max-w-lg text-sm leading-relaxed text-muted-foreground">
            {agent.summary}
          </p>
        </div>
      </header>

      <div className="rise-in mt-10">
        <AgentBody id={agent.id} />
      </div>
    </AppShell>
  );
}
