import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { Chatbot } from "./Chatbot";
import { AnimatedLines } from "./AnimatedLines";

function CompassMark() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 44 44"
      fill="none"
      aria-hidden="true"
      className="compass-logo shrink-0"
    >
      <circle cx="22" cy="22" r="20" stroke="currentColor" strokeWidth="1.25" className="text-foreground" />
      <circle cx="22" cy="22" r="13" stroke="currentColor" strokeWidth="0.5" strokeDasharray="2.5 2.5" className="text-muted-foreground" />
      <line x1="22" y1="2"  x2="22" y2="8"  stroke="currentColor" strokeWidth="2" className="text-foreground" />
      <line x1="22" y1="36" x2="22" y2="42" stroke="currentColor" strokeWidth="2" className="text-foreground" />
      <line x1="2"  y1="22" x2="8"  y2="22" stroke="currentColor" strokeWidth="2" className="text-foreground" />
      <line x1="36" y1="22" x2="42" y2="22" stroke="currentColor" strokeWidth="2" className="text-foreground" />
      <circle cx="22" cy="22" r="1.5" fill="currentColor" className="text-ink" />
      <polygon points="22,8 20.4,22 22,20.5 23.6,22"  fill="currentColor" className="compass-needle text-ink" />
      <polygon points="22,36 20.4,22 22,23.5 23.6,22" fill="currentColor" className="compass-needle text-muted-foreground" style={{ opacity: 0.45 }} />
    </svg>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="relative min-h-screen bg-background">
      {/* Global animated line field — subtle on interior pages */}
      <AnimatedLines count={36} seed={0xcafebabe} />

      <header className="sticky top-0 z-40 border-b border-border bg-background/85 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-6">
          <Link
            to="/dashboard"
            className="group flex items-center gap-2.5 transition-opacity hover:opacity-80"
          >
            <CompassMark />
            <span
              className="text-sm font-medium tracking-tight"
              style={{ fontFamily: "var(--font-display)" }}
            >
              Career&nbsp;Compass
            </span>
          </Link>
          <nav className="flex items-center gap-6 text-sm text-muted-foreground">
            <Link
              to="/dashboard"
              className="transition-colors duration-300 hover:text-ink [&.active]:text-foreground"
            >
              Agents
            </Link>
            <Link
              to="/profile"
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

      <main className="relative z-10 mx-auto max-w-5xl px-6 py-12">{children}</main>
      <Chatbot />
    </div>
  );
}
