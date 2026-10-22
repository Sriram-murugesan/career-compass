"use client";

/**
 * Mock interview test (backend: app/modules/interview, routes in API_ENDPOINTS.interview).
 *
 * setup → the backend writes a multiple-choice test for one role + domain from the profile
 * take  → answers stay in the browser until submitted (the key never reaches the browser)
 * score → the backend grades instantly: score, per-topic breakdown, answers + explanations
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Check, Clock, Loader2, RotateCcw, Sparkles, X } from "lucide-react";
import { toast } from "sonner";
import { LineButton } from "@/components/LineButton";
import { useAuth } from "@/context/AuthContext";
import { formatDate, useUserProfile } from "@/context/UserProfileContext";
import { API_ENDPOINTS, ApiRequestError } from "@/lib/api";
import { cn } from "@/lib/utils";

type Difficulty = "mixed" | "easy" | "medium" | "hard";

interface Question {
  index: number;
  question: string;
  options: string[];
  topic: string;
  difficulty: string;
}
interface AttemptSummary {
  id: string;
  score: number;
  total: number;
  percent: number;
  createdAt: string;
}
interface MockTestData {
  id: string;
  role: string;
  domain: string;
  difficulty: string;
  createdAt: string;
  questions: Question[];
  attempts: AttemptSummary[];
  bestPercent: number | null;
}
interface MockTestSummary {
  id: string;
  role: string;
  domain: string;
  difficulty: string;
  questionCount: number;
  createdAt: string;
  attempts: number;
  bestPercent: number | null;
  lastPercent: number | null;
}
interface QuestionResult {
  index: number;
  question: string;
  options: string[];
  topic: string;
  yourAnswer: number | null;
  correctAnswer: number;
  correct: boolean;
  explanation: string;
}
interface AttemptResult {
  id: string;
  score: number;
  total: number;
  percent: number;
  grade: string;
  topics: { topic: string; correct: number; total: number; percent: number }[];
  weakTopics: string[];
  results: QuestionResult[];
  timeTakenSeconds: number | null;
  attemptNumber: number;
  bestPercent: number;
}

const LETTERS = ["A", "B", "C", "D"];
const COUNTS = [5, 10, 15, 20];
const DIFFICULTIES: Difficulty[] = ["mixed", "easy", "medium", "hard"];

const clock = (seconds: number) =>
  `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;

function Chip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "rounded-full border px-3 py-1 text-[11px] transition-colors",
        active
          ? "border-foreground bg-foreground text-background"
          : "border-border hover:border-foreground",
      )}
    >
      {children}
    </button>
  );
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="mb-2 block text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
      {children}
    </span>
  );
}

/* ── Setup ────────────────────────────────────────────────────────────────── */

