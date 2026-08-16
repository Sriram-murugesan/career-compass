import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, useEffect, useRef } from "react";
import { LineButton } from "@/components/LineButton";
import { useUserProfile } from "@/context/UserProfileContext";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Career Compass — AI multi-agent career platform" },
      {
        name: "description",
        content:
          "Sign in to Career Compass: seven AI agents that build your resume, validate it, find jobs, and prepare you for interviews.",
      },
      { property: "og:title", content: "Career Compass — AI multi-agent career platform" },
      {
        property: "og:description",
        content: "Seven specialized AI agents guiding your career from resume to offer.",
      },
    ],
  }),
  component: Entry,
});

/* ── Compass SVG Logo ── */
function CompassLogo({ size = 44 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 44 44"
      fill="none"
      aria-label="Career Compass logo"
      className="compass-logo"
    >
      <circle cx="22" cy="22" r="20" stroke="currentColor" strokeWidth="1" className="text-foreground" />
      <circle cx="22" cy="22" r="14" stroke="currentColor" strokeWidth="0.5" strokeDasharray="3 3" className="text-muted-foreground" />
      <line x1="22" y1="2"  x2="22" y2="7"  stroke="currentColor" strokeWidth="1.5" className="text-foreground" />
      <line x1="22" y1="37" x2="22" y2="42" stroke="currentColor" strokeWidth="1.5" className="text-foreground" />
      <line x1="2"  y1="22" x2="7"  y2="22" stroke="currentColor" strokeWidth="1.5" className="text-foreground" />
      <line x1="37" y1="22" x2="42" y2="22" stroke="currentColor" strokeWidth="1.5" className="text-foreground" />
      <line x1="8.64"  y1="8.64"  x2="11.46" y2="11.46" stroke="currentColor" strokeWidth="0.75" className="text-muted-foreground" />
      <line x1="35.36" y1="35.36" x2="32.54" y2="32.54" stroke="currentColor" strokeWidth="0.75" className="text-muted-foreground" />
      <line x1="35.36" y1="8.64"  x2="32.54" y2="11.46" stroke="currentColor" strokeWidth="0.75" className="text-muted-foreground" />
      <line x1="8.64"  y1="35.36" x2="11.46" y2="32.54" stroke="currentColor" strokeWidth="0.75" className="text-muted-foreground" />
      <circle cx="22" cy="22" r="1.5" fill="currentColor" className="text-ink" />
      <polygon points="22,8 20.2,22 22,20 23.8,22" fill="currentColor" className="compass-needle text-ink" />
      <polygon points="22,36 20.2,22 22,24 23.8,22" fill="currentColor" className="compass-needle text-muted-foreground" style={{ opacity: 0.45 }} />
    </svg>
  );
}

/* ── Full-viewport SVG animated lines ── */
type SvgLine = {
  id: number;
  x1: number; y1: number;
  x2: number; y2: number;
  dur: number;  // seconds
  delay: number; // seconds
  strokeW: number;
  opacity: number;
};

/** Seed a pseudo-random sequence so SSR & client produce the same values */
function seededRand(seed: number) {
  let s = seed;
  return () => {
    s = (s * 1664525 + 1013904223) & 0xffffffff;
    return (s >>> 0) / 0xffffffff;
  };
}

