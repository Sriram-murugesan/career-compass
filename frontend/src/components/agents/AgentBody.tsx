"use client";

/**
 * One agent's workspace: run the REAL agent and show its REAL output.
 *
 * Each agent page keeps its own conversation on the backend (remembered per
 * user in this browser), so its last result is shown again on return and
 * agents keep building on what they produced before.
 */

import { useCallback, useEffect, useState } from "react";
import { Loader2, Play, Save } from "lucide-react";
import { toast } from "sonner";
import { AgentOutput } from "@/components/agents/AgentOutput";
import { MockTest } from "@/components/agents/MockTest";
import { ProductivityTracker } from "@/components/agents/ProductivityTracker";
import { LineButton } from "@/components/LineButton";
import { useAuth } from "@/context/AuthContext";
import { formatDate, useUserProfile } from "@/context/UserProfileContext";
import { getAgent, getAgentByBackendId } from "@/lib/agents";
import { API_ENDPOINTS, ApiRequestError } from "@/lib/api";
import { streamOrchestrate, type OrchestrateEvent } from "@/lib/orchestrate";
import { cn } from "@/lib/utils";

type Outputs = Record<string, Record<string, unknown>>;

interface StepView {
  agentId: string;
  name: string;
  status: "pending" | "running" | "completed" | "failed";
  summary?: string | undefined;
}

interface StoredMessage {
  role: string;
  createdAt: string;
  payload: { agentOutputs?: Outputs } | null;
}

const workspaceKey = (userId: string, agentId: string) =>
  `career_compass_agent_conversation_${userId}_${agentId}`;

function readQuery(): URLSearchParams {
  return typeof window === "undefined"
    ? new URLSearchParams()
    : new URLSearchParams(window.location.search);
}

