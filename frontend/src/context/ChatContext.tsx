"use client";

/**
 * Chat with the agents — real conversations and real runs.
 *
 * - Conversations and their messages come from /api/chat/conversations.
 * - Sending a message calls POST /api/chat/orchestrate and renders its live
 *   event stream: the plan, each agent's progress, then the answer and every
 *   agent's real output. The backend saves both messages.
 */

import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { getAgentByBackendId } from "@/lib/agents";
import { API_ENDPOINTS, ApiRequestError } from "@/lib/api";
import { streamOrchestrate, type OrchestrateEvent } from "@/lib/orchestrate";

export interface RunStep {
  /** backend agent id */
  agentId: string;
  agentName: string;
  status: "pending" | "running" | "completed" | "failed";
  summary?: string | undefined;
}

export interface AgentRun {
  steps: RunStep[];
  isComplete: boolean;
  /** backend agent id → its output */
  agentOutputs: Record<string, Record<string, unknown>>;
  error?: string | undefined;
}

export interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  timestamp: string;
  run?: AgentRun | undefined;
}

export interface Conversation {
  id: string;
  title: string;
  lastUpdated: string;
  messages: ChatMessage[];
  /** Messages fetched from the server (lists only carry titles). */
  loaded: boolean;
}

interface ChatContextType {
  isChatActive: boolean;
  setChatActive: (active: boolean) => void;
  conversations: Conversation[];
  activeConversationId: string | null;
  setActiveConversationId: (id: string | null) => void;
  sendMessage: (text: string) => void;
  startNewConversation: (initialMessage?: string) => void;
  deleteConversation: (id: string) => void;
  isOrchestrating: boolean;
}

interface ApiConversation {
  id: string;
  title: string;
  updatedAt: string;
}

interface ApiMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  payload: {
    steps?: Array<{ agentId: string; agentName: string; status: string; summary: string }>;
    agentOutputs?: Record<string, Record<string, unknown>>;
  } | null;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

const NEW_CONVERSATION = "__new__";

const agentName = (backendId: string) => getAgentByBackendId(backendId)?.name ?? backendId;

function toMessage(m: ApiMessage): ChatMessage {
  const steps = m.payload?.steps ?? [];
  return {
    id: m.id,
    sender: m.role,
    text: m.content,
    timestamp: m.createdAt,
    run:
      m.role === "assistant" && (steps.length || m.payload?.agentOutputs)
        ? {
            steps: steps.map((s) => ({
              agentId: s.agentId,
              agentName: s.agentName || agentName(s.agentId),
              status: s.status === "failed" ? "failed" : "completed",
              summary: s.summary,
            })),
            isComplete: true,
            agentOutputs: m.payload?.agentOutputs ?? {},
          }
        : undefined,
  };
}

