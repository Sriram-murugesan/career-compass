import React, { createContext, useContext, useState, useEffect } from "react";
import { useUserProfile } from "./UserProfileContext";

export interface OrchestrationStep {
  agentId: string;
  agentName: string;
  status: "idle" | "running" | "completed";
  details: string;
}

export interface OrchestrationData {
  steps: OrchestrationStep[];
  activeStepIndex: number;
  isComplete: boolean;
  resultType?: "jobs" | "validation" | "roadmap" | "advice" | "interview" | "text";
  resultData?: any;
}

export interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  timestamp: string;
  isOrchestration?: boolean;
  orchestration?: OrchestrationData;
}

export interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  lastUpdated: string;
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

const ChatContext = createContext<ChatContextType | undefined>(undefined);

const STORAGE_KEY = "career_compass_chat_v1";

const DEFAULT_CONVERSATIONS: Conversation[] = [
  {
    id: "conv-1",
    title: "Resume & Validation Check",
    messages: [
      {
        id: "msg-1-1",
        sender: "assistant",
        text: "Hello! I'm your multi-agent Career Compass. How can I help you accelerate your job search today?",
        timestamp: "2 hours ago",
      },
      {
        id: "msg-1-2",
        sender: "user",
        text: "Can you review my resume formatting?",
        timestamp: "2 hours ago",
      },
      {
        id: "msg-1-3",
        sender: "assistant",
        text: "I routed your resume to the **Validation Agent** and the **Resume Builder**. They completed 6 compliance checks. Your ATS readability score is 92%. Two bullets are flagged for length validation.",
        timestamp: "2 hours ago",
        isOrchestration: true,
        orchestration: {
          isComplete: true,
          activeStepIndex: 1,
          steps: [
            { agentId: "resume", agentName: "Resume Agent", status: "completed", details: "Retrieved CV parsed context" },
            { agentId: "validation", agentName: "Validation Agent", status: "completed", details: "Checked formatting & layout compatibility" }
          ],
          resultType: "validation",
          resultData: [
            { label: "Contact block parsable", state: "pass", note: "Email and phone detected" },
            { label: "Reverse-chronological order", state: "pass", note: "Consistent across roles" },
            { label: "Bullet length", state: "warn", note: "Two bullets exceed 24 words" },
            { label: "No tables or text boxes", state: "pass", note: "Clean single-column layout" }
          ]
        }
      }
    ],
    lastUpdated: "2 hours ago",
  },
  {
    id: "conv-2",
    title: "Senior Role Exploration",
    messages: [
      {
        id: "msg-2-1",
        sender: "assistant",
        text: "Welcome! Tell me what kind of roles you are targeting, and I will orchestrate a search.",
        timestamp: "Yesterday",
      },
      {
        id: "msg-2-2",
        sender: "user",
        text: "Find me some Senior Frontend roles",
        timestamp: "Yesterday",
      },
      {
        id: "msg-2-3",
        sender: "assistant",
        text: "I orchestrated a target job search matching your Senior Full-Stack Engineer profile. The **Job Search Agent** surfaced 3 roles matching TypeScript & React. I've also run a **Validation Check** against your resume.",
        timestamp: "Yesterday",
        isOrchestration: true,
        orchestration: {
          isComplete: true,
          activeStepIndex: 2,
          steps: [
            { agentId: "job-search", agentName: "Job Search Agent", status: "completed", details: "Queried matching API roles" },
            { agentId: "validation", agentName: "Validation Agent", status: "completed", details: "Checked ATS keyword intersection" }
          ],
          resultType: "jobs",
          resultData: [
            {
              id: "job-1",
              role: "Senior Frontend Engineer",
              co: "Kepler Systems",
              loc: "London · Hybrid",
              type: "Full-time",
              match: 96,
              salary: "£95k - £115k",
              keywords: ["TypeScript", "Micro-frontends", "Performance"],
              desc: "Seeking a Senior Engineer to lead frontend architecture and real-time design system pipelines."
            },
            {
              id: "job-3",
              role: "Staff AI Product Engineer",
              co: "Ostara AI",
              loc: "San Francisco · Remote",
              type: "Full-time",
              match: 88,
              salary: "$180k - $210k",
              keywords: ["React", "TypeScript", "LLM Tooling"],
              desc: "Lead customer-facing AI agent interfaces and interactive canvas workflows."
            }
          ]
        }
      }
    ],
    lastUpdated: "Yesterday",
  }
];