function buildLines(W: number, H: number): SvgLine[] {
  const rand = seededRand(0xdeadbeef);
  const lines: SvgLine[] = [];

  // Choose a spawn-edge for each line: 0=top, 1=right, 2=bottom, 3=left
  const count = 52;
  for (let i = 0; i < count; i++) {
    const edge = i % 4;          // evenly cycle through all four edges
    const lengthFactor = 0.45 + rand() * 0.55; // 45%–100% of viewport dimension
    const angleOffset = (rand() - 0.5) * 60;   // ±30° extra skew

    let x1: number, y1: number, x2: number, y2: number;

    if (edge === 0) {
      // Spawn on top edge, travel toward bottom
      x1 = rand() * W;
      y1 = -20;
      const len = H * lengthFactor;
      const angle = (90 + angleOffset) * (Math.PI / 180);
      x2 = x1 + Math.cos(angle) * len;
      y2 = y1 + Math.sin(angle) * len;
    } else if (edge === 1) {
      // Spawn on right edge, travel toward left
      x1 = W + 20;
      y1 = rand() * H;
      const len = W * lengthFactor;
      const angle = (180 + angleOffset) * (Math.PI / 180);
      x2 = x1 + Math.cos(angle) * len;
      y2 = y1 + Math.sin(angle) * len;
    } else if (edge === 2) {
      // Spawn on bottom edge, travel toward top
      x1 = rand() * W;
      y1 = H + 20;
      const len = H * lengthFactor;
      const angle = (-90 + angleOffset) * (Math.PI / 180);
      x2 = x1 + Math.cos(angle) * len;
      y2 = y1 + Math.sin(angle) * len;
    } else {
      // Spawn on left edge, travel toward right
      x1 = -20;
      y1 = rand() * H;
      const len = W * lengthFactor;
      const angle = (0 + angleOffset) * (Math.PI / 180);
      x2 = x1 + Math.cos(angle) * len;
      y2 = y1 + Math.sin(angle) * len;
    }

    lines.push({
      id: i,
      x1, y1, x2, y2,
      dur: 6 + rand() * 12,       // 6–18 s
      delay: -(rand() * 18),       // negative = start mid-animation for instant coverage
      strokeW: 0.4 + rand() * 0.8,
      opacity: 0.12 + rand() * 0.22,
    });
  }
  return lines;
}