function Setup({
  onStart,
  history,
  onRetake,
}: {
  onStart: (test: MockTestData) => void;
  history: MockTestSummary[];
  onRetake: (id: string) => void;
}) {
  const { authFetch } = useAuth();
  const { profile } = useUserProfile();
  const roles = profile.targetRoles.filter(Boolean);
  const domains = profile.interests.filter(Boolean);

  const [role, setRole] = useState(roles[0] ?? "");
  const [domain, setDomain] = useState(domains[0] ?? "");
  const [difficulty, setDifficulty] = useState<Difficulty>("mixed");
  const [count, setCount] = useState(10);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    // The profile loads after first render; pick its first role / interest once it arrives.
    setRole((current) => current || roles[0] || "");
    setDomain((current) => current || domains[0] || "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile.targetRoles.join("|"), profile.interests.join("|")]);

  const create = async () => {
    if (!role.trim()) {
      toast.error("Pick or type a role first.");
      return;
    }
    setCreating(true);
    try {
      const response = await authFetch<MockTestData>(API_ENDPOINTS.interview.mockTests, {
        method: "POST",
        body: JSON.stringify({ role: role.trim(), domain: domain.trim(), difficulty, count }),
      });
      onStart(response.data);
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : "Couldn't create the test.");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="space-y-5 rounded-lg border border-border bg-card p-5">
        <div>
          <FieldLabel>Role</FieldLabel>
          <div className="flex flex-wrap items-center gap-2">
            {roles.map((r) => (
              <Chip key={r} active={role === r} onClick={() => setRole(r)}>
                {r}
              </Chip>
            ))}
            <input
              value={roles.includes(role) ? "" : role}
              onChange={(event) => setRole(event.target.value)}
              placeholder={roles.length ? "or type another role" : "e.g. Frontend Engineer"}
              aria-label="Role for the mock test"
              maxLength={120}
              className="h-7 w-48 rounded-md border border-border bg-transparent px-2.5 text-[11px] outline-none focus:border-foreground"
            />
          </div>
        </div>

        <div>
          <FieldLabel>Domain</FieldLabel>
          <div className="flex flex-wrap items-center gap-2">
            <Chip active={domain === ""} onClick={() => setDomain("")}>
              Any
            </Chip>
            {domains.map((d) => (
              <Chip key={d} active={domain === d} onClick={() => setDomain(d)}>
                {d}
              </Chip>
            ))}
            <input
              value={domain === "" || domains.includes(domain) ? "" : domain}
              onChange={(event) => setDomain(event.target.value)}
              placeholder="or type a domain (e.g. Fintech)"
              aria-label="Domain for the mock test"
              maxLength={120}
              className="h-7 w-48 rounded-md border border-border bg-transparent px-2.5 text-[11px] outline-none focus:border-foreground"
            />
          </div>
        </div>

        <div className="flex flex-wrap gap-8">
          <div>
            <FieldLabel>Difficulty</FieldLabel>
            <div className="flex gap-2">
              {DIFFICULTIES.map((d) => (
                <Chip key={d} active={difficulty === d} onClick={() => setDifficulty(d)}>
                  {d[0]!.toUpperCase() + d.slice(1)}
                </Chip>
              ))}
            </div>
          </div>
          <div>
            <FieldLabel>Questions</FieldLabel>
            <div className="flex gap-2">
              {COUNTS.map((n) => (
                <Chip key={n} active={count === n} onClick={() => setCount(n)}>
                  {n}
                </Chip>
              ))}
            </div>
          </div>
        </div>

        <LineButton variant="solid" onClick={create} disabled={creating} className="gap-2">
          {creating ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={12} />}
          {creating ? "Writing your test…" : "Start mock test"}
        </LineButton>
        {creating ? (
          <p className="text-[11px] text-muted-foreground">
            Writing {count} questions for {role}
            {domain ? ` in ${domain}` : ""}, tuned to your skills and gaps. This usually takes 15–45
            seconds.
          </p>
        ) : null}
      </div>

      {history.length > 0 ? (
        <div>
          <FieldLabel>Your mock tests</FieldLabel>
          <ul className="divide-y divide-border rounded-md border border-border text-[11px]">
            {history.map((t) => (
              <li key={t.id} className="flex items-center justify-between gap-3 px-3 py-2.5">
                <span className="min-w-0">
                  <span className="font-medium text-foreground">{t.role}</span>
                  <span className="text-muted-foreground">
                    {t.domain ? ` · ${t.domain}` : ""} · {t.difficulty} · {t.questionCount}{" "}
                    questions · {formatDate(t.createdAt)}
                  </span>
                </span>
                <span className="flex shrink-0 items-center gap-3">
                  <span className="tabular-nums text-muted-foreground">
                    {t.bestPercent === null ? "not taken" : `best ${t.bestPercent}%`}
                  </span>
                  <button
                    type="button"
                    onClick={() => onRetake(t.id)}
                    className="rounded-md border border-border px-2 py-0.5 hover:border-foreground"
                  >
                    {t.attempts ? "Retake" : "Take"}
                  </button>
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

/* ── Taking the test ──────────────────────────────────────────────────────── */

function Taking({
  test,
  onSubmitted,
  onCancel,
}: {
  test: MockTestData;
  onSubmitted: (result: AttemptResult) => void;
  onCancel: () => void;
}) {
  const { authFetch } = useAuth();
  const [answers, setAnswers] = useState<(number | null)[]>(() => test.questions.map(() => null));
  const [elapsed, setElapsed] = useState(0);
  const [confirming, setConfirming] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const started = useRef(Date.now());

  useEffect(() => {
    const timer = window.setInterval(
      () => setElapsed(Math.floor((Date.now() - started.current) / 1000)),
      1000,
    );
    return () => window.clearInterval(timer);
  }, []);

  const answered = answers.filter((a) => a !== null).length;
  const unanswered = answers.length - answered;

  const submit = async () => {
    if (unanswered > 0 && !confirming) {
      setConfirming(true);
      return;
    }
    setSubmitting(true);
    try {
      const response = await authFetch<AttemptResult>(API_ENDPOINTS.interview.attempts(test.id), {
        method: "POST",
        body: JSON.stringify({ answers, timeTakenSeconds: elapsed }),
      });
      onSubmitted(response.data);
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : "Couldn't submit the test.");
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="sticky top-14 z-10 -mx-1 space-y-2 bg-background/95 px-1 py-2 backdrop-blur">
        <div className="flex items-center justify-between text-[11px]">
          <span>
            <span className="font-medium">{test.role}</span>
            <span className="text-muted-foreground">
              {test.domain ? ` · ${test.domain}` : ""} · {test.difficulty}
            </span>
          </span>
          <span className="flex items-center gap-3 tabular-nums text-muted-foreground">
            <span>
              {answered}/{answers.length} answered
            </span>
            <span className="flex items-center gap-1">
              <Clock size={11} /> {clock(elapsed)}
            </span>
          </span>
        </div>
        <div className="h-1 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-foreground transition-all"
            style={{ width: `${(100 * answered) / answers.length}%` }}
          />
        </div>
      </div>

      <ol className="space-y-4">
        {test.questions.map((q, i) => (
          <li key={q.index} className="rounded-lg border border-border bg-card p-4">
            <div className="mb-2 flex flex-wrap items-center gap-2 text-[10px] text-muted-foreground">
              <span className="font-semibold tabular-nums text-foreground">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span className="rounded-full border border-border px-1.5 py-px">{q.topic}</span>
              <span>{q.difficulty}</span>
            </div>
            <p className="whitespace-pre-wrap text-xs leading-relaxed text-foreground">
              {q.question}
            </p>
            <div className="mt-3 grid gap-2" role="radiogroup" aria-label={`Question ${i + 1}`}>
              {q.options.map((option, j) => {
                const chosen = answers[i] === j;
                return (
                  <button
                    key={option}
                    type="button"
                    role="radio"
                    aria-checked={chosen}
                    onClick={() => {
                      setConfirming(false);
                      setAnswers((prev) => prev.map((a, k) => (k === i ? j : a)));
                    }}
                    className={cn(
                      "flex items-start gap-2.5 rounded-md border px-3 py-2 text-left text-[11px] leading-relaxed transition-colors",
                      chosen
                        ? "border-foreground bg-foreground/5"
                        : "border-border hover:border-foreground/60",
                    )}
                  >
                    <span
                      className={cn(
                        "mt-px flex h-4 w-4 shrink-0 items-center justify-center rounded-full border text-[9px] font-semibold",
                        chosen
                          ? "border-foreground bg-foreground text-background"
                          : "border-border",
                      )}
                    >
                      {LETTERS[j]}
                    </span>
                    <span className="whitespace-pre-wrap">{option}</span>
                  </button>
                );
              })}
            </div>
          </li>
        ))}
      </ol>

      <div className="flex flex-wrap items-center gap-3">
        <LineButton variant="solid" onClick={submit} disabled={submitting} className="gap-2">
          {submitting ? <Loader2 size={13} className="animate-spin" /> : <Check size={12} />}
          {confirming ? `Submit with ${unanswered} unanswered` : "Submit & see my score"}
        </LineButton>
        <button
          type="button"
          onClick={onCancel}
          className="text-[11px] text-muted-foreground hover:text-foreground"
        >
          Cancel
        </button>
        {confirming ? (
          <span className="text-[11px] text-muted-foreground">
            Unanswered questions count as wrong.
          </span>
        ) : null}
      </div>
    </div>
  );
}

/* ── Result ───────────────────────────────────────────────────────────────── */

function Result({
  test,
  result,
  onRetake,
  onNew,
}: {
  test: MockTestData;
  result: AttemptResult;
  onRetake: () => void;
  onNew: () => void;
}) {
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-6 rounded-lg border border-border bg-card p-5">
        <div
          className="relative flex h-24 w-24 shrink-0 items-center justify-center rounded-full"
          style={{
            background: `conic-gradient(var(--color-foreground) ${result.percent * 3.6}deg, var(--color-muted) 0deg)`,
          }}
          aria-label={`Score ${result.percent}%`}
        >
          <div className="flex h-20 w-20 flex-col items-center justify-center rounded-full bg-card">
            <span className="text-2xl font-semibold tabular-nums">{result.percent}%</span>
          </div>
        </div>
        <div className="space-y-1">
          <p className="text-sm font-semibold">{result.grade}</p>
          <p className="text-[11px] text-muted-foreground">
            {result.score} of {result.total} correct · {test.role}
            {test.domain ? ` · ${test.domain}` : ""}
          </p>
          <p className="text-[11px] text-muted-foreground">
            Attempt {result.attemptNumber}
            {result.timeTakenSeconds !== null ? ` · ${clock(result.timeTakenSeconds)}` : ""} · best{" "}
            {result.bestPercent}%
          </p>
        </div>
        <div className="ml-auto flex gap-2">
          <LineButton onClick={onRetake} className="gap-1.5 text-xs">
            <RotateCcw size={12} /> Retake
          </LineButton>
          <LineButton variant="solid" onClick={onNew} className="gap-1.5 text-xs">
            <Sparkles size={12} /> New test
          </LineButton>
        </div>
      </div>

      <div>
        <FieldLabel>By topic</FieldLabel>
        <div className="space-y-2">
          {result.topics.map((t) => (
            <div
              key={t.topic}
              className="grid grid-cols-[minmax(0,10rem)_1fr_3rem] items-center gap-3 text-[11px]"
            >
              <span className="truncate">{t.topic}</span>
              <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                <div
                  className={cn(
                    "h-full rounded-full",
                    t.percent < 60 ? "bg-destructive/70" : "bg-foreground/80",
                  )}
                  style={{ width: `${t.percent}%` }}
                />
              </div>
              <span className="text-right tabular-nums text-muted-foreground">
                {t.correct}/{t.total}
              </span>
            </div>
          ))}
        </div>
        {result.weakTopics.length > 0 ? (
          <p className="mt-3 border-l-2 border-border pl-2 text-[11px] leading-relaxed">
            <span className="font-semibold">Focus next on: </span>
            {result.weakTopics.join(", ")}. Your next mock test will revisit them.
          </p>
        ) : null}
      </div>

      <div>
        <FieldLabel>Review</FieldLabel>
        <ol className="space-y-3">
          {result.results.map((r, i) => (
            <li key={r.index} className="rounded-lg border border-border p-4">
              <div className="mb-2 flex items-center gap-2 text-[10px]">
                <span
                  className={cn(
                    "flex h-4 w-4 items-center justify-center rounded-full",
                    r.correct
                      ? "bg-foreground text-background"
                      : "bg-destructive/80 text-background",
                  )}
                >
                  {r.correct ? <Check size={10} /> : <X size={10} />}
                </span>
                <span className="font-semibold tabular-nums">{String(i + 1).padStart(2, "0")}</span>
                <span className="text-muted-foreground">{r.topic}</span>
                {r.yourAnswer === null ? (
                  <span className="text-muted-foreground">· skipped</span>
                ) : null}
              </div>
              <p className="whitespace-pre-wrap text-xs leading-relaxed">{r.question}</p>
              <ul className="mt-2 space-y-1">
                {r.options.map((option, j) => (
                  <li
                    key={option}
                    className={cn(
                      "flex gap-2 rounded px-2 py-1 text-[11px]",
                      j === r.correctAnswer && "bg-foreground/10 font-medium",
                      j === r.yourAnswer && !r.correct && "bg-destructive/10 line-through",
                    )}
                  >
                    <span className="w-3 shrink-0 text-muted-foreground">{LETTERS[j]}</span>
                    <span className="whitespace-pre-wrap">{option}</span>
                  </li>
                ))}
              </ul>
              {r.explanation ? (
                <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">
                  {r.explanation}
                </p>
              ) : null}
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

/* ── Panel ────────────────────────────────────────────────────────────────── */

type Stage =
  | { name: "setup" }
  | { name: "taking"; test: MockTestData; run: number }
  | { name: "result"; test: MockTestData; result: AttemptResult };

export function MockTest() {
  const { authFetch } = useAuth();
  const [stage, setStage] = useState<Stage>({ name: "setup" });
  const [history, setHistory] = useState<MockTestSummary[]>([]);

  const loadHistory = useCallback(() => {
    authFetch<MockTestSummary[]>(API_ENDPOINTS.interview.mockTests)
      .then((response) => setHistory(response.data ?? []))
      .catch(() => undefined);
  }, [authFetch]);
  useEffect(loadHistory, [loadHistory]);

  const take = useCallback(
    async (id: string) => {
      try {
        const response = await authFetch<MockTestData>(API_ENDPOINTS.interview.mockTest(id));
        setStage({ name: "taking", test: response.data, run: Date.now() });
      } catch (err) {
        toast.error(err instanceof ApiRequestError ? err.message : "Couldn't open that test.");
      }
    },
    [authFetch],
  );

  const heading = useMemo(() => {
    if (stage.name === "taking") return "Answer every question, then submit for your score.";
    if (stage.name === "result") return "Scored instantly. Review every answer below.";
    return "A multiple-choice test written for your target role and domain, scored the moment you submit.";
  }, [stage.name]);

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-sm font-medium">Mock test</h2>
        <p className="mt-1 text-[11px] text-muted-foreground">{heading}</p>
      </div>
      {stage.name === "setup" ? (
        <Setup
          history={history}
          onRetake={take}
          onStart={(test) => setStage({ name: "taking", test, run: Date.now() })}
        />
      ) : null}
      {stage.name === "taking" ? (
        <Taking
          key={stage.run}
          test={stage.test}
          onCancel={() => setStage({ name: "setup" })}
          onSubmitted={(result) => {
            setStage({ name: "result", test: stage.test, result });
            loadHistory();
            window.scrollTo({ top: 0, behavior: "smooth" });
          }}
        />
      ) : null}
      {stage.name === "result" ? (
        <Result
          test={stage.test}
          result={stage.result}
          onRetake={() => setStage({ name: "taking", test: stage.test, run: Date.now() })}
          onNew={() => setStage({ name: "setup" })}
        />
      ) : null}
    </section>
  );
}
