/**
 * Run the agents and receive their progress live (Server-Sent Events over POST).
 * EventSource can't send a body or an Authorization header, so this reads the
 * response stream directly.
 */

import { API_BASE_URL, API_ENDPOINTS, ApiRequestError, type ApiEnvelope } from "@/lib/api";

export interface StepEvent {
  type: "step";
  agentId: string;
  agentName: string;
  status: "running" | "completed" | "failed";
  summary?: string;
  usedLlm?: boolean;
}

export interface AnswerEvent {
  type: "answer";
  runId: string;
  answer: string;
  /** backend agent id → that agent's output (camelCase) */
  agentOutputs: Record<string, Record<string, unknown>>;
  steps: Array<{ agentId: string; agentName: string; status: string; summary: string }>;
}

export type OrchestrateEvent =
  | { type: "conversation"; conversationId: string }
  | { type: "plan"; plan: string[][] }
  | StepEvent
  | AnswerEvent
  | { type: "memory"; saved: number }
  | { type: "done" }
  | { type: "error"; message: string };

export interface OrchestrateRequest {
  message: string;
  conversationId?: string | null;
  /** Run exactly these backend agents (plus what they require). */
  agents?: string[];
}

export async function streamOrchestrate(
  body: OrchestrateRequest,
  accessToken: string,
  onEvent: (event: OrchestrateEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.chat.orchestrate}`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
      body: JSON.stringify(body),
      signal: signal ?? null,
    });
  } catch {
    throw new ApiRequestError(
      0,
      "NETWORK_ERROR",
      "Can't reach the server. Is the backend running?",
    );
  }

  if (!response.ok || !response.body) {
    const envelope = (await response.json().catch(() => null)) as ApiEnvelope<null> | null;
    throw new ApiRequestError(
      response.status,
      envelope?.error?.code ?? "HTTP_ERROR",
      envelope?.error?.message ?? `Request failed (${response.status})`,
    );
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let boundary: number;
    while ((boundary = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const data = block.split("\n").find((line) => line.startsWith("data: "));
      if (data) onEvent(JSON.parse(data.slice("data: ".length)) as OrchestrateEvent);
    }
  }
}
