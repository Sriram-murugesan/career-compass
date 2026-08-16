import { useState } from "react";
import {
  Building2,
  MapPin,
  Clock3,
  Bookmark,
  CircleAlert,
  CircleCheck,
  CircleDashed,
  Play,
} from "lucide-react";
import { OutlineIcon } from "@/components/OutlineIcon";
import { LineButton } from "@/components/LineButton";
import { cn } from "@/lib/utils";

function Panel({
  title,
  aside,
  children,
}: {
  title: string;
  aside?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-border p-6">
      <div className="flex items-baseline justify-between">
        <h2 className="text-sm font-medium">{title}</h2>
        {aside && <span className="text-xs text-muted-foreground">{aside}</span>}
      </div>
      <div className="mt-5">{children}</div>
    </section>
  );
}

function Gauge({ value }: { value: number }) {
  const r = 34;
  const c = 2 * Math.PI * r;
  return (
    <div className="flex items-center gap-5">
      <svg width="88" height="88" viewBox="0 0 88 88">
        <circle cx="44" cy="44" r={r} fill="none" stroke="currentColor" strokeWidth="1" className="text-border" />
        <circle
          cx="44"
          cy="44"
          r={r}
          fill="none"
          stroke="currentColor"
          strokeWidth="1.75"
          strokeLinecap="round"
          className="text-ink"
          strokeDasharray={c}
          strokeDashoffset={c}
          transform="rotate(-90 44 44)"
          style={{ animation: `path-draw 1200ms cubic-bezier(0.65,0,0.35,1) forwards` }}
        >
          <animate attributeName="stroke-dashoffset" from={c} to={c * (1 - value / 100)} dur="1.2s" fill="freeze" />
        </circle>
        <text x="44" y="48" textAnchor="middle" className="fill-foreground text-[15px]">
          {value}
        </text>
      </svg>
      <div>
        <p className="text-sm font-medium">ATS readability</p>
        <p className="mt-1 max-w-xs text-sm text-muted-foreground">
          Parsed cleanly by 9 of 10 tracking systems. Two long bullet lines reduce the score.
        </p>
      </div>
    </div>
  );
}

function Sparkline({ points }: { points: number[] }) {
  const max = Math.max(...points, 1);
  const d = points
    .map((p, i) => `${(i / (points.length - 1)) * 240},${40 - (p / max) * 34}`)
    .join(" L ");
  return (
    <svg viewBox="0 0 240 44" className="h-14 w-full">
      <path
        d={`M ${d}`}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeLinecap="round"
        className="path-draw text-ink"
      />
    </svg>
  );
}

const resume = () => (
  <div className="space-y-6">
    <Panel title="ATS indicator" aside="Recomputed 4m ago">
      <Gauge value={82} />
    </Panel>
    <Panel title="Resume preview" aside="v4 · draft">
      <article className="space-y-5 border-t border-border pt-5 text-sm leading-relaxed">
        <div>
          <h3 className="text-base font-medium">Ada Lovelace</h3>
          <p className="text-muted-foreground">Software Engineer · London · ada@domain.com</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Experience</p>
          <p className="mt-2 font-medium">Senior Engineer — Analytical Systems</p>
          <ul className="mt-2 list-none space-y-1.5 text-muted-foreground">
            <li>— Led migration of the reporting pipeline, cutting run time 43%.</li>
            <li>— Designed the type-safe contract layer used by four teams.</li>
          </ul>
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Skills</p>
          <p className="mt-2 text-muted-foreground">TypeScript · Python · SQL · System design</p>
        </div>
      </article>
      <div className="mt-6 flex gap-3">
        <LineButton>Regenerate</LineButton>
        <LineButton variant="solid">Export PDF</LineButton>
      </div>
    </Panel>
  </div>
);

const checks = [
  { label: "Contact block parsable", state: "pass", note: "Email and phone detected" },
  { label: "Reverse-chronological order", state: "pass", note: "Consistent across roles" },
  { label: "Bullet length", state: "warn", note: "Two bullets exceed 24 words" },
  { label: "Keyword coverage vs. target roles", state: "warn", note: "Missing: Kubernetes, Airflow" },
  { label: "No tables or text boxes", state: "pass", note: "Clean single-column layout" },
  { label: "Quantified impact", state: "fail", note: "3 bullets have no measurable outcome" },
] as const;

const validation = () => (
  <Panel title="Validation results" aside="6 checks">
    <ul className="divide-y divide-border">
      {checks.map((c) => (
        <li key={c.label} className="group flex items-start gap-4 py-4">
          <OutlineIcon
            icon={c.state === "pass" ? CircleCheck : c.state === "warn" ? CircleDashed : CircleAlert}
            size={18}
            className="mt-0.5 text-muted-foreground"
          />
          <div className="flex-1">
            <p className="text-sm">{c.label}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{c.note}</p>
          </div>
          <span
            className={cn(
              "mt-2 h-px w-8",
              c.state === "pass" ? "bg-border" : c.state === "warn" ? "bg-border-strong" : "bg-ink",
            )}
          />
        </li>
      ))}
    </ul>
  </Panel>
);

const jobs = [
  { role: "Senior Frontend Engineer", co: "Kepler Systems", loc: "London · Hybrid", type: "Full-time", match: "94% match" },
  { role: "Platform Engineer", co: "Northwind Labs", loc: "Remote (EU)", type: "Full-time", match: "88% match" },
  { role: "Product Engineer", co: "Ostara", loc: "Berlin", type: "Contract", match: "81% match" },
];

