"use client";

import { usePathname, useRouter } from "next/navigation";
import { MessageCircle, X } from "lucide-react";
import { OutlineIcon } from "./OutlineIcon";
import { useChat } from "@/context/ChatContext";

export function Chatbot() {
  const pathname = usePathname();
  const router = useRouter();
  const { isChatActive, setChatActive } = useChat();

  // Hide the floating button on the sign-in/up page
  if (pathname === "/") {
    return null;
  }

  const handleToggle = () => {
    if (pathname !== "/dashboard") {
      // If we are not on the dashboard, navigate there and activate the chat mode
      setChatActive(true);
      router.push("/dashboard");
    } else {
      // Otherwise, toggle the chat mode active state on the dashboard
      setChatActive(!isChatActive);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      <button
        onClick={handleToggle}
        aria-label={isChatActive ? "Close assistant" : "Open assistant"}
        className="group flex h-12 w-12 items-center justify-center rounded-full border border-border bg-background shadow-lg transition-all duration-300 [transition-timing-function:cubic-bezier(0.65,0,0.35,1)] hover:border-ink hover:scale-105"
      >
        {isChatActive ? (
          <X
            size={20}
            strokeWidth={1.5}
            className="text-ink animate-in fade-in zoom-in-50 duration-200"
          />
        ) : (
          <OutlineIcon icon={MessageCircle} size={20} />
        )}
      </button>
    </div>
  );
}