export function AgentBody({ id }: { id: string }) {
  const agent = getAgent(id);
  const { user, authFetch, getAccessToken } = useAuth();
  const { profile, logActivity, saveTailoredResume } = useUserProfile();

  const [request, setRequest] = useState("");
  const [running, setRunning] = useState(false);
  const [steps, setSteps] = useState<StepView[]>([]);
  const [outputs, setOutputs] = useState<Outputs | null>(null);
  const [lastRunAt, setLastRunAt] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [savedResume, setSavedResume] = useState(false);

  // Prefill from a job picked elsewhere (e.g. "Tailor resume" on a job match).
  const query = readQuery();
  const target = {
    role: query.get("jobRole") ?? "",
    company: query.get("company") ?? "",
    location: query.get("loc") ?? "",
  };
  useEffect(() => {
    if (agent?.backendId === "resume" && target.role) {
      setRequest(
        `Tailor my resume for the ${target.role} role${target.company ? ` at ${target.company}` : ""}${
          target.location ? ` (${target.location})` : ""
        }.`,
      );
    }
    // Only on first load of the page.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Restore this agent's last result from its workspace conversation.
  useEffect(() => {
    if (!user || !agent) return;
    const key = workspaceKey(user.id, agent.id);
    const stored = localStorage.getItem(key);
    if (!stored) return;
    setConversationId(stored);
    authFetch<{ messages: StoredMessage[] }>(API_ENDPOINTS.chat.conversation(stored))
      .then((res) => {
        const last = [...res.data.messages]
          .reverse()
          .find((m) => m.role === "assistant" && m.payload?.agentOutputs?.[agent.backendId]);
        if (last?.payload?.agentOutputs) {
          setOutputs(last.payload.agentOutputs);
          setLastRunAt(last.createdAt);
        }
      })
      .catch((err) => {
        if (err instanceof ApiRequestError && err.status === 404) {
          localStorage.removeItem(key); // conversation was deleted from the chat history
          setConversationId(null);
        }
      });
  }, [user, agent, authFetch]);

  const onEvent = useCallback(
    (event: OrchestrateEvent) => {
      if (!agent || !user) return;
      switch (event.type) {
        case "conversation":
          setConversationId(event.conversationId);
          localStorage.setItem(workspaceKey(user.id, agent.id), event.conversationId);
          break;
        case "plan":
          setSteps(
            event.plan.flat().map((backendId) => ({
              agentId: backendId,
              name: getAgentByBackendId(backendId)?.name ?? backendId,
              status: "pending",
            })),
          );
          break;
        case "step":
          setSteps((prev) =>
            prev.map((s) =>
              s.agentId === event.agentId
                ? { ...s, status: event.status, summary: event.summary ?? s.summary }
                : s,
            ),
          );
          break;
        case "answer":
          setOutputs(event.agentOutputs);
          setLastRunAt(new Date().toISOString());
          break;
        case "error":
          setError(event.message);
          break;
        default:
          break;
      }
    },
    [agent, user],
  );

  const run = async () => {
    if (!agent || running) return;
    setRunning(true);
    setError(null);
    setSteps([]);
    setSavedResume(false);
    const body = {
      message: request.trim() || agent.defaultRequest,
      conversationId,
      agents: [agent.backendId],
    };
    try {
      let token = getAccessToken();
      try {
        if (!token) throw new ApiRequestError(401, "TOKEN_MISSING", "Not signed in");
        await streamOrchestrate(body, token, onEvent);
      } catch (err) {
        if (!(err instanceof ApiRequestError) || err.status !== 401) throw err;
        await authFetch(API_ENDPOINTS.auth.session).catch(() => undefined); // refreshes the token
        token = getAccessToken();
        if (!token) throw err;
        await streamOrchestrate(body, token, onEvent);
      }
      if (agent.backendId === "job_search") {
        logActivity({
          type: "job_searched",
          title: "Ran the Job Search Agent",
          details: body.message,
        });
      }
      if (agent.backendId === "interview") {
        logActivity({
          type: "interview_practiced",
          title: "Generated practice interview questions",
          details: body.message,
        });
      }
    } catch (err) {
      const message = err instanceof ApiRequestError ? err.message : "The agent hit a problem.";
      setError(message);
      toast.error(message);
    } finally {
      setRunning(false);
    }
  };

  if (!agent) return null;

  const mine = outputs?.[agent.backendId];
  // Inputs this agent needed that ran alongside it (e.g. the resume a validation checked).
  const supporting = Object.entries(outputs ?? {}).filter(([key]) => key !== agent.backendId);

  const saveResume = () => {
    if (!mine) return;
    const validation = outputs?.["validation"];
    saveTailoredResume({
      jobTitle: String(mine["targetRole"] ?? (target.role || "Target role")),
      company: target.company,
      location: target.location,
      atsScore:
        typeof validation?.["atsScore"] === "number" ? (validation["atsScore"] as number) : null,
      matchedKeywords: Array.isArray(mine["keywords"]) ? (mine["keywords"] as string[]) : [],
      summary: String(mine["summary"] ?? ""),
      bullets: Array.isArray(mine["bullets"]) ? (mine["bullets"] as string[]) : [],
    });
    setSavedResume(true);
    toast.success("Saved to your profile.");
  };

  const profileIsEmpty =
    !profile.title && profile.skills.length === 0 && profile.targetRoles.length === 0;

  const workspace = (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
      {/* Left: what to ask */}
      <section className="space-y-4">
        <h2 className="text-sm font-medium">Run this agent</h2>
        {profileIsEmpty ? (
          <p className="rounded-md border border-dashed border-border p-3 text-[11px] leading-relaxed text-muted-foreground">
            Your profile is empty, so results will be generic. Add your headline, skills and target
            roles on the Profile page first.
          </p>
        ) : null}
        <label className="block">
          <span className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            Request (optional)
          </span>
          <textarea
            value={request}
            onChange={(e) => setRequest(e.target.value)}
            rows={4}
            placeholder={agent.defaultRequest}
            className="mt-2 w-full resize-none rounded-md border border-border bg-transparent p-3 text-xs outline-none placeholder:text-muted-foreground/50 focus:border-ink"
          />
        </label>
        <LineButton variant="solid" onClick={run} disabled={running} className="w-full gap-2">
          {running ? <Loader2 size={13} className="animate-spin" /> : <Play size={12} />}
          {running ? "Running…" : outputs ? "Run again" : "Run agent"}
        </LineButton>

        {steps.length > 0 && (
          <ul className="space-y-2 text-[11px]">
            {steps.map((step) => (
              <li key={step.agentId} className="flex items-start gap-2">
                <span
                  className={cn(
                    "mt-1 h-1.5 w-1.5 shrink-0 rounded-full",
                    step.status === "completed" && "bg-foreground",
                    step.status === "running" && "animate-ping bg-ink",
                    step.status === "failed" && "bg-destructive",
                    step.status === "pending" && "bg-muted-foreground/30",
                  )}
                />
                <span>
                  <span className="font-medium text-foreground">{step.name}</span>
                  <span className="text-muted-foreground">
                    {" "}
                    · {step.summary ?? (step.status === "running" ? "working…" : step.status)}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        )}
        {error ? <p className="text-[11px] text-destructive">{error}</p> : null}
      </section>

      {/* Right: the result */}
      <section className="space-y-4">
        <div className="flex items-baseline justify-between">
          <h2 className="text-sm font-medium">Result</h2>
          {lastRunAt ? (
            <span className="text-[11px] text-muted-foreground">
              Last run {formatDate(lastRunAt)}
            </span>
          ) : null}
        </div>

        {mine ? (
          <div className="space-y-6 rounded-lg border border-border bg-card p-5">
            <AgentOutput agentId={agent.backendId} output={mine} />
            {agent.backendId === "resume" ? (
              <LineButton onClick={saveResume} disabled={savedResume} className="gap-2 text-xs">
                <Save size={12} /> {savedResume ? "Saved to profile" : "Save to profile"}
              </LineButton>
            ) : null}
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-border p-8 text-center text-xs text-muted-foreground">
            {running
              ? "The agent is working…"
              : "No results yet. Run the agent to see its output here."}
          </div>
        )}

        {mine &&
          supporting.map(([backendId, output]) => (
            <details key={backendId} className="rounded-lg border border-border p-4 text-xs">
              <summary className="cursor-pointer text-muted-foreground">
                Input from {getAgentByBackendId(backendId)?.name ?? backendId}
              </summary>
              <div className="mt-4">
                <AgentOutput agentId={backendId} output={output} />
              </div>
            </details>
          ))}
      </section>
    </div>
  );

  // Productivity: a tracker, not an agent run; check-ins save the moment you tap.
  if (agent.backendId === "productivity") return <ProductivityTracker />;
  if (agent.backendId !== "interview") return workspace;
  // Interview Preparation: the scored mock test first, practice questions below.
  return (
    <div className="space-y-12">
      <MockTest />
      <div className="space-y-4 border-t border-border pt-10">
        <h2 className="text-sm font-medium">Practice questions</h2>
        {workspace}
      </div>
    </div>
  );
}
