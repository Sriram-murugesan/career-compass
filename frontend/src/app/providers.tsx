"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { UserProfileProvider } from "@/context/UserProfileContext";
import { ChatProvider } from "@/context/ChatContext";
import { Toaster } from "@/components/ui/sonner";

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <UserProfileProvider>
        <ChatProvider>
          {children}
          <Toaster position="top-right" />
        </ChatProvider>
      </UserProfileProvider>
    </QueryClientProvider>
  );
}
