import { useEffect, useRef, useState } from "react";
import { MessageCircle, X, ArrowUp } from "lucide-react";
import { OutlineIcon } from "./OutlineIcon";
import { cn } from "@/lib/utils";

type Msg = { id: number; role: "bot" | "user"; text: string };

const seed: Msg[] = [
  {
    id: 1,
    role: "bot",
    text: "I'm your compass. Ask me about your resume, matches, or what to do next.",
  },
];

export function Chatbot() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Msg[]>(seed);
  const [draft, setDraft] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = () => {
    const text = draft.trim();
    if (!text) return;
    const id = Date.now();
    setMessages((m) => [...m, { id, role: "user", text }]);
    setDraft("");
    setTimeout(() => {
      setMessages((m) => [
        ...m,
        {
          id: id + 1,
          role: "bot",
          text: "Noted. I'll route that to the right agent and follow up on your dashboard.",
        },
      ]);
    }, 500);
    inputRef.current?.focus();
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">
      {open && (
        <div className="rise-in flex h-[26rem] w-[21rem] flex-col rounded-lg border border-border bg-card">
          <header className="flex items-center justify-between border-b border-border px-4 py-3">
            <div>
              <p className="text-sm font-medium">Assistant</p>
              <p className="text-xs text-muted-foreground">Connected to all 7 agents</p>
            </div>
            <button
              onClick={() => setOpen(false)}
              aria-label="Close assistant"
              className="draw-icon text-muted-foreground transition-colors hover:text-ink"
            >
              <X size={16} strokeWidth={1.5} />
            </button>
          </header>

          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
            {messages.map((m) => (
              <div
                key={m.id}
                className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}
              >
                <p
                  className={cn(
                    "max-w-[85%] rounded-md border px-3 py-2 text-sm leading-relaxed",
                    m.role === "bot"
                      ? "border-border text-foreground"
                      : "border-border-strong text-muted-foreground",
                  )}
                >
                  {m.text}
                </p>
              </div>
            ))}
            <div ref={endRef} />
          </div>

          <div className="flex items-end gap-2 border-t border-border px-3 py-3">
            <textarea
              ref={inputRef}
              rows={1}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              placeholder="Ask anything…"
              className="max-h-24 flex-1 resize-none bg-transparent py-1 text-sm outline-none placeholder:text-muted-foreground"
            />
            <button
              onClick={send}
              aria-label="Send message"
              className="draw-icon rounded-md border border-border p-1.5 text-muted-foreground transition-colors duration-300 hover:border-ink hover:text-ink"
            >
              <ArrowUp size={15} strokeWidth={1.5} />
            </button>
          </div>
        </div>
      )}

      <button
        onClick={() => setOpen((o) => !o)}
        aria-label="Open assistant"
        className="group flex h-11 w-11 items-center justify-center rounded-full border border-border bg-background transition-colors duration-300 [transition-timing-function:cubic-bezier(0.65,0,0.35,1)] hover:border-ink"
      >
        <OutlineIcon icon={MessageCircle} size={19} />
      </button>
    </div>
  );
}