export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, authFetch, getAccessToken } = useAuth();
  const [isChatActive, setChatActive] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [isOrchestrating, setIsOrchestrating] = useState(false);
  const loading = useRef(new Set<string>());

  // Load the conversation list when the signed-in ACCOUNT changes (not on every
  // token refresh, which hands us a new user object for the same account).
  const userId = user?.id ?? null;
  useEffect(() => {
    setConversations([]);
    setActiveConversationId(null);
    if (!userId) return;
    let active = true;
    authFetch<ApiConversation[]>(API_ENDPOINTS.chat.conversations)
      .then((res) => {
        if (!active) return;
        // Merge, don't replace: a message may have been sent while the list was loading,
        // and its live run must not be wiped by the (older) server list.
        setConversations((current) => {
          const known = new Map(current.map((c) => [c.id, c]));
          const fromServer = res.data.map(
            (c): Conversation =>
              known.get(c.id) ?? {
                id: c.id,
                title: c.title,
                lastUpdated: c.updatedAt,
                messages: [],
                loaded: false,
              },
          );
          const serverIds = new Set(res.data.map((c) => c.id));
          return [...current.filter((c) => !serverIds.has(c.id)), ...fromServer];
        });
      })
      .catch(() => active && toast.error("Couldn't load your conversations."));
    return () => {
      active = false;
    };
  }, [userId, authFetch]);

  // Fetch a conversation's messages the first time it's opened.
  useEffect(() => {
    const id = activeConversationId;
    if (!id || id === NEW_CONVERSATION || loading.current.has(id)) return;
    const conversation = conversations.find((c) => c.id === id);
    if (!conversation || conversation.loaded) return;
    loading.current.add(id);
    authFetch<{ messages: ApiMessage[] }>(API_ENDPOINTS.chat.conversation(id))
      .then((res) => {
        setConversations((prev) =>
          prev.map((c) =>
            c.id === id ? { ...c, messages: res.data.messages.map(toMessage), loaded: true } : c,
          ),
        );
      })
      .catch(() => toast.error("Couldn't load this conversation."))
      .finally(() => loading.current.delete(id));
  }, [activeConversationId, conversations, authFetch]);

  const updateConversation = useCallback(
    (id: string, change: (conversation: Conversation) => Conversation) => {
      setConversations((prev) => prev.map((c) => (c.id === id ? change(c) : c)));
    },
    [],
  );

  const startNewConversation = useCallback((initialMessage?: string) => {
    setConversations((prev) => prev.filter((c) => c.id !== NEW_CONVERSATION));
    setActiveConversationId(null);
    setChatActive(true);
    if (initialMessage) {
      // Defer so the reset above is applied first.
      setTimeout(() => sendMessageRef.current?.(initialMessage), 0);
    }
  }, []);

  const deleteConversation = useCallback(
    (id: string) => {
      authFetch(API_ENDPOINTS.chat.conversation(id), { method: "DELETE" })
        .then(() => {
          setConversations((prev) => prev.filter((c) => c.id !== id));
          setActiveConversationId((current) => (current === id ? null : current));
        })
        .catch(() => toast.error("Couldn't delete this conversation."));
    },
    [authFetch],
  );

  const sendMessage = useCallback(
    (text: string) => {
      if (isOrchestrating || !text.trim()) return;
      const existingId =
        activeConversationId && activeConversationId !== NEW_CONVERSATION
          ? activeConversationId
          : null;
      let conversationId = existingId ?? NEW_CONVERSATION;
      const now = new Date().toISOString();
      const assistantId = crypto.randomUUID();
      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        sender: "user",
        text,
        timestamp: now,
      };
      const placeholder: ChatMessage = {
        id: assistantId,
        sender: "assistant",
        text: "",
        timestamp: now,
        run: { steps: [], isComplete: false, agentOutputs: {} },
      };

      setConversations((prev) => {
        if (existingId) {
          return prev.map((c) =>
            c.id === existingId ? { ...c, messages: [...c.messages, userMessage, placeholder] } : c,
          );
        }
        const draft: Conversation = {
          id: NEW_CONVERSATION,
          title: text.length > 60 ? `${text.slice(0, 57)}…` : text,
          lastUpdated: now,
          messages: [userMessage, placeholder],
          loaded: true,
        };
        return [draft, ...prev.filter((c) => c.id !== NEW_CONVERSATION)];
      });
      setActiveConversationId(conversationId);
      setChatActive(true);
      setIsOrchestrating(true);

      const patchRun = (change: (run: AgentRun, message: ChatMessage) => Partial<ChatMessage>) =>
        updateConversation(conversationId, (c) => ({
          ...c,
          messages: c.messages.map((m) =>
            m.id === assistantId && m.run ? { ...m, ...change(m.run, m) } : m,
          ),
        }));

      const onEvent = (event: OrchestrateEvent) => {
        switch (event.type) {
          case "conversation":
            if (conversationId === NEW_CONVERSATION) {
              const realId = event.conversationId;
              setConversations((prev) =>
                prev.map((c) => (c.id === NEW_CONVERSATION ? { ...c, id: realId } : c)),
              );
              setActiveConversationId(realId);
              conversationId = realId;
            }
            break;
          case "plan":
            patchRun((run) => ({
              run: {
                ...run,
                steps: event.plan.flat().map((id) => ({
                  agentId: id,
                  agentName: agentName(id),
                  status: "pending" as const,
                })),
              },
            }));
            break;
          case "step":
            patchRun((run) => ({
              run: {
                ...run,
                steps: run.steps.map((s) =>
                  s.agentId === event.agentId
                    ? { ...s, status: event.status, summary: event.summary ?? s.summary }
                    : s,
                ),
              },
            }));
            break;
          case "answer":
            patchRun((run) => ({
              text: event.answer,
              run: { ...run, isComplete: true, agentOutputs: event.agentOutputs },
            }));
            break;
          case "error":
            patchRun((run) => ({ run: { ...run, isComplete: true, error: event.message } }));
            break;
          default:
            break;
        }
      };

      const run = async () => {
        let token = getAccessToken();
        const body = { message: text, conversationId: existingId };
        try {
          if (!token) throw new ApiRequestError(401, "TOKEN_MISSING", "Not signed in");
          await streamOrchestrate(body, token, onEvent);
        } catch (error) {
          if (error instanceof ApiRequestError && error.status === 401) {
            // Access token expired mid-session: refresh (authFetch does it) and retry once.
            await authFetch(API_ENDPOINTS.auth.session).catch(() => undefined);
            token = getAccessToken();
            if (token) {
              await streamOrchestrate(body, token, onEvent);
              return;
            }
          }
          throw error;
        }
      };

      run()
        .catch((error) => {
          const message =
            error instanceof ApiRequestError ? error.message : "The agents hit a problem.";
          patchRun((r) => ({ run: { ...r, isComplete: true, error: message } }));
          toast.error(message);
        })
        .finally(() => {
          setIsOrchestrating(false);
          updateConversation(conversationId, (c) => ({
            ...c,
            lastUpdated: new Date().toISOString(),
          }));
        });
    },
    [isOrchestrating, activeConversationId, updateConversation, getAccessToken, authFetch],
  );

  const sendMessageRef = useRef(sendMessage);
  sendMessageRef.current = sendMessage;

  return (
    <ChatContext.Provider
      value={{
        isChatActive,
        setChatActive,
        conversations,
        activeConversationId,
        setActiveConversationId,
        sendMessage,
        startNewConversation,
        deleteConversation,
        isOrchestrating,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error("useChat must be used within a ChatProvider");
  }
  return context;
};
