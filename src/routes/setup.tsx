import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Sparkle, Target, Layers, Check } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { OutlineIcon } from "@/components/OutlineIcon";
import { LineButton } from "@/components/LineButton";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/setup")({
  head: () => ({
    meta: [
      { title: "Profile Setup — Career Compass" },
      {
        name: "description",
        content: "Tell Career Compass your skills, interests and goals so the agents can begin.",
      },
      { property: "og:title", content: "Profile Setup — Career Compass" },
      {
        property: "og:description",
        content: "A short three-step flow: skills, interests, goals.",
      },
    ],
  }),
  component: Setup,
});

const steps = [
  { key: "skills", label: "Skills", icon: Layers, hint: "What you can already do well." },
  { key: "interests", label: "Interests", icon: Sparkle, hint: "What keeps your attention." },
  { key: "goals", label: "Goals", icon: Target, hint: "Where you want to be in 12 months." },
] as const;

const suggestions: Record<string, string[]> = {
  skills: ["TypeScript", "Python", "System design", "SQL", "Figma", "Data modelling"],
  interests: ["Infrastructure", "AI tooling", "Fintech", "Design systems", "Climate", "Robotics"],
  goals: ["Senior engineer", "Switch to ML", "Remote role", "Team lead", "Higher comp", "FAANG"],
};

function Setup() {
  const [step, setStep] = useState(0);
  const [selected, setSelected] = useState<Record<string, string[]>>({
    skills: ["TypeScript"],
    interests: [],
    goals: [],
  });
  const [draft, setDraft] = useState("");
  const navigate = useNavigate();
  const key = steps[step].key;

  const toggle = (tag: string) =>
    setSelected((s) => ({
      ...s,
      [key]: s[key].includes(tag) ? s[key].filter((t) => t !== tag) : [...s[key], tag],
    }));

  return (
    <AppShell>
      <div className="mx-auto max-w-2xl">
        <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Profile setup</p>
        <h1 className="mt-3 text-2xl font-medium tracking-tight">
          Give the agents something to work with
        </h1>

        <ol className="mt-10 flex items-center">
          {steps.map((s, i) => (
            <li key={s.key} className="flex flex-1 items-center last:flex-none">
              <button
                onClick={() => setStep(i)}
                className="group flex items-center gap-3 text-left"
              >
                <span
                  className={cn(
                    "flex h-9 w-9 items-center justify-center rounded-full border transition-colors duration-300",
                    i === step ? "border-ink text-ink" : "border-border text-muted-foreground",
                  )}
                >
                  <OutlineIcon icon={i < step ? Check : s.icon} size={16} />
                </span>
                <span
                  className={cn(
                    "text-sm transition-colors duration-300",
                    i === step ? "text-foreground" : "text-muted-foreground group-hover:text-ink",
                  )}
                >
                  {s.label}
                </span>
              </button>
              {i < steps.length - 1 && <span className="mx-4 h-px flex-1 bg-border" />}
            </li>
          ))}
        </ol>

        <section key={key} className="rise-in mt-12">
          <h2 className="text-sm font-medium">{steps[step].label}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{steps[step].hint}</p>

          <form
            className="mt-6"
            onSubmit={(e) => {
              e.preventDefault();
              const v = draft.trim();
              if (!v) return;
              setSelected((s) => ({ ...s, [key]: [...s[key], v] }));
              setDraft("");
            }}
          >
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={`Add a ${steps[step].label.toLowerCase().replace(/s$/, "")} and press Enter`}
              className="w-full border-b border-border bg-transparent pb-2 text-sm outline-none transition-colors duration-300 placeholder:text-muted-foreground/60 focus:border-ink"
            />
          </form>

          <div className="mt-6 flex flex-wrap gap-2">
            {[...new Set([...suggestions[key], ...selected[key]])].map((tag) => {
              const on = selected[key].includes(tag);
              return (
                <button
                  key={tag}
                  onClick={() => toggle(tag)}
                  className={cn(
                    "rounded-full border px-3 py-1.5 text-sm transition-colors duration-300 [transition-timing-function:cubic-bezier(0.65,0,0.35,1)]",
                    on
                      ? "border-ink text-ink"
                      : "border-border text-muted-foreground hover:border-border-strong hover:text-foreground",
                  )}
                >
                  {tag}
                </button>
              );
            })}
          </div>
        </section>

        <div className="mt-14 flex items-center justify-between border-t border-border pt-6">
          <LineButton
            variant="ghost"
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            disabled={step === 0}
          >
            Back
          </LineButton>
          <LineButton
            variant={step === steps.length - 1 ? "solid" : "outline"}
            onClick={() =>
              step === steps.length - 1
                ? navigate({ to: "/dashboard" })
                : setStep((s) => s + 1)
            }
          >
            {step === steps.length - 1 ? "Activate agents" : "Continue"}
          </LineButton>
        </div>
      </div>
    </AppShell>
  );
}
