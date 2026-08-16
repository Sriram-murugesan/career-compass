import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { UserRound } from "lucide-react";
import { OutlineIcon } from "@/components/OutlineIcon";
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

function Field({
  label,
  type = "text",
  placeholder,
  value,
  onChange,
}: {
  label: string;
  type?: string;
  placeholder?: string;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
}) {
  return (
    <label className="group block">
      <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">{label}</span>
      <input
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        className="mt-2 w-full border-b border-border bg-transparent pb-2 text-sm outline-none placeholder:text-muted-foreground/60 focus:border-ink"
        style={{ transition: "border-color 300ms cubic-bezier(0.65,0,0.35,1)" }}
      />
    </label>
  );
}

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
    <div className="flex min-h-screen items-center justify-center px-6">
      <div className="rise-in w-full max-w-sm">
        <div className="mb-10 flex items-center gap-3">
          <span className="rounded-full border border-border p-2">
            <OutlineIcon icon={UserRound} size={18} />
          </span>
          <div>
            <h1 className="text-lg font-medium tracking-tight">Career Compass</h1>
            <p className="text-xs text-muted-foreground">
              Seven agents. One deliberate career path.
            </p>
          </div>
        </div>

        <div className="mb-8 flex gap-6 text-sm">
          {(["in", "up"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={
                "relative pb-1 transition-colors duration-300 " +
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

        <form className="space-y-7" onSubmit={handleSubmit}>
          {mode === "up" && (
            <Field
              label="Full name"
              placeholder="Ada Lovelace"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          )}
          <Field
            label="Email"
            type="email"
            placeholder="you@domain.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Field
            label="Password"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <LineButton type="submit" className="w-full">
            {mode === "in" ? "Continue" : "Start profile setup"}
          </LineButton>
        </form>

        <p className="mt-8 text-xs text-muted-foreground">
          Skip ahead to the{" "}
          <Link to="/dashboard" className="text-ink underline underline-offset-4">
            agent dashboard
          </Link>
          .
        </p>
      </div>
    </div>
  );
}
