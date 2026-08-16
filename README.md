# 🧭 Career Compass

Career Compass is a premium, AI multi-agent career platform designed to help job seekers navigate their career transition with maximum deliberation and clarity. By coordinating a pipeline of seven specialized AI agents, the platform refines your profile, tailors resumes to target specs in real-time, validates application readiness, maps out weekly roadmaps, and runs mock interview loops.

---

## 🌟 Key Features

- **7-Agent Pipeline**:
  1. **Resume Builder**: Generates tailored resume versions mapping to specific job specifications.
  2. **Validation Agent**: Audits contacts, reverse-chronological order, and metrics.
  3. **Job Search Agent**: Curates high-match openings based on user preferences.
  4. **Productivity Agent**: Tracks application volumes, goals, and daily streak statistics.
  5. **Roadmap Agent**: Designs multi-week milestone pathways for career growth.
  6. **Career Advisor**: Offers targeted coaching suggestions and strategic action points.
  7. **Interview Agent**: Prepares behavioural and system design interactive mock loops.

- **Real-Time Tailored Resume Builder**:
  - Direct CTA triggers transition from target job search match to the Resume Builder.
  - Interactive **5-step live AI generation panel** with simulated progress stepper, live ATS score feedback (e.g. 82% to 96%), and log activity console stream.
  - One-click "Save Tailored Resume to Profile" and "Export PDF".

- **Monochrome & Minimalist Aesthetic**:
  - Curated oklch colors utilizing the signature indigo-slate `--ink` accent.
  - Clean typographic system combining the friendly, rounded **Comfortaa** font for UI body text with the script-like **Playwrite US Modern** font for headings, dashboard greetings, and brand wordmarks.
  - Animated `.draw-icon` hover action on outline SVG components.
  - Custom brand logo (Compass SVG mark) with interactive 360-degree needle rotation on hover.

- **Dynamic Background Line Tracing**:
  - Full-screen SVG canvas animation generating 52 custom linear-gradient lines sweeping diagonally from all 4 viewport edges.
  - Solid card containers (`bg-background` and `bg-card`) ensure line animations remain clean and restricted strictly to negative background space.

- **Centralized User Profile Context**:
  - Context Provider synchronizing target salary, preferences, bio, goals, activities, and resume items in `localStorage`.

---

## 🛠️ Technology Stack

- **Framework**: TanStack Start (SSR + Client React, built on Vite and Nitro)
- **Routing**: TanStack Router (fully type-safe, file-based routing)
- **State**: React Context API (`UserProfileContext` with localStorage backup)
- **Styling**: Tailwind CSS v4 + custom Vanilla CSS utilities
- **Fonts**: Self-hosted variable TTF fonts (Comfortaa & Playwrite US Modern)
- **Icons**: Lucide React wrapped in custom `OutlineIcon` components
- **Dialogs & Overlays**: Radix UI Primitives

---

## 📂 Directory Structure

```
career-compass-ui/
├── public/
│   ├── Comfortaa/                    # Self-hosted Comfortaa variable TTF font
│   │   └── Comfortaa-VariableFont_wght.ttf
│   ├── Playwrite_US_Modern/          # Self-hosted Playwrite US Modern variable TTF font
│   │   └── PlaywriteUSModern-VariableFont_wght.ttf
│   ├── favicon.ico
│   └── robots.txt
├── src/
│   ├── components/
│   │   ├── agents/
│   │   │   └── AgentBody.tsx         # UIs for all 7 pipeline agents
│   │   ├── ui/                       # Radix UI shadcn base primitives
│   │   ├── AnimatedLines.tsx         # Shared full-screen SVG drifting lines component
│   │   ├── AppShell.tsx              # Navigation header and viewport container
│   │   ├── Chatbot.tsx               # Floating AI chatbot widget
│   │   ├── LineButton.tsx            # Signature monochrome button
│   │   └── OutlineIcon.tsx           # Animate-on-hover SVG icon wrapper
│   ├── context/
│   │   └── UserProfileContext.tsx    # Context Provider managing credentials, logs, and skills
│   ├── lib/
│   │   ├── agents.ts                 # Local configuration for 7 agents
│   │   └── utils.ts                  # Tailwind class merge helper
│   ├── routes/
│   │   ├── __root.tsx                # Context provider wrapper and Toast container
│   │   ├── index.tsx                 # Entry Sign-In/Up page with line drifting
│   │   ├── setup.tsx                 # Onboarding setup wizard
│   │   ├── dashboard.tsx             # Pipeline grid overview
│   │   ├── agents.$agentId.tsx       # Main agent workspace route
│   │   └── profile.tsx               # 6-tab profile details hub
│   ├── routeTree.gen.ts              # Auto-generated route tree
│   ├── router.tsx                    # Router bootstrap configuration
│   ├── server.ts                     # SSR entrypoint
│   ├── start.ts                      # Client hydration entrypoint
│   └── styles.css                    # Design system tokens, @font-face rules, and utilities
├── package.json
├── tsconfig.json
└── vite.config.ts
```

---

## 🧭 Application Routes

| Route | File Path | Purpose |
|---|---|---|
| `/` | `src/routes/index.tsx` | Entry portal for authentication |
| `/setup` | `src/routes/setup.tsx` | Multi-step onboarding setup |
| `/dashboard` | `src/routes/dashboard.tsx` | Pipeline system board |
| `/agents/$agentId` | `src/routes/agents.$agentId.tsx` | Workspace layout for each agent |
| `/profile` | `src/routes/profile.tsx` | Profile information, goals, logs, and resumes |

---

## 🎨 Design System & Animation Specifications

- **Typography**:
  - Sans-Serif: `font-family: var(--font-sans)` (Comfortaa)
  - Display Script: `font-family: var(--font-display)` (Playwrite US Modern)
- **Keyframe Motions**:
  - `rise-in`: Entry translate animation (`cubic-bezier(0.65, 0, 0.35, 1)`).
  - `stroke-draw`: Inline path outline tracing for outline icons on hover.
  - `compass-spin`: Complete rotation of compass needles on logo mouse-over.
  - `animate-line`: SVG line sweep tracing using animated `stroke-dasharray` and opacity pulses.

---

## 🚀 Getting Started

To install dependencies and start the local development server:

```bash
# Install package dependencies
npm install

# Start Vite dev server
npm run dev

# Build production bundle (SSR client & server worker)
npm run build

# Preview build locally
npm run preview
```

---

> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting published git history (force pushing, rebasing, or amending commits) as it syncs back to Lovable and can disrupt project history. Keep the branch in a working state.
