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
  Sparkles,
  FileText,
  Loader2,
  CheckCircle2,
  Bot,
  Download,
} from "lucide-react";
import { OutlineIcon } from "@/components/OutlineIcon";
import { LineButton } from "@/components/LineButton";
import { cn } from "@/lib/utils";
import { useUserProfile } from "@/context/UserProfileContext";
import { toast } from "sonner";
import { useNavigate } from "@tanstack/react-router";

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
    <section className="rounded-lg border border-border bg-background p-6">
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
          strokeDashoffset={c * (1 - value / 100)}
          transform="rotate(-90 44 44)"
          style={{ transition: "stroke-dashoffset 800ms cubic-bezier(0.65,0,0.35,1)" }}
        />
        <text x="44" y="48" textAnchor="middle" className="fill-foreground text-[15px] font-medium">
          {value}%
        </text>
      </svg>
      <div>
        <p className="text-sm font-medium">ATS Readability &amp; Keyword Match</p>
        <p className="mt-1 max-w-xs text-xs text-muted-foreground leading-relaxed">
          {value >= 90
            ? "Recognized cleanly by 10 of 10 automated tracking systems."
            : "Parsed cleanly by 8 of 10 systems. Tailor experience bullets to optimize match."}
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

// ----------------------------------------------------
// JOB SEARCH AGENT COMPONENT
// ----------------------------------------------------
const jobsList = [
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

function JobSearchAgent() {
  const { logActivity } = useUserProfile();
  const [saved, setSaved] = useState<string[]>([]);
  const navigate = useNavigate();

  const handleTailorResume = (job: (typeof jobsList)[0]) => {
    logActivity({
      type: "job_searched",
      title: `Selected role: ${job.role} at ${job.co}`,
      details: `Match score ${job.match}%. Initiating tailored resume generation.`,
      targetCompany: job.co,
    });

    toast.info(`Selected ${job.co}! Transferring specs to Resume Agent...`);

    navigate({
      to: "/agents/$agentId",
      params: { agentId: "resume" },
      search: { jobRole: job.role, company: job.co, loc: job.loc } as any,
    });
  };

  return (
    <div className="space-y-6">
      <Panel title="AI Matched Target Roles" aside="Surfaced from profile context">
        <ul className="space-y-4">
          {jobsList.map((j) => (
            <li
              key={j.id}
              className="group rounded-lg border border-border p-5 transition-colors duration-300 hover:border-ink"
            >
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div className="flex items-center gap-3">
                    <h3 className="text-sm font-medium">{j.role}</h3>
                    <span className="text-xs tabular-nums text-muted-foreground">{j.match}% match</span>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
                    <span className="inline-flex items-center gap-1.5 font-medium text-foreground">
                      <Building2 size={14} strokeWidth={1.5} /> {j.co}
                    </span>
                    <span className="inline-flex items-center gap-1.5">
                      <MapPin size={14} strokeWidth={1.5} /> {j.loc}
                    </span>
                    <span className="inline-flex items-center gap-1.5">
                      <Clock3 size={14} strokeWidth={1.5} /> {j.type}
                    </span>
                  </div>
                  <p className="mt-3 text-xs text-muted-foreground max-w-2xl leading-relaxed">
                    {j.desc}
                  </p>

                  <div className="mt-3 flex flex-wrap gap-2">
                    {j.keywords.map((kw) => (
                      <span
                        key={kw}
                        className="rounded-full border border-border px-2.5 py-0.5 text-[11px] text-muted-foreground"
                      >
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="flex flex-row sm:flex-col items-center sm:items-end gap-3 self-end sm:self-start">
                  <LineButton
                    variant="solid"
                    onClick={() => handleTailorResume(j)}
                    className="gap-2 text-xs py-1.5"
                  >
                    <OutlineIcon icon={Sparkles} size={14} /> Tailor Resume
                  </LineButton>

                  <button
                    aria-label="Save role"
                    onClick={() =>
                      setSaved((s) => (s.includes(j.id) ? s.filter((x) => x !== j.id) : [...s, j.id]))
                    }
                    className={cn(
                      "flex items-center gap-1 text-xs transition-colors duration-300",
                      saved.includes(j.id) ? "text-ink" : "text-muted-foreground hover:text-foreground"
                    )}
                  >
                    <Bookmark
                      size={16}
                      strokeWidth={1.5}
                      fill={saved.includes(j.id) ? "currentColor" : "none"}
                    />
                    <span>{saved.includes(j.id) ? "Saved" : "Save"}</span>
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}

// ----------------------------------------------------
// RESUME BUILDER AGENT COMPONENT (WITH REAL-TIME SIDE PANEL)
// ----------------------------------------------------
function ResumeBuilderAgent() {
  const { profile, saveTailoredResume } = useUserProfile();
  const [selectedJob, setSelectedJob] = useState(jobsList[0]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStep, setGenerationStep] = useState<number>(0);
  const [currentScore, setCurrentScore] = useState<number>(82);
  const [logs, setLogs] = useState<string[]>([]);
  const [tailoredVersion, setTailoredVersion] = useState<number>(1);

  const stepsList = [
    { title: "Analyzing Target Job Specs", desc: `Extracting keywords for ${selectedJob.role} at ${selectedJob.co}` },
    { title: "Matching Profile Skills", desc: `Aligning ${profile.skills.length} verified profile skills with ATS criteria` },
    { title: "Writing Executive Summary", desc: "Generating high-impact lead bio with quantitative highlights" },
    { title: "Quantifying Bullet Impact", desc: "Enhancing experience metrics with performance outcomes" },
    { title: "ATS Optimization & Formatting", desc: "Formatting single-column layout for 95%+ parser readiness" },
  ];

  const handleStartGeneration = () => {
    setIsGenerating(true);
    setGenerationStep(1);
    setCurrentScore(82);
    setLogs([`[AI Engine] Initializing Resume Builder agent for ${selectedJob.co}...`]);

    const timer1 = setTimeout(() => {
      setGenerationStep(2);
      setCurrentScore(86);
      setLogs((prev) => [
        ...prev,
        `[Keyword Extraction] Target keywords: ${selectedJob.keywords.join(", ")}`,
        `[Profile Match] Matched ${profile.skills.slice(0, 4).map((s) => s.name).join(", ")}.`,
      ]);
    }, 1200);

    const timer2 = setTimeout(() => {
      setGenerationStep(3);
      setCurrentScore(91);
      setLogs((prev) => [
        ...prev,
        `[Summary Writer] Tailored summary drafted for ${profile.name}.`,
      ]);
    }, 2400);

    const timer3 = setTimeout(() => {
      setGenerationStep(4);
      setCurrentScore(94);
      setLogs((prev) => [
        ...prev,
        `[Impact Metrics] Quantified outcomes across roles (+43% latency reduction).`,
      ]);
    }, 3600);

    const timer4 = setTimeout(() => {
      setGenerationStep(5);
      setCurrentScore(selectedJob.match);
      setIsGenerating(false);
      setTailoredVersion((v) => v + 1);
      setLogs((prev) => [
        ...prev,
        `[ATS Check] Verification complete! ATS Match Score: ${selectedJob.match}%.`,
      ]);
      toast.success(`Tailored resume generated for ${selectedJob.co}!`);
    }, 4800);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      clearTimeout(timer4);
    };
  };

  const handleSaveToProfile = () => {
    saveTailoredResume({
      jobTitle: selectedJob.role,
      company: selectedJob.co,
      location: selectedJob.loc,
      atsScore: selectedJob.match,
      matchedKeywords: selectedJob.keywords,
      summary: `Tailored Senior Software Engineer resume for ${selectedJob.co}. Highlighted ${selectedJob.keywords.slice(0, 3).join(", ")}.`,
      bullets: [
        `Architected high-scale frontend systems for ${selectedJob.co} target domains, reducing p95 render latency by 43%.`,
        `Engineered type-safe contracts with React & TypeScript, boosting release velocity across 4 teams.`,
        `Integrated automated ATS keyword validation checks, achieving ${selectedJob.match}% match compliance.`,
      ],
    });

    toast.success(`Saved tailored resume for ${selectedJob.co} to Profile!`);
  };

  return (
    <div className="space-y-6">
      {/* Target Job Selection Header */}
      <Panel title="Select Target Job Spec" aside="Generates custom ATS resume">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex-1 w-full">
            <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Target Role</span>
            <select
              value={selectedJob.id}
              onChange={(e) => {
                const found = jobsList.find((j) => j.id === e.target.value);
                if (found) setSelectedJob(found);
              }}
              className="mt-2 w-full border-b border-border bg-transparent pb-2 text-sm outline-none focus:border-ink"
            >
              {jobsList.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.role} — {j.co} ({j.match}% match)
                </option>
              ))}
            </select>
          </div>

          <LineButton
            variant="solid"
            onClick={handleStartGeneration}
            disabled={isGenerating}
            className="w-full sm:w-auto gap-2 self-end py-2 text-xs"
          >
            {isGenerating ? (
              <>
                <Loader2 size={14} className="animate-spin" /> Tailoring...
              </>
            ) : (
              <>
                <OutlineIcon icon={Sparkles} size={14} /> Generate Tailored Resume
              </>
            )}
          </LineButton>
        </div>
      </Panel>

      {/* Main Grid: Live Side Panel + Resume Output */}
      <div className="grid gap-6 lg:grid-cols-12">
        {/* LEFT / REAL-TIME BUILDING SIDE PANEL (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          <Panel title="Real-Time AI Building Panel" aside={isGenerating ? "Building live..." : "Ready"}>
            <div className="border-b border-border pb-5">
              <Gauge value={currentScore} />
            </div>

            <div className="mt-5 space-y-4">
              <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Generation Pipeline</span>
              <div className="space-y-3">
                {stepsList.map((step, idx) => {
                  const stepNum = idx + 1;
                  const isDone = generationStep > stepNum || (!isGenerating && generationStep === 5);
                  const isCurrent = isGenerating && generationStep === stepNum;
                  return (
                    <div
                      key={step.title}
                      className={cn(
                        "flex items-start gap-3 rounded-md p-2.5 transition-colors duration-300 text-xs border border-border",
                        isCurrent ? "border-ink" : "bg-transparent"
                      )}
                    >
                      <span className="mt-0.5">
                        {isDone ? (
                          <OutlineIcon icon={CheckCircle2} size={15} className="text-foreground" />
                        ) : isCurrent ? (
                          <Loader2 size={15} className="animate-spin text-ink" />
                        ) : (
                          <CircleDashed size={15} className="text-muted-foreground" />
                        )}
                      </span>
                      <div>
                        <p className="font-medium text-foreground">{step.title}</p>
                        <p className="mt-0.5 text-[11px] text-muted-foreground">{step.desc}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="mt-6 border-t border-border pt-4">
              <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Activity Stream</span>
              <div className="mt-2 h-28 overflow-y-auto rounded-md border border-border p-3 text-[11px] font-mono text-muted-foreground space-y-1.5 scrollbar-none">
                {logs.length === 0 ? (
                  <p className="italic">Click "Generate Tailored Resume" to view building stream...</p>
                ) : (
                  logs.map((log, i) => (
                    <p key={i} className="leading-tight">
                      {log}
                    </p>
                  ))
                )}
              </div>
            </div>
          </Panel>
        </div>

        {/* RIGHT / RESUME PREVIEW OUTPUT (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          <Panel title={`Tailored Resume Preview (v${tailoredVersion})`} aside={`Tailored for ${selectedJob.co}`}>
            <article className="space-y-6 border-t border-border pt-5 text-sm leading-relaxed">
              <div className="border-b border-border pb-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-medium">{profile.name}</h3>
                  <span className="text-xs tabular-nums text-muted-foreground">{selectedJob.match}% ATS Score</span>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {profile.title} · {profile.location} · {profile.email}
                </p>
              </div>

              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Executive Summary</p>
                <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                  {profile.name} is a {profile.title} with 6+ years of expertise in system architecture,{" "}
                  {selectedJob.keywords.slice(0, 2).join(", ")}, and high-performance application design.
                </p>
              </div>

              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Tailored Experience</p>
                <div className="mt-2">
                  <div className="flex justify-between items-baseline">
                    <p className="text-xs font-medium text-foreground">Senior Engineer — Analytical Systems</p>
                    <span className="text-[11px] text-muted-foreground">2022 – Present</span>
                  </div>
                  <ul className="mt-2 list-none space-y-2 text-xs text-muted-foreground">
                    <li>— Led migration of core frontend architecture for <strong className="text-foreground">{selectedJob.co}</strong>, cutting run time 43%.</li>
                    <li>— Engineered type-safe contract layer with <strong className="text-foreground">TypeScript &amp; React</strong> across 4 teams.</li>
                    <li>— Integrated automated ATS formatting, raising keyword coverage to {selectedJob.match}%.</li>
                  </ul>
                </div>
              </div>

              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Skills</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {[...profile.skills.map((s) => s.name), ...selectedJob.keywords].map((skill, i) => (
                    <span
                      key={i}
                      className="rounded-full border border-border px-2.5 py-0.5 text-[11px] text-muted-foreground"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            </article>

            <div className="mt-6 flex flex-wrap gap-3 border-t border-border pt-4">
              <LineButton variant="solid" onClick={handleSaveToProfile} className="gap-2 text-xs">
                <OutlineIcon icon={Bookmark} size={14} /> Save to Profile
              </LineButton>
              <LineButton
                variant="outline"
                onClick={() => toast.info("Simulated PDF Export complete!")}
                className="gap-2 text-xs"
              >
                <OutlineIcon icon={Download} size={14} /> Export PDF
              </LineButton>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}

// ----------------------------------------------------
// VALIDATION AGENT COMPONENT
// ----------------------------------------------------
const checks = [
  { label: "Contact block parsable", state: "pass", note: "Email and phone detected" },
  { label: "Reverse-chronological order", state: "pass", note: "Consistent across roles" },
  { label: "Bullet length", state: "warn", note: "Two bullets exceed 24 words" },
  { label: "Keyword coverage vs. target roles", state: "pass", note: "TypeScript, React, System Design covered" },
  { label: "No tables or text boxes", state: "pass", note: "Clean single-column layout" },
  { label: "Quantified impact", state: "pass", note: "Metrics verified across bullet points" },
] as const;

const ValidationAgent = () => (
  <Panel title="Validation results" aside="6 checks complete">
    <ul className="divide-y divide-border">
      {checks.map((c) => (
        <li key={c.label} className="group flex items-start gap-4 py-4">
          <OutlineIcon
            icon={c.state === "pass" ? CircleCheck : c.state === "warn" ? CircleDashed : CircleAlert}
            size={18}
            className="mt-0.5 text-muted-foreground"
          />
          <div className="flex-1">
            <p className="text-sm font-medium">{c.label}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{c.note}</p>
          </div>
          <span
            className={cn(
              "mt-2 h-px w-8",
              c.state === "pass" ? "bg-border" : c.state === "warn" ? "bg-border-strong" : "bg-ink"
            )}
          />
        </li>
      ))}
    </ul>
  </Panel>
);

const productivity = () => (
  <div className="space-y-6">
    <Panel title="Weekly activity" aside="Applications sent">
      <Sparkline points={[2, 4, 3, 6, 5, 8, 7, 9, 6, 11]} />
      <div className="mt-2 flex justify-between text-xs text-muted-foreground">
        <span>10 weeks ago</span>
        <span>This week</span>
      </div>
    </Panel>
    <Panel title="Streak" aside="9 days active">
      <div className="flex flex-wrap gap-2">
        {Array.from({ length: 21 }).map((_, i) => (
          <span
            key={i}
            className={cn(
              "h-5 w-5 rounded-full border",
              i > 11 ? "border-ink" : i > 5 ? "border-border-strong" : "border-border"
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
      return <ResumeBuilderAgent />;
    case "validation":
      return <ValidationAgent />;
    case "job-search":
      return <JobSearchAgent />;
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
