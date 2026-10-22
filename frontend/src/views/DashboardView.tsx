"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { OutlineIcon } from "@/components/OutlineIcon";
import { AgentOutput } from "@/components/agents/AgentOutput";
import { agents, getAgentByBackendId, type Agent } from "@/lib/agents";
import { useUserProfile } from "@/context/UserProfileContext";
import { useChat } from "@/context/ChatContext";
import {
  Sparkles,
  ShieldCheck,
  ArrowRight,
  Plus,
  Trash2,
  ArrowUp,
  MessageCircle,
  Play,
  Loader2,
  CheckCircle2,
  CircleDashed,
  Building2,
  MapPin,
  Clock3,
  Bookmark,
  Calendar,
  Layers,
  Search,
  Activity,
  Route as RouteIcon,
  Compass,
  MessagesSquare,
  Bot,
} from "lucide-react";
import { useState, useRef, useEffect, useMemo } from "react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

function AgentCard({ agent, index }: { agent: Agent; index: number }) {
  return (
    <Link
      href={`/agents/${agent.id}`}
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
        <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{agent.summary}</p>
      </div>
    </Link>
  );
}

export function Dashboard() {
  const { profile, completionPercentage, logActivity } = useUserProfile();
  const {
    isChatActive,
    setChatActive,
    conversations,
    activeConversationId,
    setActiveConversationId,
    sendMessage,
    startNewConversation,
    deleteConversation,
    isOrchestrating,
  } = useChat();

  const [chatDraft, setChatDraft] = useState("");
  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const router = useRouter();

  const foundation = agents.filter((a) => a.phase === "foundation");
  const growth = agents.filter((a) => a.phase === "growth");
  const firstName = profile.name ? profile.name.split(" ")[0] : "there";
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  // Auto scroll chat to bottom when messages or orchestration changes
  const activeConversation = conversations.find((c) => c.id === activeConversationId);
  const messages = useMemo(() => activeConversation?.messages ?? [], [activeConversation]);

  useEffect(() => {
    if (isChatActive) {
      chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isChatActive, isOrchestrating]);

  const handleSend = () => {
    const text = chatDraft.trim();
    if (!text) return;
    sendMessage(text);
    setChatDraft("");
    setTimeout(() => {
      inputRef.current?.focus();
    }, 100);
  };

  const handleSuggestionClick = (text: string) => {
    sendMessage(text);
  };

  const handleTailorResume = (job: { role: string; company: string; location: string }) => {
    logActivity({
      type: "job_searched",
      title: `Picked ${job.role} at ${job.company}`,
      details: "Opening the Resume Agent to tailor a draft.",
      targetCompany: job.company,
    });
    const search = new URLSearchParams({
      jobRole: job.role,
      company: job.company,
      loc: job.location,
    });
    router.push(`/agents/resume?${search}`);
  };

  // Determine which agent is currently executing based on active orchestration step
  const activeRun = messages.find((m) => m.run && !m.run.isComplete)?.run;
  const runningBackendIds = new Set(
    activeRun?.steps.filter((s) => s.status === "running").map((s) => s.agentId) ?? [],
  );

  return (
    <AppShell>
      {/* ── MODE 1: Standard Multi-Agent Dashboard ── */}
      <div
        className={cn(
          "transition-all duration-500 ease-in-out",
          isChatActive
            ? "opacity-0 pointer-events-none absolute -translate-y-4 scale-95"
            : "opacity-100",
        )}
      >
        {!isChatActive && (
          <>
            <header className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
              <div className="max-w-xl">
                <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground flex items-center gap-2">
                  <Sparkles size={12} className="text-ink" /> AI Multi-Agent System
                </p>
                <h1
                  className="mt-3 text-2xl font-medium tracking-tight animate-in fade-in slide-in-from-top-3 duration-500"
                  style={{ fontFamily: "var(--font-display)" }}
                >
                  {greeting}, {firstName}
                </h1>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground animate-in fade-in duration-700">
                  Your pipeline runs left to right.{" "}
                  {profile.title ? (
                    <>
                      Tailored for your profile as{" "}
                      <span className="font-medium text-foreground">{profile.title}</span>.
                    </>
                  ) : (
                    <>
                      <Link href="/profile" className="text-ink underline underline-offset-4">
                        Add your headline and skills
                      </Link>{" "}
                      so the agents can tailor their work to you.
                    </>
                  )}
                </p>
              </div>

              <Link
                href="/profile"
                className="group inline-flex items-center gap-3 rounded-lg border border-border bg-background p-4 transition-colors duration-300 hover:border-ink animate-in fade-in slide-in-from-right-4 duration-500"
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
                    {profile.skills.length} skills · {profile.targetRoles.length} target roles
                  </p>
                </div>
                <ArrowRight
                  size={14}
                  className="text-muted-foreground transition-transform duration-300 group-hover:translate-x-0.5 group-hover:text-ink"
                />
              </Link>
            </header>

            <section className="mt-14">
              <div className="flex items-baseline justify-between">
                <h2 className="text-sm font-medium">Foundation</h2>
                <span className="text-xs text-muted-foreground">
                  Resume · Validation · Search · Track
                </span>
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
          </>
        )}
      </div>

      {/* ── MODE 2: Claude-like Chat Assistant Interface ── */}
      <div
        className={cn(
          "transition-all duration-500 ease-in-out h-full min-h-0",
          !isChatActive
            ? "opacity-0 pointer-events-none absolute translate-y-4 scale-95"
            : "opacity-100",
        )}
      >
        {isChatActive && (
          <div className="-mx-6 -my-12 flex h-[calc(100vh-3.5rem)] min-h-0 overflow-hidden lg:-mx-10 xl:-mx-14">
            {/* Left sidebar: Chat History */}
            <aside className="hidden min-h-0 w-60 shrink-0 flex-col border-r border-border md:flex">
              <div className="p-3 shrink-0">
                <button
                  onClick={() => startNewConversation()}
                  className="flex w-full items-center justify-center gap-2 rounded-md border border-dashed border-border-strong py-2 text-xs font-medium text-muted-foreground transition-all duration-300 hover:border-ink hover:text-ink hover:bg-accent/5"
                >
                  <Plus size={14} />
                  New Chat
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-2 space-y-1 scrollbar-none min-h-0">
                {conversations.length === 0 ? (
                  <p className="text-xs text-muted-foreground text-center py-6 italic">
                    No history yet.
                  </p>
                ) : (
                  conversations.map((c) => (
                    <div
                      key={c.id}
                      className={cn(
                        "group flex items-center justify-between rounded-md px-3 py-2 text-xs transition-colors duration-200 cursor-pointer",
                        activeConversationId === c.id
                          ? "bg-secondary text-foreground font-medium border border-border"
                          : "text-muted-foreground hover:bg-accent/5 hover:text-foreground",
                      )}
                      onClick={() => setActiveConversationId(c.id)}
                    >
                      <span className="truncate pr-2 max-w-[85%]">{c.title}</span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteConversation(c.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 p-0.5 text-muted-foreground hover:text-destructive transition-all duration-200"
                        title="Delete chat"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </aside>

            {/* Right column: Chat Area */}
            <div className="flex min-w-0 flex-1 flex-col min-h-0 overflow-hidden">
              {/* Active Chat Header */}
              <header className="flex shrink-0 items-center justify-between gap-4 border-b border-border px-5 py-2.5">
                <div className="min-w-0">
                  <h2 className="truncate text-xs font-semibold text-foreground">
                    {activeConversation?.title || "New Chat"}
                  </h2>
                  <p className="mt-0.5 text-[10px] text-muted-foreground">
                    {isOrchestrating ? "Routing query..." : "All agents ready"}
                  </p>
                </div>

                <div className="ml-auto hidden items-center gap-2 lg:flex">
                  {agents.map((a) => {
                    const isRunning = runningBackendIds.has(a.backendId);
                    return (
                      <Link
                        key={a.id}
                        href={`/agents/${a.id}`}
                        title={a.name}
                        className={cn(
                          "relative flex h-7 w-7 items-center justify-center rounded-full border transition-all duration-300 hover:border-ink",
                          isRunning
                            ? "agent-circle-pulse border-ink text-ink"
                            : "border-border text-muted-foreground",
                        )}
                      >
                        <OutlineIcon icon={a.icon} size={13} />
                      </Link>
                    );
                  })}
                </div>

                <button
                  onClick={() => setChatActive(false)}
                  className="text-[11px] font-medium text-muted-foreground hover:text-ink border border-border hover:border-ink rounded-md px-2.5 py-1 transition-all duration-300"
                >
                  View Grid Dashboard
                </button>
              </header>

              {/* Messages feed */}
              <div className="min-h-0 flex-1 overflow-y-auto modern-scrollbar">
                <div className="mx-auto w-full max-w-3xl space-y-8 px-6 py-8">
                  {messages.length === 0 ? (
                    /* Initial Claude-like state */
                    <div className="h-full flex flex-col justify-center items-center max-w-lg mx-auto text-center space-y-6 py-8">
                      <div className="rounded-full border border-border p-4 bg-background shadow-2xs">
                        <MessageCircle size={28} className="text-ink" />
                      </div>
                      <div>
                        <h3
                          className="text-base font-semibold text-foreground tracking-tight"
                          style={{ fontFamily: "var(--font-display)" }}
                        >
                          How can Career Compass help you today?
                        </h3>
                        <p className="text-xs text-muted-foreground mt-2 max-w-sm leading-relaxed">
                          Ask me to scan for jobs, validate your resume compatibility, structure a
                          milestones roadmap, or run practice interview loops.
                        </p>
                      </div>

                      {/* Suggestions list */}
                      <div className="w-full grid gap-2 sm:grid-cols-2 pt-2">
                        {[
                          "Find roles that fit my profile",
                          "Draft my resume and check it for ATS readiness",
                          "Build a milestone roadmap to my goal",
                          "Give me practice interview questions",
                        ].map((sug) => (
                          <button
                            key={sug}
                            onClick={() => handleSuggestionClick(sug)}
                            className="text-[11px] text-left p-3 rounded-md border border-border bg-card hover:border-ink hover:bg-accent/5 text-muted-foreground hover:text-foreground transition-all duration-300 leading-normal hover:shadow-2xs"
                          >
                            {sug}
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : (
                    /* Message bubbles */
                    messages.map((m) => {
                      const isUser = m.sender === "user";
                      return (
                        <div
                          key={m.id}
                          className={cn(
                            "flex flex-col",
                            isUser
                              ? "items-end animate-in fade-in slide-in-from-right-3 duration-300"
                              : "items-start animate-in fade-in duration-300",
                          )}
                        >
                          {/* Sender badge */}
                          <span className="text-[10px] text-muted-foreground mb-1 tabular-nums px-1">
                            {isUser ? "You" : "Compass Assistant"} ·{" "}
                            {new Date(m.timestamp).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>

                          <div
                            className={cn(
                              "text-xs leading-relaxed space-y-4",
                              isUser
                                ? "max-w-[85%] rounded-lg border border-border bg-secondary px-4 py-3 text-foreground"
                                : "w-full text-foreground",
                            )}
                          >
                            {m.text ? (
                              <p className="whitespace-pre-line leading-relaxed font-medium">
                                {m.text}
                              </p>
                            ) : null}

                            {/* Real agent run: plan, live progress, then each agent's output */}
                            {!isUser && m.run && (
                              <div className="border border-border rounded-lg bg-background/40 p-4 space-y-4 mt-3">
                                <div className="flex items-center justify-between border-b border-border pb-2.5">
                                  <div className="flex items-center gap-2">
                                    <Loader2
                                      size={13}
                                      className={cn(
                                        "text-ink",
                                        !m.run.isComplete && "animate-spin",
                                      )}
                                    />
                                    <span className="text-[11px] font-semibold tracking-wide text-foreground">
                                      Agent orchestrator
                                    </span>
                                  </div>
                                  <span className="text-[10px] uppercase font-bold tracking-widest text-muted-foreground">
                                    {m.run.error
                                      ? "Failed"
                                      : m.run.isComplete
                                        ? "Done"
                                        : m.run.steps.length
                                          ? "Running"
                                          : "Planning"}
                                  </span>
                                </div>

                                {m.run.steps.length > 0 && (
                                  <div className="relative pl-4 space-y-3">
                                    <div className="absolute left-[9px] top-2 bottom-2 w-[1px] bg-border-strong border-dashed border-l" />
                                    {m.run.steps.map((step) => {
                                      const isDone = step.status === "completed";
                                      const isRunning = step.status === "running";
                                      return (
                                        <div
                                          key={step.agentId}
                                          className={cn(
                                            "relative flex items-start gap-3 text-[11px] transition-all duration-300",
                                            isRunning ? "text-ink" : "text-muted-foreground",
                                          )}
                                        >
                                          <span className="absolute -left-[12px] top-1 flex h-2 w-2 rounded-full border bg-background items-center justify-center">
                                            {isDone ? (
                                              <span className="h-1.5 w-1.5 rounded-full bg-foreground" />
                                            ) : isRunning ? (
                                              <span className="h-1.5 w-1.5 rounded-full bg-ink animate-ping" />
                                            ) : step.status === "failed" ? (
                                              <span className="h-1.5 w-1.5 rounded-full bg-destructive" />
                                            ) : (
                                              <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/30" />
                                            )}
                                          </span>
                                          <div className="pl-3 flex-1">
                                            <p
                                              className={cn(
                                                "font-semibold",
                                                isRunning ? "text-ink" : "text-foreground",
                                              )}
                                            >
                                              {step.agentName}
                                            </p>
                                            <p className="text-[10px] text-muted-foreground mt-0.5">
                                              {step.summary ??
                                                (isRunning
                                                  ? "Working…"
                                                  : step.status === "pending"
                                                    ? "Queued"
                                                    : "")}
                                            </p>
                                          </div>
                                        </div>
                                      );
                                    })}
                                  </div>
                                )}

                                {m.run.error && (
                                  <p className="text-[11px] text-destructive">{m.run.error}</p>
                                )}

                                {m.run.isComplete &&
                                  Object.entries(m.run.agentOutputs).map(([agentId, output]) => (
                                    <div
                                      key={agentId}
                                      className="border-t border-border pt-4 animate-in fade-in slide-in-from-top-2 duration-500"
                                    >
                                      <AgentOutput
                                        agentId={agentId}
                                        output={output}
                                        onTailor={handleTailorResume}
                                      />
                                    </div>
                                  ))}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })
                  )}
                  <div ref={chatEndRef} />
                </div>
              </div>

              {/* Bottom chat input */}
              <div className="shrink-0 border-t border-border">
                <div className="mx-auto w-full max-w-3xl px-6 py-4">
                  <div className="flex items-end gap-3 border border-border rounded-lg p-2.5 bg-background focus-within:border-ink transition-all duration-300 shadow-2xs">
                    <textarea
                      ref={inputRef}
                      rows={1}
                      value={chatDraft}
                      onChange={(e) => setChatDraft(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          handleSend();
                        }
                      }}
                      disabled={isOrchestrating}
                      placeholder={
                        isOrchestrating
                          ? "Waiting for agents to orchestrate..."
                          : "Ask your multi-agent compass..."
                      }
                      className="max-h-24 flex-1 resize-none bg-transparent py-1 px-2 text-xs outline-none placeholder:text-muted-foreground/60 focus:ring-0 leading-normal scrollbar-none"
                    />
                    <button
                      onClick={handleSend}
                      disabled={!chatDraft.trim() || isOrchestrating}
                      aria-label="Send message"
                      className={cn(
                        "rounded-md border p-2 transition-all duration-300 shrink-0",
                        chatDraft.trim() && !isOrchestrating
                          ? "border-ink text-ink bg-accent/5 hover:scale-105"
                          : "border-border text-muted-foreground opacity-50 cursor-not-allowed",
                      )}
                    >
                      {isOrchestrating ? (
                        <Loader2 size={13} className="animate-spin text-muted-foreground" />
                      ) : (
                        <ArrowUp size={13} strokeWidth={1.5} />
                      )}
                    </button>
                  </div>
                  <div className="mt-2 text-center">
                    <span className="text-[9px] text-muted-foreground uppercase tracking-widest">
                      connected to all 7 active agents
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}

// Wrapper mock components for OutlineIcon alignment checks (LineButton imports)
function LineButton({
  children,
  variant = "outline",
  onClick,
  className,
  disabled,
}: {
  children: React.ReactNode;
  variant?: "solid" | "outline" | "ghost";
  onClick?: () => void;
  className?: string;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "rounded-md text-[11px] px-3.5 py-2 font-medium tracking-wide transition-all duration-300 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed",
        variant === "solid" &&
          "bg-primary text-primary-foreground border border-transparent hover:bg-primary/95 shadow-sm",
        variant === "outline" &&
          "border border-border text-foreground hover:border-ink hover:text-ink bg-background",
        variant === "ghost" && "text-muted-foreground hover:text-foreground bg-transparent",
        className,
      )}
    >
      {children}
    </button>
  );
}