function JobSearch() {
  const [saved, setSaved] = useState<string[]>([]);
  return (
    <Panel title="Matches" aside="Refreshed hourly">
      <ul className="space-y-3">
        {jobs.map((j) => (
          <li
            key={j.role}
            className="group rounded-md border border-border p-5 transition-colors duration-300 hover:border-ink"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="text-sm font-medium">{j.role}</h3>
                <div className="mt-2 flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
                  <span className="inline-flex items-center gap-1.5">
                    <Building2 size={14} strokeWidth={1.5} /> {j.co}
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <MapPin size={14} strokeWidth={1.5} /> {j.loc}
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <Clock3 size={14} strokeWidth={1.5} /> {j.type}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-xs tabular-nums text-muted-foreground">{j.match}</span>
                <button
                  aria-label="Save role"
                  onClick={() =>
                    setSaved((s) => (s.includes(j.role) ? s.filter((x) => x !== j.role) : [...s, j.role]))
                  }
                  className={cn(
                    "transition-colors duration-300",
                    saved.includes(j.role) ? "text-ink" : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  <Bookmark
                    size={17}
                    strokeWidth={1.5}
                    fill={saved.includes(j.role) ? "currentColor" : "none"}
                  />
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

const productivity = () => (
  <div className="space-y-6">
    <Panel title="Weekly activity" aside="Applications sent">
      <Sparkline points={[2, 4, 3, 6, 5, 8, 7, 9, 6, 11]} />
      <div className="mt-2 flex justify-between text-xs text-muted-foreground">
        <span>10 weeks ago</span>
        <span>This week</span>
      </div>
    </Panel>
    <Panel title="Streak" aside="9 days">
      <div className="flex flex-wrap gap-2">
        {Array.from({ length: 21 }).map((_, i) => (
          <span
            key={i}
            className={cn(
              "h-5 w-5 rounded-full border",
              i > 11 ? "border-ink" : i > 5 ? "border-border-strong" : "border-border",
            )}
          />
        ))}
      </div>
    </Panel>
  </div>
);

const milestones = [
  { title: "Sharpen system design", when: "Weeks 1–3", note: "Two design reviews per week." },
  { title: "Ship a public project", when: "Weeks 4–7", note: "Something infra-flavoured and small." },
  { title: "Targeted applications", when: "Weeks 8–10", note: "Twelve roles, all senior scope." },
  { title: "Interview loops", when: "Weeks 11–14", note: "Expect three onsite processes." },
];

const roadmap = () => (
  <Panel title="Your path" aside="14 weeks">
    <div className="relative pl-8">
      <svg className="absolute left-0 top-1 h-full w-8" preserveAspectRatio="none" viewBox="0 0 32 400">
        <path
          d="M 16 0 L 16 400"
          fill="none"
          stroke="currentColor"
          strokeWidth="1"
          className="path-draw text-border-strong"
        />
      </svg>
      <ol className="space-y-9">
        {milestones.map((m, i) => (
          <li key={m.title} className="relative">
            <span className="absolute -left-8 top-1 flex h-4 w-4 -translate-x-1/2 items-center justify-center rounded-full border border-ink bg-background" />
            <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">{m.when}</p>
            <h3 className="mt-1.5 text-sm font-medium">
              {String(i + 1).padStart(2, "0")} · {m.title}
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">{m.note}</p>
          </li>
        ))}
      </ol>
    </div>
  </Panel>
);

const advice = [
  { t: "Lean into infrastructure", b: "Your strongest signals are pipelines and type systems — most postings you saved reward that." },
  { t: "Don't chase the title yet", b: "Two of the three loops you're likely to pass down-level on scope, not skill. Frame impact in numbers." },
  { t: "Fix quantification first", b: "The validation agent found three unmeasured bullets. That is the cheapest score you'll gain this week." },
  { t: "Talk to two people", b: "Referrals moved 40% of comparable candidates past screening." },
];

const advisor = () => (
  <div className="grid gap-4 sm:grid-cols-2">
    {advice.map((a) => (
      <article
        key={a.t}
        className="group rounded-lg border border-border p-5 transition-colors duration-300 hover:border-ink"
      >
        <h3 className="text-sm font-medium">{a.t}</h3>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{a.b}</p>
      </article>
    ))}
  </div>
);

const questions = [
  "Walk me through a system you designed end to end.",
  "Describe a time you disagreed with a technical decision.",
  "How would you cut p95 latency on a read-heavy API?",
  "What trade-offs did your last migration force?",
  "How do you decide what not to build?",
];

const interview = () => (
  <div className="space-y-6">
    <Panel title="Progress" aside="12 of 30 answered">
      <div className="h-px w-full bg-border">
        <div className="h-px bg-ink" style={{ width: "40%" }} />
      </div>
    </Panel>
    <Panel title="Practice set" aside="Behavioural + system design">
      <ul className="divide-y divide-border">
        {questions.map((q, i) => (
          <li key={q} className="group flex items-center gap-4 py-4">
            <span className="text-xs tabular-nums text-muted-foreground">
              {String(i + 1).padStart(2, "0")}
            </span>
            <p className="flex-1 text-sm">{q}</p>
            <OutlineIcon icon={Play} size={16} className="text-muted-foreground" />
          </li>
        ))}
      </ul>
      <div className="mt-6">
        <LineButton variant="solid">Start mock interview</LineButton>
      </div>
    </Panel>
  </div>
);

export function AgentBody({ id }: { id: string }) {
  switch (id) {
    case "resume":
      return resume();
    case "validation":
      return validation();
    case "job-search":
      return <JobSearch />;
    case "productivity":
      return productivity();
    case "roadmap":
      return roadmap();
    case "advisor":
      return advisor();
    case "interview":
      return interview();
    default:
      return null;
  }
}
