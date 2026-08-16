# Career Compass UI

UI Development Brief — "Career Compass"

1. Project Summary

Career Compass is an AI multi-agent career platform. A user sets up a profile (skills, interests, goals), and a chain of specialized AI agents takes over — building their resume, validating it, searching jobs, tracking productivity, generating a roadmap, giving career advice, and prepping them for interviews. A chatbot sits alongside the whole experience as a persistent assistant.

Your job is not to design a generic SaaS dashboard. Every screen and component should map directly to a step in the workflow below. Treat the workflow diagram as the literal information architecture of the app.

2. Design Philosophy — Read This Before Building Anything

Minimal. Linear. Quiet. Confident.

No large solid color fills. No colored card backgrounds, no gradient hero blocks, no colored buttons-as-blocks. Surfaces stay neutral (white / near-white / very light gray, or near-black in dark mode).

Color is used as an accent only — thin lines, small dots, a single highlight stroke, subtle status indicators. Think "ink on paper," not "poster."

Icons are outlined/stroked, never filled. Use a consistent stroke-based icon set (e.g., Lucide, Phosphor (outline weight), Feather, or Tabler Icons — outline variant only). Uniform stroke width across the entire app (recommend 1.5px–1.75px).

Motion is the personality of this app. Since color is restrained, hover states carry the visual delight:

On hover, an icon's outline should animate as if being drawn/redrawn — think SVG stroke-dashoffset path animation, or the outline subtly "traveling" around the icon's border like a pulse moving along a wire.

Movement should feel precise and engineered, not bouncy or playful. Use cubic-bezier(0.65, 0, 0.35, 1) or similar — no default ease, no elastic/spring bounce.

Duration: 250–400ms for hover transitions. Never instant, never sluggish.

Optional secondary hover cue: icon lifts 1–2px with a very faint shadow, paired with the stroke animation — not instead of it.

Typography carries hierarchy, not color or boxes. Use weight and size contrast (e.g., a geometric sans like Inter, Söhne, or General Sans) instead of colored labels/badges.

Whitespace is a feature. Err on the side of more breathing room, not less.

Borders over fills. Cards/containers use 1px hairline borders (light gray / low-opacity), not shadows-as-default or filled backgrounds. Shadows, if any, should be extremely soft and used sparingly (e.g., only on active/focused elements).

One-line brief for the developer: "If you removed all icons and interaction, the screen should look almost like a well-typeset document. Color and motion only ever appear as a reward for interaction — never as decoration."

3. Application Architecture (from the Workflow Diagram)

This is the literal user journey — build the IA around this, in this order:

1. USER (auth / entry point)
        ↓
2. PROFILE SETUP
   → Skills · Interests · Goals input flow
        ↓
3. AI MULTI-AGENT SYSTEM (core app — likely a dashboard with 7 agent modules)
   a. Resume Agent            → generates ATS-friendly resume
   b. Validation Agent        → validates/reviews the resume
   c. Job Search Agent        → surfaces matching job listings
   d. Productivity Tracker Agent → tracks user activity/progress
   e. Personalized Roadmap Agent → generates a custom career roadmap
   f. Career Advisor Agent    → gives career guidance/recommendations
   g. Interview Preparation Agent → mock interviews / prep material
        ↓
4. CHATBOT (persistent, accessible from anywhere — likely a floating/docked assistant)


Note the diagram shows two agent rows connected by a routing arrow (Productivity Tracker → down → Personalized Roadmap), and the last row (Roadmap → Career Advisor → Interview Prep) splits into the Chatbot at the bottom. Interpretation for UI purposes:

Agents a–d form the "setup & foundation" phase (resume + validation + job matching + tracking).

Agents e–g form the "growth & readiness" phase (roadmap + advice + interview readiness).

The Chatbot is the connective tissue across both — it should feel reachable from every screen, not buried in one agent's view.

4. Screen-by-Screen Requirements

4.1 Entry / Auth (User)

Minimal sign-in/sign-up. Outlined user icon, single accent line under the active input.

No colored buttons — use a bordered button with an animated outline on hover (this is the first place the user should feel the "signature" hover interaction).

4.2 Profile Setup

A short, linear, multi-step flow (not a long single form) for Skills, Interests, Goals.

