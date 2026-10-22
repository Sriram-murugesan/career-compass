"use client";

/**
 * Renders the REAL output of one backend agent (from an orchestration run).
 * Shapes mirror the Pydantic schemas in backend/app/agents/<agent>/schema.py,
 * camelCased by the API.
 */

import { Building2, CalendarDays, ExternalLink, MapPin } from "lucide-react";
import { cn } from "@/lib/utils";

type Output = Record<string, unknown>;

interface JobMatch {
  role: string;
  company: string;
  location: string;
  matchScore: number;
  reason: string;
  // Re-ranking detail (AI-ranked live postings only):
  fit?: { skills: number; experience: number; location: number; goals: number } | null;
  eligibility?: "eligible" | "check" | "unlikely" | null;
  matchedSkills?: string[];
  missingSkills?: string[];
  nextStep?: string;
  // Live postings only (from the job board, never written by the model):
  applyUrl?: string | null;
  postedAt?: string | null;
  salary?: string | null;
  source?: string | null;
}

/** "2026-10-10T09:00:00Z" → "2 days ago" / "today" / "Oct 3". */
function postedLabel(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const days = Math.floor((Date.now() - date.getTime()) / 86_400_000);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 14) return `${days} days ago`;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
const FIT_LABELS = [
  ["skills", "Skills"],
  ["experience", "Level"],
  ["location", "Location"],
  ["goals", "Goals"],
] as const;

const ELIGIBILITY = {
  eligible: { label: "Can apply from your region", tone: "text-emerald-700 dark:text-emerald-400" },
  check: { label: "Check location eligibility", tone: "text-amber-700 dark:text-amber-400" },
  unlikely: { label: "Hires outside your region", tone: "text-red-700 dark:text-red-400" },
} as const;