export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { profile, logActivity } = useUserProfile();
  const [isChatActive, setChatActive] = useState<boolean>(false);
  const [conversations, setConversations] = useState<Conversation[]>(() => {
    if (typeof window === "undefined") return DEFAULT_CONVERSATIONS;
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (e) {
      console.error("Failed to load chat history:", e);
    }
    return DEFAULT_CONVERSATIONS;
  });

  const [activeConversationId, setActiveConversationId] = useState<string | null>(() => {
    if (conversations.length > 0) return conversations[0]!.id;
    return null;
  });

  const [isOrchestrating, setIsOrchestrating] = useState<boolean>(false);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
    } catch (e) {
      console.error("Failed to save chat history:", e);
    }
  }, [conversations]);

  const startNewConversation = (initialMessage?: string) => {
    const newId = `conv-${Date.now()}`;
    const newConv: Conversation = {
      id: newId,
      title: initialMessage ? (initialMessage.length > 25 ? initialMessage.slice(0, 25) + "..." : initialMessage) : "New Conversation",
      messages: [
        {
          id: `msg-${Date.now()}-init`,
          sender: "assistant",
          text: "I'm connected to all 7 agents in your compass. How can I help you today?",
          timestamp: "Just now",
        },
      ],
      lastUpdated: "Just now",
    };
    setConversations((prev) => [newConv, ...prev]);
    setActiveConversationId(newId);
    setChatActive(true);
  };

  const deleteConversation = (id: string) => {
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeConversationId === id) {
      const remaining = conversations.filter((c) => c.id !== id);
      setActiveConversationId(remaining.length > 0 ? remaining[0]!.id : null);
    }
  };

  const sendMessage = (text: string) => {
    // [API] Replace the local intent-routing simulation below with the orchestrator.
    // POST ENDPOINTS.chat.orchestrate
    //   { conversationId: string | null, message: string }
    // Streams (SSE / chunked JSON) one event per agent step, then a final result:
    //   { type: "step",   step: { agentId, agentName, status, details } }
    //   { type: "result", message: CONVERSATION_TEMPLATE.messages[0] }
    // Non-streaming fallback: POST ENDPOINTS.chat.messages(conversationId)
    //   { text } -> ChatMessage (with .orchestration populated)
    //
    // const res = await apiFetch<typeof CONVERSATION_TEMPLATE.messages[0]>(
    //   ENDPOINTS.chat.messages(convId), { method: "POST", body: JSON.stringify({ text }) });

    const cleanText = text.trim();
    if (!cleanText) return;


    let convId = activeConversationId;
    if (!convId) {
      convId = `conv-${Date.now()}`;
      const newConv: Conversation = {
        id: convId,
        title: cleanText.length > 25 ? cleanText.slice(0, 25) + "..." : cleanText,
        messages: [],
        lastUpdated: "Just now",
      };
      setConversations((prev) => [newConv, ...prev]);
      setActiveConversationId(convId);
    }

    const timestamp = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}-user`,
      sender: "user",
      text: cleanText,
      timestamp,
    };

    // Update conversation with user message
    setConversations((prev) =>
      prev.map((c) => {
        if (c.id === convId) {
          const isNewTitle = c.title === "New Conversation" || c.messages.length === 0 || (c.messages.length === 1 && c.messages[0]!.id.includes("init"));
          return {
            ...c,
            title: isNewTitle ? (cleanText.length > 25 ? cleanText.slice(0, 25) + "..." : cleanText) : c.title,
            messages: [...c.messages, userMsg],
            lastUpdated: "Just now",
          };
        }
        return c;
      })
    );

    // Intent Routing analysis
    const queryLower = cleanText.toLowerCase();
    let selectedAgents: OrchestrationStep[] = [];
    let resultType: OrchestrationData["resultType"] = "text";
    let resultData: any = null;

    if (queryLower.includes("job") || queryLower.includes("search") || queryLower.includes("find") || queryLower.includes("kepler") || queryLower.includes("work")) {
      selectedAgents = [
        { agentId: "job-search", agentName: "Job Search Agent", status: "idle", details: "Scanning for matching roles..." },
        { agentId: "resume", agentName: "Resume Agent", status: "idle", details: "Aligning CV to target roles..." },
        { agentId: "validation", agentName: "Validation Agent", status: "idle", details: "Checking ATS compliance..." },
      ];
      resultType = "jobs";
      resultData = [
        {
          id: "job-1",
          role: "Senior Frontend Engineer",
          co: "Kepler Systems",
          loc: "London · Hybrid",
          type: "Full-time",
          match: 96,
          salary: "£95k - £115k",
          keywords: ["TypeScript", "Micro-frontends", "Performance", "System Architecture"],
          desc: "Seeking a Senior Engineer to lead frontend architecture and real-time design system pipelines.",
        },
        {
          id: "job-2",
          role: "Platform Engineer",
          co: "Northwind Labs",
          loc: "Remote (EU/US)",
          type: "Full-time",
          match: 91,
          salary: "$165k - $190k",
          keywords: ["Python", "Kubernetes", "DevOps", "AI Infrastructure"],
          desc: "Build scalable cloud orchestration and agent evaluation frameworks for high-throughput AI workloads.",
        },
        {
          id: "job-3",
          role: "Staff AI Product Engineer",
          co: "Ostara AI",
          loc: "San Francisco · Remote",
          type: "Full-time",
          match: 88,
          salary: "$180k - $210k",
          keywords: ["React", "TypeScript", "LLM Tooling", "Product Design"],
          desc: "Lead customer-facing AI agent interfaces and interactive canvas workflows.",
        },
      ];
    } else if (queryLower.includes("resume") || queryLower.includes("cv") || queryLower.includes("validation") || queryLower.includes("check") || queryLower.includes("formatting") || queryLower.includes("ats")) {
      selectedAgents = [
        { agentId: "resume", agentName: "Resume Agent", status: "idle", details: "Retrieving current resume parser data..." },
        { agentId: "validation", agentName: "Validation Agent", status: "idle", details: "Auditing layout, section headers, and formatting..." },
      ];
      resultType = "validation";
      resultData = [
        { label: "Contact block parsable", state: "pass", note: "Email and phone detected" },
        { label: "Reverse-chronological order", state: "pass", note: "Consistent across roles" },
        { label: "Bullet length", state: "warn", note: "Two bullets exceed 24 words" },
        { label: "Keyword coverage vs. target roles", state: "pass", note: "TypeScript, React, System Design covered" },
        { label: "No tables or text boxes", state: "pass", note: "Clean single-column layout" },
        { label: "Quantified impact", state: "pass", note: "Metrics verified across bullet points" },
      ];
    } else if (queryLower.includes("roadmap") || queryLower.includes("path") || queryLower.includes("plan") || queryLower.includes("milestone") || queryLower.includes("growth")) {
      selectedAgents = [
        { agentId: "roadmap", agentName: "Personalized Roadmap", status: "idle", details: "Structuring growth trajectory milestones..." },
        { agentId: "advisor", agentName: "Career Advisor", status: "idle", details: "Evaluating technical skill gaps..." },
      ];
      resultType = "roadmap";
      resultData = [
        { title: "Sharpen system design", when: "Weeks 1–3", note: "Two design reviews per week." },
        { title: "Ship a public project", when: "Weeks 4–7", note: "Something infra-flavoured and small." },
        { title: "Targeted applications", when: "Weeks 8–10", note: "Twelve roles, all senior scope." },
        { title: "Interview loops", when: "Weeks 11–14", note: "Expect three onsite processes." },
      ];
    } else if (queryLower.includes("interview") || queryLower.includes("prep") || queryLower.includes("practice") || queryLower.includes("question")) {
      selectedAgents = [
        { agentId: "interview", agentName: "Interview Preparation", status: "idle", details: "Retrieving custom interview banks..." },
        { agentId: "advisor", agentName: "Career Advisor", status: "idle", details: "Formulating mock parameters..." },
      ];
      resultType = "interview";
      resultData = [
        "Walk me through a system you designed end to end.",
        "Describe a time you disagreed with a technical decision.",
        "How would you cut p95 latency on a read-heavy API?",
        "What trade-offs did your last migration force?",
        "How do you decide what not to build?",
      ];
    } else {
      selectedAgents = [
        { agentId: "advisor", agentName: "Career Advisor", status: "idle", details: "Analyzing query in profile context..." },
      ];
      resultType = "text";
      resultData = "Your career pipeline is fully sync'd! You can tell me to search for jobs, validate your resume, build a milestone roadmap, or run a practice interview. What agent shall we invoke?";
    }

    // Set orchestrating state
    setIsOrchestrating(true);

    const orchestrationId = `msg-${Date.now()}-orchestration`;
    const initialOrchMsg: ChatMessage = {
      id: orchestrationId,
      sender: "assistant",
      text: "Routing intent via Orchestrator...",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      isOrchestration: true,
      orchestration: {
        steps: selectedAgents.map((s, idx) => (idx === 0 ? { ...s, status: "running" } : s)),
        activeStepIndex: 0,
        isComplete: false,
        resultType,
      },
    };

    // Add orchestration message
    setConversations((prev) =>
      prev.map((c) => {
        if (c.id === convId) {
          return {
            ...c,
            messages: [...c.messages, initialOrchMsg],
          };
        }
        return c;
      })
    );

    // Simulate multi-agent execution step-by-step
    let currentStep = 0;

    const runNextStep = () => {
      setTimeout(() => {
        currentStep++;
        if (currentStep < selectedAgents.length) {
          // Advance step
          setConversations((prev) =>
            prev.map((c) => {
              if (c.id === convId) {
                return {
                  ...c,
                  messages: c.messages.map((m) => {
                    if (m.id === orchestrationId && m.orchestration) {
                      const updatedSteps = m.orchestration.steps.map((s, idx) => {
                        if (idx === currentStep - 1) return { ...s, status: "completed" as const, details: s.details.replace("...", "") + " (Success)" };
                        if (idx === currentStep) return { ...s, status: "running" as const };
                        return s;
                      });
                      return {
                        ...m,
                        orchestration: {
                          ...m.orchestration,
                          activeStepIndex: currentStep,
                          steps: updatedSteps,
                        },
                      };
                    }
                    return m;
                  }),
                };
              }
              return c;
            })
          );
          runNextStep();
        } else {
          // Complete orchestration
          setIsOrchestrating(false);
          setConversations((prev) =>
            prev.map((c) => {
              if (c.id === convId) {
                return {
                  ...c,
                  messages: c.messages.map((m) => {
                    if (m.id === orchestrationId && m.orchestration) {
                      const finalSteps = m.orchestration.steps.map((s) => ({
                        ...s,
                        status: "completed" as const,
                        details: s.details.replace("...", "") + " (Success)",
                      }));

                      let finalResponse = "";
                      if (resultType === "jobs") {
                        finalResponse = `I orchestrated a target role scan. The **Job Search Agent** found 3 new openings matching your skills. The **Resume Agent** and **Validation Agent** evaluated your credentials for optimization.`;
                        logActivity({
                          type: "job_searched",
                          title: `Assistant searched: "${cleanText}"`,
                          details: `Found 3 matched roles for ${profile.title}.`,
                        });
                      } else if (resultType === "validation") {
                        finalResponse = `I ran the **Validation Agent** check on your resume. Here are the compliance check results. Please optimize the bullet points identified.`;
                        logActivity({
                          type: "profile_updated",
                          title: "Assistant checked Resume Validation",
                          details: "Completed layout and parsing tests.",
                        });
                      } else if (resultType === "roadmap") {
                        finalResponse = `I structured your 14-week **Personalized Roadmap** focusing on target milestones.`;
                      } else if (resultType === "interview") {
                        finalResponse = `I pulled 5 custom mock questions from the **Interview Prep Agent** banks.`;
                      } else {
                        finalResponse = resultData;
                      }

                      return {
                        ...m,
                        text: finalResponse,
                        orchestration: {
                          ...m.orchestration,
                          isComplete: true,
                          steps: finalSteps,
                          resultData,
                        },
                      };
                    }
                    return m;
                  }),
                };
              }
              return c;
            })
          );
        }
      }, 1000);
    };

    runNextStep();
  };

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