Consider a horizontal stepper at the top using thin lines connecting outlined step icons — the "current step" icon gets the animated outline treatment; completed steps get a subtle static checkmark (outlined, not filled).

Tag/chip inputs for skills should be outlined pills, not filled colored pills.

4.3 AI Multi-Agent System — Home/Dashboard

This is the core screen. Recommend a node-map or card-grid layout that visually echoes the workflow diagram itself — users should recognize the same 7-agent structure they'd see in documentation.

Each of the 7 agents = one card/module:

Outlined icon (unique per agent, but same stroke weight/style)

Agent name + one-line status ("Resume ready", "3 new matches", "Roadmap updated 2d ago")

On hover: icon outline animates; card border brightens slightly (still no fill)

Maintain the visual grouping from the diagram: Resume → Validation → Job Search → Productivity Tracker as one row/cluster, then Roadmap → Career Advisor → Interview Prep as the next.

A thin connecting line (like the diagram's arrows) between related agents is a nice subtle touch for showing flow/sequence — optional but on-brand.

4.4 Individual Agent Views

Each agent gets its own focused screen, reached by clicking its dashboard card:

Resume Agent: resume preview/editor, ATS-friendliness indicator (use an outlined gauge/meter, not a colored bar).

Validation Agent: checklist-style validation results — outlined check/warning/error icons, no red/green fills; use icon shape difference + a thin accent line for status, not solid color blocks.

Job Search Agent: job listing cards, minimal, outlined company/location/type icons, save/bookmark as an outline icon that animates/fills subtly only on click (not hover).

Productivity Tracker Agent: simple line-based charts/sparklines (no filled bar charts), streak indicators as outlined dots/rings.

Personalized Roadmap Agent: a timeline/path UI — this is a great place to reuse the "animated line drawing" motif at a larger scale (the roadmap path itself could draw in on load).

Career Advisor Agent: conversational or card-based recommendations, same outline treatment.

Interview Preparation Agent: practice question list / mock interview flow, minimal progress indicator.

4.5 Chatbot

Persistent, accessible via a small outlined chat-bubble icon fixed in a corner across all screens (not just the dashboard).

Expands into a lightweight panel/drawer — no heavy modal, no colored header bar.

Message bubbles: outlined for the bot, a subtle hairline-bordered variant for the user — avoid filled colored chat bubbles entirely.

5. Component & Style System

Element Guidance Color palette Neutral base (white/near-white or near-black dark mode) + one accent color used sparingly (e.g., a single ink-blue or graphite) for hover states, active indicators, and links only Icons Outline-only icon set, consistent stroke width, no icon fills — ever Buttons Bordered/ghost style by default; animated outline on hover; avoid solid-fill primary buttons — if a strong CTA is needed, use a subtle inverted (near-black/near-white) fill, not a bright color fill Cards 1px hairline border, transparent/neutral background, no drop shadow at rest Typography One geometric/humanist sans-serif family; hierarchy via weight + size, not color Charts Line/stroke-based (sparklines, line charts, radial outline gauges) — never solid filled bar/pie charts Hover motion SVG stroke-dashoffset "draw" animation on icons, 250–400ms, engineered easing (no bounce) Spacing Generous, consistent spacing scale (e.g., 4/8/12/16/24/32/48px)

6. Suggested Tech Notes (adjust to your stack)

Icons: Lucide or Tabler Icons (outline), rendered as inline SVG so stroke-dashoffset hover animation is achievable per-icon.

Animation: Framer Motion (React) or GSAP for the stroke-draw hover effect; CSS-only fallback via stroke-dasharray/stroke-dashoffset + :hover transition is acceptable for simpler icons.

Keep dark mode in mind from the start — the "outline-only, minimal fill" language should translate cleanly to a dark theme (near-black background, near-white strokes).

7. What Success Looks Like

A user should be able to look at the dashboard and immediately recognize the same 7-step agent pipeline from the internal workflow diagram — Resume → Validation → Job Search → Productivity Tracker → Roadmap → Career Advisor → Interview Prep — with the Chatbot always one click away. The interface should feel calm and editorial at rest, and only "come alive" through precise, professional line-drawing animations when the user interacts with it.

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/bc638eb0-e8e5-48ac-941d-58146ce1798b).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