function AnimatedLines() {
  const ref = useRef<SVGSVGElement>(null);
  const [lines, setLines] = useState<SvgLine[]>([]);
  const [dim, setDim] = useState({ w: 1440, h: 900 });

  useEffect(() => {
    const measure = () => {
      setDim({ w: window.innerWidth, h: window.innerHeight });
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);

  useEffect(() => {
    setLines(buildLines(dim.w, dim.h));
  }, [dim.w, dim.h]);

  return (
    <svg
      ref={ref}
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 h-full w-full"
      viewBox={`0 0 ${dim.w} ${dim.h}`}
      preserveAspectRatio="xMidYMid slice"
    >
      <defs>
        {lines.map((l) => {
          const len = Math.hypot(l.x2 - l.x1, l.y2 - l.y1);
          return (
            <linearGradient
              key={`g${l.id}`}
              id={`lg${l.id}`}
              gradientUnits="userSpaceOnUse"
              x1={l.x1} y1={l.y1}
              x2={l.x2} y2={l.y2}
            >
              <stop offset="0%"   stopColor="var(--ink)" stopOpacity="0" />
              <stop offset="30%"  stopColor="var(--ink)" stopOpacity={l.opacity} />
              <stop offset="70%"  stopColor="var(--ink)" stopOpacity={l.opacity} />
              <stop offset="100%" stopColor="var(--ink)" stopOpacity="0" />
            </linearGradient>
          );
        })}
      </defs>

      {lines.map((l) => {
        const len = Math.hypot(l.x2 - l.x1, l.y2 - l.y1);
        return (
          <line
            key={l.id}
            x1={l.x1} y1={l.y1}
            x2={l.x2} y2={l.y2}
            stroke={`url(#lg${l.id})`}
            strokeWidth={l.strokeW}
            strokeLinecap="round"
          >
            {/* Animate stroke-dashoffset for a "sweeping trace" effect */}
            <animate
              attributeName="stroke-dasharray"
              from={`0 ${len}`}
              to={`${len} 0`}
              dur={`${l.dur}s`}
              begin={`${l.delay}s`}
              repeatCount="indefinite"
              calcMode="linear"
            />
            {/* Fade the line in and out in sync */}
            <animate
              attributeName="opacity"
              values="0;1;1;0"
              keyTimes="0;0.12;0.88;1"
              dur={`${l.dur}s`}
              begin={`${l.delay}s`}
              repeatCount="indefinite"
            />
          </line>
        );
      })}
    </svg>
  );
}

/* ── Form Field ── */
function Field({
  id,
  label,
  type = "text",
  placeholder,
  value,
  onChange,
}: {
  id: string;
  label: string;
  type?: string;
  placeholder?: string;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
}) {
  return (
    <label className="group block" htmlFor={id}>
      <span className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{label}</span>
      <input
        id={id}
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        className="mt-2 w-full border-b border-border bg-transparent pb-2.5 text-sm outline-none placeholder:text-muted-foreground/40 focus:border-ink"
        style={{ transition: "border-color 300ms cubic-bezier(0.65,0,0.35,1)" }}
      />
    </label>
  );
}

/* ── Entry Page ── */
function Entry() {
  const [mode, setMode] = useState<"in" | "up">("in");
  const { profile, updateProfile } = useUserProfile();
  const [name, setName] = useState(profile.name || "");
  const [email, setEmail] = useState(profile.email || "");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateProfile({
      name: name.trim() || (mode === "up" ? "Ada Lovelace" : profile.name),
      email: email.trim() || profile.email,
    });
    navigate({ to: mode === "up" ? "/setup" : "/dashboard" });
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-6">

      {/* Full-screen SVG animated line field */}
      <AnimatedLines />

      {/* Deep radial vignette — darkens corners, keeps centre clear for form */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0"
        style={{
          background: [
            "radial-gradient(ellipse 55% 55% at 50% 50%, transparent 0%, color-mix(in oklab, var(--background) 72%, transparent) 100%)",
          ].join(", "),
        }}
      />

      {/* Form card — NO border, pure backdrop blur */}
      <div className="rise-in relative z-10 w-full max-w-sm">
        <div
          className="rounded-2xl p-8 shadow-xs bg-background border border-border/10"
        >
          {/* Logo */}
          <div className="mb-9 flex flex-col items-center gap-4 text-center">
            <CompassLogo size={52} />
            <div>
              <h1
                className="text-2xl md:text-3xl font-semibold tracking-tight brand-animate brand-interactive"
                style={{ fontFamily: "var(--font-display)" }}
              >
                Career Compass
              </h1>
              <p className="mt-2 text-xs text-muted-foreground">
                Seven agents. One deliberate career path.
              </p>
            </div>
          </div>

          {/* Mode toggle tabs */}
          <div className="mb-7 flex gap-6 border-b border-border pb-1 text-sm">
            {(["in", "up"] as const).map((m) => (
              <button
                key={m}
                id={m === "in" ? "tab-sign-in" : "tab-create-account"}
                onClick={() => setMode(m)}
                className={
                  "relative pb-2.5 font-medium transition-colors duration-300 " +
                  (mode === m ? "text-foreground" : "text-muted-foreground hover:text-ink")
                }
              >
                {m === "in" ? "Sign in" : "Create account"}
                <span
                  className={
                    "absolute inset-x-0 bottom-0 h-px origin-left bg-ink transition-transform duration-[320ms] [transition-timing-function:cubic-bezier(0.65,0,0.35,1)] " +
                    (mode === m ? "scale-x-100" : "scale-x-0")
                  }
                />
              </button>
            ))}
          </div>

          {/* Form */}
          <form className="space-y-6" onSubmit={handleSubmit}>
            {mode === "up" && (
              <Field
                id="field-name"
                label="Full name"
                placeholder="Ada Lovelace"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            )}
            <Field
              id="field-email"
              label="Email"
              type="email"
              placeholder="you@domain.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <Field
              id="field-password"
              label="Password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <LineButton id="btn-submit" type="submit" className="mt-2 w-full">
              {mode === "in" ? "Continue" : "Start profile setup →"}
            </LineButton>
          </form>

          <p className="mt-6 text-center text-xs text-muted-foreground">
            Skip to{" "}
            <Link
              to="/dashboard"
              id="link-skip-dashboard"
              className="text-ink underline underline-offset-4 transition-opacity hover:opacity-70"
            >
              agent dashboard
            </Link>
            .
          </p>
        </div>

        {/* Tagline below card */}
        <p
          className="mt-6 text-center text-xs text-muted-foreground"
          style={{ fontFamily: "var(--font-display)", letterSpacing: "0.04em" }}
        >
          Seven AI Agents · One Career Path
        </p>
      </div>
    </div>
  );
}
