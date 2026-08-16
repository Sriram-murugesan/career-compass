import { createFileRoute, Link } from "@tanstack/react-router";
import { AppShell } from "@/components/AppShell";
import { OutlineIcon } from "@/components/OutlineIcon";
import { agents, type Agent } from "@/lib/agents";
import { useUserProfile } from "@/context/UserProfileContext";
import { Sparkles, ShieldCheck, ArrowRight } from "lucide-react";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Agent Dashboard — Career Compass" },
      {
        name: "description",
        content:
          "Seven AI agents in one pipeline: resume, validation, job search, tracking, roadmap, advice and interview prep.",
      },
      { property: "og:title", content: "Agent Dashboard — Career Compass" },
      {
        property: "og:description",
        content: "Follow the pipeline from resume to interview readiness.",
      },
    ],
  }),
  component: Dashboard,
});

function AgentCard({ agent, index }: { agent: Agent; index: number }) {
  return (
    <Link
      to="/agents/$agentId"
      params={{ agentId: agent.id }}
      className="rise-in group relative flex flex-col justify-between rounded-lg border border-border bg-background p-5 transition-colors duration-300 [transition-timing-function:cubic-bezier(0.65,0,0.35,1)] hover:border-ink"
      style={{ animationDelay: `${index * 45}ms` }}
    >
      <div className="flex items-start justify-between">
        <OutlineIcon icon={agent.icon} size={22} />
        <span className="text-[11px] tabular-nums text-muted-foreground">
          {String(index + 1).padStart(2, "0")}
        </span>
      </div>
      <div className="mt-8">
        <h3 className="text-sm font-medium">{agent.name}</h3>
        <p className="mt-1 text-xs text-muted-foreground">{agent.status}</p>
      </div>
    </Link>
  );
}

function Dashboard() {
  const { profile, completionPercentage } = useUserProfile();
  const foundation = agents.filter((a) => a.phase === "foundation");
  const growth = agents.filter((a) => a.phase === "growth");
  const firstName = profile.name ? profile.name.split(" ")[0] : "Ada";

  return (
    <AppShell>
      <header className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
        <div className="max-w-xl">
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground flex items-center gap-2">
            <Sparkles size={12} className="text-ink" /> AI Multi-Agent System
          </p>
          <h1
            className="mt-3 text-2xl font-medium tracking-tight"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Good afternoon, {firstName}
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Your pipeline runs left to right. Tailored for your profile as a{" "}
            <span className="font-medium text-foreground">{profile.title}</span>.
          </p>
        </div>

        <Link
          to="/profile"
          className="group inline-flex items-center gap-3 rounded-lg border border-border bg-background p-4 transition-colors duration-300 hover:border-ink"
        >
          <OutlineIcon icon={ShieldCheck} size={22} />
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-foreground">Profile Context</span>
              <span className="text-[11px] tabular-nums text-muted-foreground">
                {completionPercentage}% Sync
              </span>
            </div>
            <p className="text-[11px] text-muted-foreground">
              {profile.skills.length} skills · {profile.resume?.atsScore}% ATS score
            </p>
          </div>
          <ArrowRight size={14} className="text-muted-foreground transition-transform duration-300 group-hover:translate-x-0.5 group-hover:text-ink" />
        </Link>
      </header>

      <section className="mt-14">
        <div className="flex items-baseline justify-between">
          <h2 className="text-sm font-medium">Foundation</h2>
          <span className="text-xs text-muted-foreground">Resume · Validation · Search · Track</span>
        </div>
        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {foundation.map((a, i) => (
            <AgentCard key={a.id} agent={a} index={i} />
          ))}
        </div>
      </section>

      <div className="relative my-10 h-12">
        <svg className="h-full w-full" viewBox="0 0 100 48" preserveAspectRatio="none">
          <path
            d="M 88 0 L 88 20 L 12 28 L 12 48"
            fill="none"
            stroke="currentColor"
            strokeWidth="0.3"
            className="path-draw text-border-strong"
          />
        </svg>
      </div>

      <section>
        <div className="flex items-baseline justify-between">
          <h2 className="text-sm font-medium">Growth &amp; readiness</h2>
          <span className="text-xs text-muted-foreground">Roadmap · Advice · Interview</span>
        </div>
        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {growth.map((a, i) => (
            <AgentCard key={a.id} agent={a} index={i + 4} />
          ))}
        </div>
      </section>
    </AppShell>
  );
}
