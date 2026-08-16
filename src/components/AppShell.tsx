import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { Chatbot } from "./Chatbot";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 border-b border-border bg-background/85 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-6">
          <Link to="/dashboard" className="text-sm font-medium tracking-tight">
            Career&nbsp;Compass
          </Link>
          <nav className="flex items-center gap-6 text-sm text-muted-foreground">
            <Link
              to="/dashboard"
              className="transition-colors duration-300 hover:text-ink [&.active]:text-foreground"
            >
              Agents
            </Link>
            <Link
              to="/setup"
              className="transition-colors duration-300 hover:text-ink [&.active]:text-foreground"
            >
              Profile
            </Link>
            <Link to="/" className="transition-colors duration-300 hover:text-ink">
              Sign out
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-12">{children}</main>
      <Chatbot />
    </div>
  );
}
