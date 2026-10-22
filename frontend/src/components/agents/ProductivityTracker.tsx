"use client";

/**
 * Productivity tracker (backend: app/modules/productivity, routes in API_ENDPOINTS.productivity).
 * No agent run: habits and check-ins are plain data, saved the moment you tap.
 *
 * Learning is linked to mock tests: weak topics from graded attempts are suggested here,
 * a tracked topic counts the study since it was last tested, and the score trend sits
 * next to the learning time logged before each test.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Archive,
  ArrowDownRight,
  ArrowUpRight,
  BookOpen,
  Briefcase,
  Check,
  Dumbbell,
  Flame,
  HeartPulse,
  Leaf,
  Loader2,
  Plus,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { LineButton } from "@/components/LineButton";
import { useAuth } from "@/context/AuthContext";
import { API_ENDPOINTS, ApiRequestError } from "@/lib/api";
import { cn } from "@/lib/utils";

type Category = "fitness" | "learning" | "career" | "wellbeing" | "other";

interface Habit {
  id: string;
  name: string;
  category: Category;
  targetPerWeek: number;
  targetMinutes: number | null;
  linkedTopic: string | null;
}
interface HabitStatus {
  habit: Habit;
  doneToday: boolean;
  minutesToday: number | null;
  weekCount: number;
  streak: number;
  streakUnit: "days" | "weeks";
  last7: boolean[];
  totalSessions: number;
  totalMinutes: number;
}
interface LearningTopic {
  topic: string;
  role: string;
  latestPercent: number;
  previousPercent: number | null;
  delta: number | null;
  lastTested: string;
  habitId: string | null;
  sessionsSinceTest: number;
  minutesSinceTest: number;
  status: "untracked" | "not_started" | "studying" | "ready_to_retest" | "improved";
}
interface ScorePoint {
  attemptId: string;
  takenAt: string;
  percent: number;
  role: string;
  learningSessionsBefore: number;
  learningMinutesBefore: number;
}
interface Overview {
  today: string;
  habits: HabitStatus[];
  doneToday: number;
  weekCompletion: number;
  heatmap: { day: string; completed: number }[];
  learning: LearningTopic[];
  scoreTrend: ScorePoint[];
}

const CATEGORY_ICON = {
  fitness: Dumbbell,
  learning: BookOpen,
  career: Briefcase,
  wellbeing: Leaf,
  other: HeartPulse,
} as const;

const PRESETS: {
  name: string;
  category: Category;
  targetPerWeek: number;
  targetMinutes: number;
}[] = [
  { name: "Gym", category: "fitness", targetPerWeek: 3, targetMinutes: 60 },
  { name: "Cardio", category: "fitness", targetPerWeek: 5, targetMinutes: 30 },
  { name: "Learn a new topic", category: "learning", targetPerWeek: 7, targetMinutes: 30 },
  { name: "Apply to jobs", category: "career", targetPerWeek: 5, targetMinutes: 30 },
  { name: "Mock interview practice", category: "career", targetPerWeek: 2, targetMinutes: 30 },
  { name: "Sleep 8 hours", category: "wellbeing", targetPerWeek: 7, targetMinutes: 480 },
];

const STATUS_LABEL: Record<LearningTopic["status"], string> = {
  untracked: "Not tracked",
  not_started: "Not started",
  studying: "Studying",
  ready_to_retest: "Ready to retest",
  improved: "Improved",
};

/** The user's LOCAL calendar date, YYYY-MM-DD (not UTC). */
function localDate(offsetDays = 0): string {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

const shortDate = (iso: string) =>
  new Date(iso.length === 10 ? `${iso}T00:00:00` : iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="mb-3 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
      {children}
    </h3>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-[10px] uppercase tracking-widest text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
      {hint ? <p className="mt-0.5 text-[10px] text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

/* ── One habit row ────────────────────────────────────────────────────────── */

function HabitRow({
  status,
  onToggle,
  onMinutes,
  onArchive,
  onDelete,
  busy,
}: {
  status: HabitStatus;
  onToggle: () => void;
  onMinutes: (minutes: number | null) => void;
  onArchive: () => void;
  onDelete: () => void;
  busy: boolean;
}) {
  const { habit } = status;
  const Icon = CATEGORY_ICON[habit.category] ?? HeartPulse;
  const [minutes, setMinutes] = useState(status.minutesToday?.toString() ?? "");
  useEffect(() => setMinutes(status.minutesToday?.toString() ?? ""), [status.minutesToday]);
  const weekly = habit.targetPerWeek < 7;

  return (
    <li className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
      <button
        type="button"
        onClick={onToggle}
        disabled={busy}
        aria-pressed={status.doneToday}
        aria-label={`${status.doneToday ? "Undo" : "Check in"} ${habit.name} for today`}
        className={cn(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border transition-colors",
          status.doneToday
            ? "border-foreground bg-foreground text-background"
            : "border-border hover:border-foreground",
        )}
      >
        {busy ? (
          <Loader2 size={12} className="animate-spin" />
        ) : status.doneToday ? (
          <Check size={13} />
        ) : null}
      </button>

      <div className="min-w-0 flex-1">
        <p className="flex items-center gap-1.5 text-xs font-medium">
          <Icon size={12} className="text-muted-foreground" /> {habit.name}
          {habit.linkedTopic ? (
            <span className="rounded-full border border-border px-1.5 py-px text-[9px] font-normal text-muted-foreground">
              mock-test topic
            </span>
          ) : null}
        </p>
        <p className="mt-0.5 text-[10px] text-muted-foreground">
          {weekly ? `${status.weekCount}/${habit.targetPerWeek} this week` : "Daily"}
          {habit.targetMinutes ? ` · ${habit.targetMinutes} min goal` : ""}
          {status.totalMinutes ? ` · ${Math.round(status.totalMinutes / 60)}h total` : ""}
        </p>
      </div>

      {/* Last 7 days, oldest → today */}
      <div className="flex gap-1" aria-label="Last 7 days">
        {status.last7.map((done, i) => (
          <span
            key={i}
            title={`${shortDate(localDate(i - 6))}: ${done ? "done" : "not done"}`}
            className={cn(
              "h-2.5 w-2.5 rounded-sm",
              done ? "bg-foreground" : "bg-muted",
              i === 6 && "ring-1 ring-foreground/30 ring-offset-1 ring-offset-card",
            )}
          />
        ))}
      </div>

      <span
        className="flex w-16 items-center justify-end gap-1 text-[11px] tabular-nums"
        title={`Streak: ${status.streak} ${status.streakUnit}`}
      >
        <Flame
          size={12}
          className={status.streak ? "text-foreground" : "text-muted-foreground/50"}
        />
        {status.streak}
        <span className="text-[9px] text-muted-foreground">
          {status.streakUnit === "days" ? "d" : "wk"}
        </span>
      </span>

      {status.doneToday ? (
        <label className="flex items-center gap-1 text-[10px] text-muted-foreground">
          <input
            type="number"
            min={1}
            max={1440}
            value={minutes}
            onChange={(event) => setMinutes(event.target.value)}
            onBlur={() => {
              const value = minutes ? Number(minutes) : null;
              if (value !== status.minutesToday) onMinutes(value && value > 0 ? value : null);
            }}
            aria-label={`Minutes of ${habit.name} today`}
            className="h-6 w-14 rounded border border-border bg-transparent px-1.5 text-right text-[11px] text-foreground outline-none focus:border-foreground"
          />
          min
        </label>
      ) : null}

      <span className="flex gap-1">
        <button
          type="button"
          onClick={onArchive}
          aria-label={`Archive ${habit.name}`}
          title="Archive (keeps history)"
          className="rounded p-1 text-muted-foreground hover:text-foreground"
        >
          <Archive size={12} />
        </button>
        <button
          type="button"
          onClick={onDelete}
          aria-label={`Delete ${habit.name}`}
          title="Delete with its history"
          className="rounded p-1 text-muted-foreground hover:text-destructive"
        >
          <Trash2 size={12} />
        </button>
      </span>
    </li>
  );
}

/* ── Charts (one measure per chart; never a dual axis) ────────────────────── */

function ColumnChart({
  title,
  points,
  value,
  max,
  format,
}: {
  title: string;
  points: ScorePoint[];
  value: (p: ScorePoint) => number;
  max: number;
  format: (p: ScorePoint) => string;
}) {
  const height = 96;
  const top = Math.max(max, 1);
  return (
    <figure>
      <figcaption className="mb-2 text-[10px] text-muted-foreground">{title}</figcaption>
      <div
        className="flex h-[96px] items-end gap-1.5 border-b border-border"
        role="img"
        aria-label={title}
      >
        {points.map((p) => {
          const h = Math.max(2, Math.round((value(p) / top) * height));
          return (
            <div key={p.attemptId} className="group relative flex flex-1 justify-center">
              <div
                className="w-full max-w-7 rounded-t-[4px] bg-foreground/75 transition-colors group-hover:bg-foreground"
                style={{ height: `${h}px` }}
              />
              <div className="pointer-events-none absolute bottom-full z-10 mb-1 hidden whitespace-nowrap rounded border border-border bg-popover px-2 py-1 text-[10px] text-popover-foreground shadow-sm group-hover:block">
                {format(p)}
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-1 flex gap-1.5">
        {points.map((p) => (
          <span key={p.attemptId} className="flex-1 text-center text-[9px] text-muted-foreground">
            {shortDate(p.takenAt)}
          </span>
        ))}
      </div>
    </figure>
  );
}

function ScoreVsLearning({ points }: { points: ScorePoint[] }) {
  if (points.length === 0) return null;
  const maxMinutes = Math.max(...points.map((p) => p.learningMinutesBefore), 30);
  return (
    <div className="space-y-4">
      <ColumnChart
        title="Mock-test score (%)"
        points={points}
        value={(p) => p.percent}
        max={100}
        format={(p) => `${p.percent}% · ${p.role} · ${shortDate(p.takenAt)}`}
      />
      <ColumnChart
        title="Learning logged before each test (minutes)"
        points={points}
        value={(p) => p.learningMinutesBefore}
        max={maxMinutes}
        format={(p) =>
          `${p.learningMinutesBefore} min in ${p.learningSessionsBefore} session${p.learningSessionsBefore === 1 ? "" : "s"}`
        }
      />
      <details className="text-[10px] text-muted-foreground">
        <summary className="cursor-pointer">View as table</summary>
        <table className="mt-2 w-full text-left tabular-nums">
          <thead>
            <tr className="border-b border-border">
              <th className="py-1 font-medium">Test</th>
              <th className="py-1 font-medium">Role</th>
              <th className="py-1 text-right font-medium">Score</th>
              <th className="py-1 text-right font-medium">Learning before</th>
            </tr>
          </thead>
          <tbody>
            {points.map((p) => (
              <tr key={p.attemptId} className="border-b border-border/60">
                <td className="py-1">{shortDate(p.takenAt)}</td>
                <td className="py-1">{p.role}</td>
                <td className="py-1 text-right text-foreground">{p.percent}%</td>
                <td className="py-1 text-right">{p.learningMinutesBefore} min</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}

/** Last 28 days: one hue, light → dark by how many habits were done. */
function Heatmap({ days, habits }: { days: Overview["heatmap"]; habits: number }) {
  const shade = (completed: number) => {
    if (completed === 0 || habits === 0) return "bg-muted";
    const share = completed / habits;
    if (share >= 1) return "bg-foreground";
    if (share >= 0.66) return "bg-foreground/70";
    if (share >= 0.33) return "bg-foreground/45";
    return "bg-foreground/25";
  };
  return (
    <div>
      <div
        className="grid grid-cols-7 gap-1"
        role="img"
        aria-label="Habits completed per day, last 28 days"
      >
        {days.map((d) => (
          <span
            key={d.day}
            title={`${shortDate(d.day)}: ${d.completed} of ${habits} habits`}
            className={cn("aspect-square rounded-[3px]", shade(d.completed))}
          />
        ))}
      </div>
      <div className="mt-2 flex items-center justify-end gap-1 text-[9px] text-muted-foreground">
        Less
        {[
          "bg-muted",
          "bg-foreground/25",
          "bg-foreground/45",
          "bg-foreground/70",
          "bg-foreground",
        ].map((c) => (
          <span key={c} className={cn("h-2 w-2 rounded-[2px]", c)} />
        ))}
        More
      </div>
    </div>
  );
}

/* ── Add a habit ──────────────────────────────────────────────────────────── */

function AddHabit({
  existing,
  onAdd,
}: {
  existing: string[];
  onAdd: (body: Record<string, unknown>) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [category, setCategory] = useState<Category>("other");
  const [perWeek, setPerWeek] = useState(7);
  const [minutes, setMinutes] = useState("");
  const taken = new Set(existing.map((n) => n.toLowerCase()));
  const presets = PRESETS.filter((p) => !taken.has(p.name.toLowerCase()));

  return (
    <div className="space-y-3">
      {presets.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {presets.map((p) => (
            <button
              key={p.name}
              type="button"
              onClick={() => onAdd({ ...p })}
              className="inline-flex items-center gap-1 rounded-full border border-dashed border-border px-2.5 py-1 text-[11px] hover:border-foreground"
            >
              <Plus size={11} /> {p.name}
              <span className="text-muted-foreground">
                · {p.targetPerWeek === 7 ? "daily" : `${p.targetPerWeek}×/wk`}
              </span>
            </button>
          ))}
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="rounded-full border border-border px-2.5 py-1 text-[11px] hover:border-foreground"
          >
            {open ? "Close" : "Custom…"}
          </button>
        </div>
      ) : null}
      {open || presets.length === 0 ? (
        <form
          className="flex flex-wrap items-end gap-3 rounded-lg border border-border p-3"
          onSubmit={async (event) => {
            event.preventDefault();
            if (!name.trim()) return;
            await onAdd({
              name: name.trim(),
              category,
              targetPerWeek: perWeek,
              targetMinutes: minutes ? Number(minutes) : null,
            });
            setName("");
            setMinutes("");
          }}
        >
          <label className="text-[10px] text-muted-foreground">
            Habit
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={60}
              placeholder="e.g. Yoga"
              className="mt-1 block h-8 w-44 rounded-md border border-border bg-transparent px-2 text-xs text-foreground outline-none focus:border-foreground"
            />
          </label>
          <label className="text-[10px] text-muted-foreground">
            Type
            <select
              value={category}
              onChange={(event) => setCategory(event.target.value as Category)}
              className="mt-1 block h-8 rounded-md border border-border bg-background px-2 text-xs text-foreground"
            >
              {Object.keys(CATEGORY_ICON).map((c) => (
                <option key={c} value={c}>
                  {c[0]!.toUpperCase() + c.slice(1)}
                </option>
              ))}
            </select>
          </label>
          <label className="text-[10px] text-muted-foreground">
            How often
            <select
              value={perWeek}
              onChange={(event) => setPerWeek(Number(event.target.value))}
              className="mt-1 block h-8 rounded-md border border-border bg-background px-2 text-xs text-foreground"
            >
              {[7, 6, 5, 4, 3, 2, 1].map((n) => (
                <option key={n} value={n}>
                  {n === 7 ? "Every day" : `${n}× a week`}
                </option>
              ))}
            </select>
          </label>
          <label className="text-[10px] text-muted-foreground">
            Minutes (optional)
            <input
              type="number"
              min={5}
              max={600}
              value={minutes}
              onChange={(event) => setMinutes(event.target.value)}
              className="mt-1 block h-8 w-24 rounded-md border border-border bg-transparent px-2 text-xs text-foreground outline-none focus:border-foreground"
            />
          </label>
          <LineButton variant="solid" type="submit" className="h-8 gap-1 text-xs">
            <Plus size={12} /> Add
          </LineButton>
        </form>
      ) : null}
    </div>
  );
}

/* ── Learning from mock tests ─────────────────────────────────────────────── */

function LearningPanel({
  topics,
  onTrack,
}: {
  topics: LearningTopic[];
  onTrack: (topic: string) => void;
}) {
  if (topics.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-border p-4 text-[11px] leading-relaxed text-muted-foreground">
        Take a mock test on the{" "}
        <Link
          href="/agents/interview"
          className="underline underline-offset-2 hover:text-foreground"
        >
          Interview Preparation
        </Link>{" "}
        page. Topics you score low on show up here to study, and your next score shows whether it
        worked.
      </p>
    );
  }
  return (
    <ul className="divide-y divide-border rounded-lg border border-border">
      {topics.map((t) => (
        <li key={t.topic} className="flex flex-wrap items-center gap-x-4 gap-y-1.5 px-4 py-3">
          <div className="min-w-0 flex-1">
            <p className="text-xs font-medium">{t.topic}</p>
            <p className="mt-0.5 text-[10px] text-muted-foreground">
              {t.role} · tested {shortDate(t.lastTested)}
              {t.habitId
                ? ` · ${t.sessionsSinceTest} session${t.sessionsSinceTest === 1 ? "" : "s"}${
                    t.minutesSinceTest ? `, ${t.minutesSinceTest} min` : ""
                  } since`
                : ""}
            </p>
          </div>
          <span className="flex items-center gap-1 text-xs tabular-nums">
            {t.previousPercent !== null ? (
              <span className="text-muted-foreground">{t.previousPercent}% →</span>
            ) : null}
            <span className="font-semibold">{t.latestPercent}%</span>
            {t.delta !== null && t.delta !== 0 ? (
              t.delta > 0 ? (
                <ArrowUpRight size={12} aria-label={`up ${t.delta} points`} />
              ) : (
                <ArrowDownRight size={12} aria-label={`down ${-t.delta} points`} />
              )
            ) : null}
          </span>
          <span
            className={cn(
              "rounded-full px-2 py-0.5 text-[9px]",
              t.status === "ready_to_retest" || t.status === "improved"
                ? "bg-foreground text-background"
                : "border border-border text-muted-foreground",
            )}
          >
            {STATUS_LABEL[t.status]}
          </span>
          {t.status === "untracked" ? (
            <button
              type="button"
              onClick={() => onTrack(t.topic)}
              className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-0.5 text-[10px] hover:border-foreground"
            >
              <Plus size={10} /> Track
            </button>
          ) : t.status === "ready_to_retest" ? (
            <Link
              href="/agents/interview"
              className="rounded-md border border-foreground px-2 py-0.5 text-[10px] hover:bg-foreground hover:text-background"
            >
              Retake a test
            </Link>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

/* ── The tracker ──────────────────────────────────────────────────────────── */

export function ProductivityTracker() {
  const { authFetch } = useAuth();
  const [data, setData] = useState<Overview | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");
  const today = useMemo(() => localDate(), []);

  const load = useCallback(async () => {
    try {
      const params = new URLSearchParams({ today });
      const response = await authFetch<Overview>(
        `${API_ENDPOINTS.productivity.overview}?${params}`,
      );
      setData(response.data);
      setError("");
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Couldn't load your tracker.");
    }
  }, [authFetch, today]);
  useEffect(() => {
    void load();
  }, [load]);

  const act = async (key: string, run: () => Promise<unknown>, success?: string) => {
    setBusy(key);
    try {
      await run();
      await load();
      if (success) toast.success(success);
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : "Something went wrong.");
    } finally {
      setBusy(null);
    }
  };

  const logUrl = (id: string) =>
    `${API_ENDPOINTS.productivity.log(id, today)}?${new URLSearchParams({ today })}`;

  const toggle = (s: HabitStatus) =>
    act(s.habit.id, () =>
      s.doneToday
        ? authFetch(logUrl(s.habit.id), { method: "DELETE" })
        : authFetch(logUrl(s.habit.id), {
            method: "PUT",
            body: JSON.stringify({ minutes: s.habit.targetMinutes }),
          }),
    );

  const add = (body: Record<string, unknown>) =>
    act(
      "add",
      () =>
        authFetch(API_ENDPOINTS.productivity.habits, {
          method: "POST",
          body: JSON.stringify(body),
        }),
      "Habit added.",
    );

  if (!data) {
    return (
      <div className="rounded-lg border border-dashed border-border p-8 text-center text-xs text-muted-foreground">
        {error || "Loading your tracker…"}
      </div>
    );
  }

  const bestStreak = data.habits.reduce((best, s) => (s.streak > best.streak ? s : best), {
    streak: 0,
    streakUnit: "days",
  } as Pick<HabitStatus, "streak" | "streakUnit">);
  const learningThisWeek = data.habits
    .filter((s) => s.habit.category === "learning")
    .reduce((sum, s) => sum + s.weekCount, 0);

  return (
    <div className="space-y-10">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Today" value={`${data.doneToday}/${data.habits.length}`} hint="habits done" />
        <Stat label="This week" value={`${data.weekCompletion}%`} hint="of your targets" />
        <Stat
          label="Best streak"
          value={String(bestStreak.streak)}
          hint={bestStreak.streakUnit === "days" ? "days in a row" : "weeks on target"}
        />
        <Stat label="Learning" value={String(learningThisWeek)} hint="sessions this week" />
      </div>

      <div className="grid gap-10 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <section>
          <SectionLabel>Today · {shortDate(data.today)}</SectionLabel>
          {data.habits.length > 0 ? (
            <ul className="mb-4 divide-y divide-border rounded-lg border border-border bg-card">
              {data.habits.map((s) => (
                <HabitRow
                  key={s.habit.id}
                  status={s}
                  busy={busy === s.habit.id}
                  onToggle={() => toggle(s)}
                  onMinutes={(minutes) =>
                    act(s.habit.id, () =>
                      authFetch(logUrl(s.habit.id), {
                        method: "PUT",
                        body: JSON.stringify({ minutes }),
                      }),
                    )
                  }
                  onArchive={() =>
                    act(
                      s.habit.id,
                      () =>
                        authFetch(API_ENDPOINTS.productivity.habit(s.habit.id), {
                          method: "PATCH",
                          body: JSON.stringify({ archived: true }),
                        }),
                      `Archived ${s.habit.name}.`,
                    )
                  }
                  onDelete={() => {
                    if (!window.confirm(`Delete ${s.habit.name} and all its check-ins?`)) return;
                    void act(
                      s.habit.id,
                      () =>
                        authFetch(API_ENDPOINTS.productivity.habit(s.habit.id), {
                          method: "DELETE",
                        }),
                      `Deleted ${s.habit.name}.`,
                    );
                  }}
                />
              ))}
            </ul>
          ) : (
            <p className="mb-4 text-[11px] text-muted-foreground">
              Add the habits you want to keep. Tap the circle each day you do them.
            </p>
          )}
          <AddHabit existing={data.habits.map((s) => s.habit.name)} onAdd={add} />
        </section>

        <section>
          <SectionLabel>Last 4 weeks</SectionLabel>
          <Heatmap days={data.heatmap} habits={data.habits.length} />
        </section>
      </div>

      <div className="grid gap-10 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <section>
          <SectionLabel>Learn from your mock tests</SectionLabel>
          <LearningPanel
            topics={data.learning}
            onTrack={(topic) => add({ linkedTopic: topic, targetPerWeek: 5, targetMinutes: 30 })}
          />
        </section>
        <section>
          <SectionLabel>Scores vs learning</SectionLabel>
          {data.scoreTrend.length > 0 ? (
            <ScoreVsLearning points={data.scoreTrend} />
          ) : (
            <p className="text-[11px] text-muted-foreground">
              Your mock-test scores appear here, next to the learning you logged before each one.
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