/** Four small bars: how the final score was built. */
function FitBars({ fit }: { fit: NonNullable<JobMatch["fit"]> }) {
  return (
    <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 sm:grid-cols-4">
      {FIT_LABELS.map(([key, label]) => (
        <div key={key}>
          <div className="flex justify-between text-[9px] text-muted-foreground">
            <span>{label}</span>
            <span className="tabular-nums">{fit[key]}</span>
          </div>
          <div className="mt-0.5 h-1 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-foreground/70"
              style={{ width: `${fit[key]}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function SkillChips({ skills, missing }: { skills: string[]; missing?: boolean }) {
  if (skills.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-1">
      <span className="text-[9px] text-muted-foreground">{missing ? "Gaps:" : "You have:"}</span>
      {skills.map((skill) => (
        <span
          key={skill}
          className={cn(
            "rounded-full border px-1.5 py-px text-[9px]",
            missing
              ? "border-dashed border-border text-muted-foreground"
              : "border-border bg-muted/60 text-foreground",
          )}
        >
          {skill}
        </span>
      ))}
    </div>
  );
}

interface Check {
  label: string;
  state: "pass" | "warn" | "fail";
  note: string;
}
interface Milestone {
  title: string;
  when: string;
  note: string;
}

const list = <T,>(value: unknown): T[] => (Array.isArray(value) ? (value as T[]) : []);
const text = (value: unknown): string => (typeof value === "string" ? value : "");

function Label({ children }: { children: React.ReactNode }) {
  return (
    <span className="block text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
      {children}
    </span>
  );
}

export function AgentOutput({
  agentId,
  output,
  onTailor,
}: {
  /** backend agent id, e.g. "job_search" */
  agentId: string;
  output: Output;
  /** Optional action on a job match (e.g. open the Resume agent for it). */
  onTailor?: (match: JobMatch) => void;
}) {
  switch (agentId) {
    case "job_search": {
      const matches = list<JobMatch>(output["matches"]);
      const live = output["mode"] === "live";
      const notice = text(output["notice"]);
      const query = text(output["query"]);
      const considered = typeof output["considered"] === "number" ? output["considered"] : 0;
      const ranking = text(output["ranking"]);
      return (
        <div className="space-y-3">
          <Label>
            {live ? `Live job postings${query ? ` · ${query}` : ""}` : "Suggested role types"}
          </Label>
          {live && considered > 0 && matches.length > 0 ? (
            <p className="text-[10px] text-muted-foreground">
              Top {matches.length} of {considered} postings,{" "}
              {ranking === "ai"
                ? "re-ranked by AI on skills, level, location and goals"
                : "ranked by keyword match"}
              .
            </p>
          ) : null}
          {notice ? (
            <p className="rounded-md border border-dashed border-border p-2.5 text-[10px] leading-relaxed text-muted-foreground">
              {notice}
            </p>
          ) : null}
          {matches.length === 0 ? <Empty /> : null}
          {matches.map((job) => (
            <div
              key={job.applyUrl ?? `${job.role}-${job.company}`}
              className="flex flex-col gap-3 rounded-md border border-border bg-card p-4 sm:flex-row sm:items-start sm:justify-between"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h4 className="text-xs font-semibold">{job.role}</h4>
                  <span className="rounded-full bg-accent/5 px-2 py-0.5 text-[10px] font-semibold text-ink">
                    {job.matchScore}% fit
                  </span>
                </div>
                <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-muted-foreground">
                  <span className="flex items-center gap-1 font-medium text-foreground">
                    <Building2 size={11} /> {job.company}
                  </span>
                  {job.location ? (
                    <span className="flex items-center gap-1">
                      <MapPin size={11} /> {job.location}
                    </span>
                  ) : null}
                  {job.postedAt ? (
                    <span className="flex items-center gap-1">
                      <CalendarDays size={11} /> Posted {postedLabel(job.postedAt)}
                    </span>
                  ) : null}
                  {job.salary ? <span>{job.salary}</span> : null}
                </div>
                <p className="mt-2 text-[10px] leading-relaxed text-muted-foreground">
                  {job.reason}
                </p>
                {job.fit ? <FitBars fit={job.fit} /> : null}
                {(job.matchedSkills?.length ?? 0) + (job.missingSkills?.length ?? 0) > 0 ? (
                  <div className="mt-2 space-y-1">
                    <SkillChips skills={job.matchedSkills ?? []} />
                    <SkillChips skills={job.missingSkills ?? []} missing />
                  </div>
                ) : null}
                {job.eligibility ? (
                  <p
                    className={cn("mt-2 text-[9px] font-medium", ELIGIBILITY[job.eligibility].tone)}
                  >
                    {ELIGIBILITY[job.eligibility].label}
                  </p>
                ) : null}
                {job.nextStep ? (
                  <p className="mt-2 border-l-2 border-border pl-2 text-[10px] leading-relaxed">
                    <span className="font-semibold">Next step: </span>
                    {job.nextStep}
                  </p>
                ) : null}
                {job.source ? (
                  <p className="mt-1 text-[9px] uppercase tracking-wider text-muted-foreground/70">
                    via {job.source}
                  </p>
                ) : null}
              </div>
              <div className="flex shrink-0 gap-2 self-end sm:flex-col sm:self-start">
                {job.applyUrl ? (
                  <a
                    href={job.applyUrl}
                    target="_blank"
                    rel="noopener noreferrer nofollow"
                    className="inline-flex items-center justify-center gap-1 rounded-md border border-foreground bg-foreground px-3 py-1 text-[10px] font-semibold text-background transition-colors hover:bg-transparent hover:text-foreground"
                  >
                    Apply <ExternalLink size={10} />
                  </a>
                ) : null}
                {onTailor ? (
                  <button
                    type="button"
                    onClick={() => onTailor(job)}
                    className="rounded-md border border-border px-3 py-1 text-[10px] font-semibold transition-colors hover:border-ink hover:text-ink"
                  >
                    Tailor resume
                  </button>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      );
    }

    case "resume": {
      const bullets = list<string>(output["bullets"]);
      const keywords = list<string>(output["keywords"]);
      return (
        <div className="space-y-3">
          <Label>Resume draft · {text(output["targetRole"])}</Label>
          <p className="text-xs leading-relaxed text-foreground">{text(output["summary"])}</p>
          {bullets.length ? (
            <ul className="list-disc space-y-1.5 pl-4 text-[11px] leading-relaxed text-foreground">
              {bullets.map((bullet) => (
                <li key={bullet}>{bullet}</li>
              ))}
            </ul>
          ) : null}
          {keywords.length ? (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {keywords.map((keyword) => (
                <span
                  key={keyword}
                  className="rounded-full border border-border px-2 py-0.5 text-[10px] text-muted-foreground"
                >
                  {keyword}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      );
    }

    case "validation": {
      const checks = list<Check>(output["checks"]);
      return (
        <div className="space-y-3">
          <Label>ATS score: {String(output["atsScore"] ?? "—")} / 100</Label>
          <div className="divide-y divide-border rounded-md border border-border bg-card text-[11px]">
            {checks.map((check) => (
              <div key={check.label} className="flex items-center justify-between gap-4 p-3">
                <div>
                  <p className="font-medium text-foreground">{check.label}</p>
                  <p className="mt-0.5 text-[10px] text-muted-foreground">{check.note}</p>
                </div>
                <span
                  className={cn(
                    "shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold",
                    check.state === "pass" && "bg-secondary text-foreground",
                    check.state === "warn" && "border border-ink/20 bg-accent/5 text-ink",
                    check.state === "fail" && "border border-destructive/30 text-destructive",
                  )}
                >
                  {check.state === "pass" ? "Passed" : check.state === "warn" ? "Review" : "Fix"}
                </span>
              </div>
            ))}
          </div>
        </div>
      );
    }

    case "roadmap": {
      const milestones = list<Milestone>(output["milestones"]);
      return (
        <div className="space-y-3">
          <Label>Roadmap · {text(output["goal"])}</Label>
          <div className="relative space-y-4 pl-6">
            <div className="absolute bottom-1 left-[7px] top-1 w-px border-l border-dashed border-border-strong" />
            {milestones.map((item, i) => (
              <div key={`${item.title}-${i}`} className="relative">
                <span className="absolute -left-[23px] top-1 flex h-3.5 w-3.5 items-center justify-center rounded-full border border-ink bg-background text-[8px] font-bold text-ink">
                  {i + 1}
                </span>
                <span className="text-[9px] uppercase tracking-wider text-muted-foreground">
                  {item.when}
                </span>
                <h4 className="mt-0.5 text-xs font-semibold text-foreground">{item.title}</h4>
                <p className="mt-0.5 text-[10px] text-muted-foreground">{item.note}</p>
              </div>
            ))}
          </div>
        </div>
      );
    }

    case "interview": {
      const questions = list<string>(output["questions"]);
      return (
        <div className="space-y-3">
          <Label>Practice questions · {text(output["focus"])}</Label>
          <div className="divide-y divide-border rounded-md border border-border bg-card text-[11px]">
            {questions.map((question, i) => (
              <div key={question} className="flex items-start gap-3 p-3">
                <span className="mt-0.5 font-semibold tabular-nums text-muted-foreground">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <p className="flex-1 leading-normal text-foreground">{question}</p>
              </div>
            ))}
          </div>
        </div>
      );
    }

    case "advisor":
    case "productivity": {
      const heading =
        agentId === "advisor" ? text(output["answer"]) : text(output["focusThisWeek"]);
      const steps = list<string>(
        agentId === "advisor" ? output["nextSteps"] : output["suggestions"],
      );
      return (
        <div className="space-y-3">
          <Label>{agentId === "advisor" ? "Advice" : "This week"}</Label>
          <p className="text-xs leading-relaxed text-foreground">{heading}</p>
          {steps.length ? (
            <ol className="list-decimal space-y-1.5 pl-4 text-[11px] leading-relaxed text-foreground">
              {steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          ) : null}
        </div>
      );
    }

    default:
      return <Empty />;
  }
}

function Empty() {
  return <p className="text-[11px] text-muted-foreground">No output.</p>;
}
