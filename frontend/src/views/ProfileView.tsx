"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import {
  User,
  Mail,
  MapPin,
  Briefcase,
  DollarSign,
  Sparkles,
  FileText,
  Upload,
  Edit3,
  Plus,
  Trash2,
  Layers,
  Target,
  Bot,
  Sliders,
  Compass,
  Activity,
  Eye,
  ShieldCheck,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { OutlineIcon } from "@/components/OutlineIcon";
import { LineButton } from "@/components/LineButton";
import { useUserProfile, type TailoredResumeItem } from "@/context/UserProfileContext";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";

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

export function ProfilePage() {
  const {
    profile,
    updateProfile,
    addSkill,
    removeSkill,
    uploadResumeSimulated,
    deleteTailoredResume,
    completionPercentage,
  } = useUserProfile();

  const router = useRouter();
  const [activeTab, setActiveTab] = useState<
    "overview" | "skills" | "goals" | "resume" | "activity" | "agent_settings"
  >("overview");

  const [selectedResumeModal, setSelectedResumeModal] = useState<TailoredResumeItem | null>(null);

  // Edit Profile Modal State
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editForm, setEditForm] = useState({
    name: profile.name,
    email: profile.email,
    title: profile.title,
    bio: profile.bio,
    location: profile.location,
    targetSalary: profile.targetSalary,
    workPreference: profile.workPreference,
    experienceLevel: profile.experienceLevel,
  });

  // Add Skill Modal State
  const [isAddSkillOpen, setIsAddSkillOpen] = useState(false);
  const [newSkillName, setNewSkillName] = useState("");
  const [newSkillCategory, setNewSkillCategory] = useState<"Technical" | "Soft Skills" | "Tools">(
    "Technical",
  );
  const [newSkillLevel, setNewSkillLevel] = useState<
    "Beginner" | "Intermediate" | "Advanced" | "Expert"
  >("Advanced");

  // Add Goal & Interest State
  const [newGoalText, setNewGoalText] = useState("");
  const [newInterestText, setNewInterestText] = useState("");

  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault();
    updateProfile(editForm);
    setIsEditOpen(false);
    toast.success("Profile details updated.");
  };

  const handleAddSkillSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSkillName.trim()) return;
    addSkill({
      name: newSkillName.trim(),
      category: newSkillCategory,
      level: newSkillLevel,
    });
    setNewSkillName("");
    setIsAddSkillOpen(false);
    toast.success(`Skill "${newSkillName}" added.`);
  };

  const handleAddGoal = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newGoalText.trim()) return;
    updateProfile({ goals: [...profile.goals, newGoalText.trim()] });
    setNewGoalText("");
    toast.success("Goal added.");
  };

  const handleAddInterest = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newInterestText.trim()) return;
    updateProfile({ interests: [...profile.interests, newInterestText.trim()] });
    setNewInterestText("");
    toast.success("Interest added.");
  };

  const tabs = [
    { id: "overview", label: "Overview & Target", icon: Briefcase },
    { id: "skills", label: `Skills (${profile.skills.length})`, icon: Layers },
    { id: "goals", label: `Interests & Goals (${profile.goals.length})`, icon: Target },
    { id: "resume", label: "Resume & ATS Intelligence", icon: FileText },
    {
      id: "activity",
      label: `Activity & Resumes (${(profile.tailoredResumes || []).length})`,
      icon: Activity,
    },
    { id: "agent_settings", label: "AI Agent Context", icon: Sliders },
  ] as const;

  return (
    <AppShell>
      <div className="space-y-10">
        {/* Top Header */}
        <header className="flex flex-col md:flex-row md:items-start md:justify-between gap-6">
          <div className="max-w-xl">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
              User Profile
            </p>
            <h1
              className="mt-3 text-2xl font-medium tracking-tight"
              style={{ fontFamily: "var(--font-display)" }}
            >
              {profile.name}
            </h1>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              {profile.title} · {profile.location} · {profile.workPreference}
            </p>
            {profile.bio && (
              <p className="mt-3 text-xs leading-relaxed text-muted-foreground">{profile.bio}</p>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-3 self-start">
            <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
              <DialogTrigger asChild>
                <LineButton variant="outline" className="gap-2 text-xs">
                  <OutlineIcon icon={Edit3} size={15} />
                  Edit Profile
                </LineButton>
              </DialogTrigger>
              <DialogContent className="max-w-lg">
                <DialogHeader>
                  <DialogTitle className="text-base font-medium">
                    Edit Profile Information
                  </DialogTitle>
                </DialogHeader>
                <form onSubmit={handleSaveProfile} className="space-y-5 py-2">
                  <div>
                    <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                      Full Name
                    </span>
                    <input
                      type="text"
                      value={editForm.name}
                      onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                      className="mt-2 w-full border-b border-border bg-transparent pb-2 text-sm outline-none focus:border-ink"
                      required
                    />
                  </div>
                  <div>
                    <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                      Professional Title
                    </span>
                    <input
                      type="text"
                      value={editForm.title}
                      onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                      className="mt-2 w-full border-b border-border bg-transparent pb-2 text-sm outline-none focus:border-ink"
                      required
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                        Email
                      </span>
                      <input
                        type="email"
                        value={editForm.email}
                        onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                        className="mt-2 w-full border-b border-border bg-transparent pb-2 text-sm outline-none focus:border-ink"
                      />
                    </div>
                    <div>
                      <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                        Location
                      </span>
                      <input
                        type="text"
                        value={editForm.location}
                        onChange={(e) => setEditForm({ ...editForm, location: e.target.value })}
                        className="mt-2 w-full border-b border-border bg-transparent pb-2 text-sm outline-none focus:border-ink"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                        Target Salary
                      </span>
                      <input
                        type="text"
                        value={editForm.targetSalary}
                        onChange={(e) => setEditForm({ ...editForm, targetSalary: e.target.value })}
                        className="mt-2 w-full border-b border-border bg-transparent pb-2 text-sm outline-none focus:border-ink"
                      />
                    </div>
                    <div>
                      <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                        Work Preference
                      </span>
                      <select
                        value={editForm.workPreference}
                        onChange={(e) =>
                          setEditForm({
                            ...editForm,
                            workPreference: e.target.value as "Remote" | "Hybrid" | "Onsite",
                          })
                        }
                        className="mt-2 w-full border-b border-border bg-transparent pb-2 text-sm outline-none focus:border-ink"
                      >
                        <option value="Remote">Remote</option>
                        <option value="Hybrid">Hybrid</option>
                        <option value="Onsite">Onsite</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                      Bio
                    </span>
                    <textarea
                      rows={2}
                      value={editForm.bio}
                      onChange={(e) => setEditForm({ ...editForm, bio: e.target.value })}
                      className="mt-2 w-full border-b border-border bg-transparent pb-2 text-sm outline-none focus:border-ink"
                    />
                  </div>
                  <DialogFooter className="pt-2">
                    <LineButton type="submit" variant="solid">
                      Save Changes
                    </LineButton>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>

            <LineButton
              variant="ghost"
              className="gap-2 text-xs"
              onClick={() => router.push("/setup")}
            >
              <OutlineIcon icon={Compass} size={15} />
              Setup Wizard
            </LineButton>
          </div>
        </header>

        {/* Minimal Progress Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Profile Sync &amp; Agent Context</span>
            <span className="tabular-nums">{completionPercentage}%</span>
          </div>
          <div className="h-px w-full bg-border">
            <div
              className="h-px bg-ink transition-all duration-500"
              style={{ width: `${completionPercentage}%` }}
            />
          </div>
        </div>

        {/* 4 Minimal Metric Highlight Cards */}
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rise-in group relative flex flex-col justify-between rounded-lg border border-border bg-background p-5 transition-colors duration-300 [transition-timing-function:cubic-bezier(0.65,0,0.35,1)] hover:border-ink">
            <div className="flex items-start justify-between">
              <OutlineIcon icon={FileText} size={22} />
              <span className="text-[11px] tabular-nums text-muted-foreground">01</span>
            </div>
            <div className="mt-8">
              <h3 className="text-sm font-medium">{profile.resume?.atsScore ?? 92}% ATS Match</h3>
              <p className="mt-1 text-xs text-muted-foreground truncate">
                {profile.resume?.fileName || "Resume uploaded"}
              </p>
            </div>
          </div>

          <div
            className="rise-in group relative flex flex-col justify-between rounded-lg border border-border bg-background p-5 transition-colors duration-300 [transition-timing-function:cubic-bezier(0.65,0,0.35,1)] hover:border-ink"
            style={{ animationDelay: "45ms" }}
          >
            <div className="flex items-start justify-between">
              <OutlineIcon icon={Layers} size={22} />
              <span className="text-[11px] tabular-nums text-muted-foreground">02</span>
            </div>
            <div className="mt-8">
              <h3 className="text-sm font-medium">{profile.skills.length} Verified Skills</h3>
              <p className="mt-1 text-xs text-muted-foreground">
                {profile.skills.filter((s) => s.level === "Expert").length} Expert ·{" "}
                {profile.skills.filter((s) => s.level === "Advanced").length} Advanced
              </p>
            </div>
          </div>

          <div
            className="rise-in group relative flex flex-col justify-between rounded-lg border border-border bg-background p-5 transition-colors duration-300 [transition-timing-function:cubic-bezier(0.65,0,0.35,1)] hover:border-ink"
            style={{ animationDelay: "90ms" }}
          >
            <div className="flex items-start justify-between">
              <OutlineIcon icon={Briefcase} size={22} />
              <span className="text-[11px] tabular-nums text-muted-foreground">03</span>
            </div>
            <div className="mt-8">
              <h3 className="text-sm font-medium">
                {(profile.tailoredResumes || []).length} Tailored Resumes
              </h3>
              <p className="mt-1 text-xs text-muted-foreground truncate">
                Latest: {profile.tailoredResumes?.[0]?.company || "Kepler Systems"}
              </p>
            </div>
          </div>

          <div
            className="rise-in group relative flex flex-col justify-between rounded-lg border border-border bg-background p-5 transition-colors duration-300 [transition-timing-function:cubic-bezier(0.65,0,0.35,1)] hover:border-ink"
            style={{ animationDelay: "135ms" }}
          >
            <div className="flex items-start justify-between">
              <OutlineIcon icon={Activity} size={22} />
              <span className="text-[11px] tabular-nums text-muted-foreground">04</span>
            </div>
            <div className="mt-8">
              <h3 className="text-sm font-medium">
                {(profile.activities || []).length} Agent Actions
              </h3>
              <p className="mt-1 text-xs text-muted-foreground">
                Tone: {profile.aiPreferences?.tone || "Ambitious"}
              </p>
            </div>
          </div>
        </section>

        {/* Minimal Tab Bar */}
        <section className="space-y-6">
          <div className="flex border-b border-border text-sm overflow-x-auto scrollbar-none gap-6">
            {tabs.map((t) => (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id as typeof activeTab)}
                className={cn(
                  "relative pb-3 transition-colors duration-300 text-sm font-medium whitespace-nowrap",
                  activeTab === t.id ? "text-foreground" : "text-muted-foreground hover:text-ink",
                )}
              >
                <span className="flex items-center gap-2">
                  <OutlineIcon icon={t.icon} size={16} />
                  {t.label}
                </span>
                <span
                  className={cn(
                    "absolute inset-x-0 bottom-0 h-px origin-left bg-ink transition-transform duration-[320ms] [transition-timing-function:cubic-bezier(0.65,0,0.35,1)]",
                    activeTab === t.id ? "scale-x-100" : "scale-x-0",
                  )}
                />
              </button>
            ))}
          </div>

          {/* TAB 1: OVERVIEW */}
          {activeTab === "overview" && (
            <div className="rise-in grid gap-6 md:grid-cols-2">
              <Panel title="Target Role Criteria" aside="Updated dynamically">
                <div className="space-y-4 text-sm">
                  <div>
                    <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                      Current Title
                    </span>
                    <p className="mt-1 font-medium">{profile.title}</p>
                  </div>
                  <div>
                    <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                      Target Titles
                    </span>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {profile.targetRoles.map((r) => (
                        <span
                          key={r}
                          className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground"
                        >
                          {r}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4 pt-2">
                    <div>
                      <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                        Target Compensation
                      </span>
                      <p className="mt-1 font-medium">{profile.targetSalary}</p>
                    </div>
                    <div>
                      <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                        Location
                      </span>
                      <p className="mt-1 font-medium">{profile.location}</p>
                    </div>
                  </div>
                </div>
              </Panel>

              <Panel title="AI Agent Pipeline Alignment" aside="7 agents active">
                <p className="text-xs leading-relaxed text-muted-foreground">
                  Your profile details sequence outputs across the entire pipeline:
                </p>
                <ul className="mt-4 space-y-3 text-xs text-muted-foreground">
                  <li className="flex items-center gap-2">
                    <span className="h-1 w-1 rounded-full bg-ink" />
                    <span>
                      <strong className="text-foreground">Resume Agent:</strong> Drafts ATS bullet
                      points tailored for {profile.title}.
                    </span>
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="h-1 w-1 rounded-full bg-ink" />
                    <span>
                      <strong className="text-foreground">Job Search Agent:</strong> Filters roles
                      matching {profile.targetSalary}.
                    </span>
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="h-1 w-1 rounded-full bg-ink" />
                    <span>
                      <strong className="text-foreground">Interview Agent:</strong> Prepares system
                      design mock loops.
                    </span>
                  </li>
                </ul>
                <div className="mt-6 pt-4 border-t border-border">
                  <LineButton
                    variant="solid"
                    onClick={() => router.push("/dashboard")}
                    className="w-full text-xs"
                  >
                    View All Agents
                  </LineButton>
                </div>
              </Panel>
            </div>
          )}

          {/* TAB 2: SKILLS */}
          {activeTab === "skills" && (
            <div className="rise-in space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-medium">Verified Skills</h3>
                  <p className="text-xs text-muted-foreground">
                    Categorized skills used for ATS matching and interview evaluation.
                  </p>
                </div>

                <Dialog open={isAddSkillOpen} onOpenChange={setIsAddSkillOpen}>
                  <DialogTrigger asChild>
                    <LineButton variant="outline" className="gap-1.5 text-xs">
                      <OutlineIcon icon={Plus} size={15} /> Add Skill
                    </LineButton>
                  </DialogTrigger>
                  <DialogContent className="max-w-md">
                    <DialogHeader>
                      <DialogTitle className="text-base font-medium">Add Skill</DialogTitle>
                    </DialogHeader>
                    <form onSubmit={handleAddSkillSubmit} className="space-y-4 py-2">
                      <div>
                        <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                          Skill Name
                        </span>
                        <input
                          type="text"
                          placeholder="e.g. React, Next.js, System Architecture"
                          value={newSkillName}
                          onChange={(e) => setNewSkillName(e.target.value)}
                          className="mt-2 w-full border-b border-border bg-transparent pb-2 text-sm outline-none focus:border-ink"
                          required
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                            Category
                          </span>
                          <select
                            value={newSkillCategory}
                            onChange={(e) =>
                              setNewSkillCategory(
                                e.target.value as "Technical" | "Soft Skills" | "Tools",
                              )
                            }
                            className="mt-2 w-full border-b border-border bg-transparent pb-2 text-sm outline-none focus:border-ink"
                          >
                            <option value="Technical">Technical</option>
                            <option value="Tools">Tools</option>
                            <option value="Soft Skills">Soft Skills</option>
                          </select>
                        </div>
                        <div>
                          <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                            Level
                          </span>
                          <select
                            value={newSkillLevel}
                            onChange={(e) =>
                              setNewSkillLevel(
                                e.target.value as
                                  "Beginner" | "Intermediate" | "Advanced" | "Expert",
                              )
                            }
                            className="mt-2 w-full border-b border-border bg-transparent pb-2 text-sm outline-none focus:border-ink"
                          >
                            <option value="Beginner">Beginner</option>
                            <option value="Intermediate">Intermediate</option>
                            <option value="Advanced">Advanced</option>
                            <option value="Expert">Expert</option>
                          </select>
                        </div>
                      </div>
                      <DialogFooter className="pt-2">
                        <LineButton type="submit" variant="solid">
                          Add Skill
                        </LineButton>
                      </DialogFooter>
                    </form>
                  </DialogContent>
                </Dialog>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {profile.skills.map((skill) => (
                  <div
                    key={skill.name}
                    className="group flex items-center justify-between rounded-lg border border-border p-4 transition-colors duration-300 hover:border-ink"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">{skill.name}</span>
                        <span className="text-[10px] text-muted-foreground">
                          · {skill.category}
                        </span>
                      </div>
                      <span className="mt-1 block text-xs text-muted-foreground">
                        {skill.level}
                      </span>
                    </div>

                    <button
                      onClick={() => {
                        removeSkill(skill.name);
                        toast.info(`Removed skill "${skill.name}".`);
                      }}
                      className="text-muted-foreground/50 transition-colors hover:text-foreground"
                      title="Remove skill"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 3: INTERESTS & GOALS */}
          {activeTab === "goals" && (
            <div className="rise-in grid gap-6 md:grid-cols-2">
              <Panel title="12-Month Goals" aside={`${profile.goals.length} goals`}>
                <form onSubmit={handleAddGoal} className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Add goal and press Enter"
                    value={newGoalText}
                    onChange={(e) => setNewGoalText(e.target.value)}
                    className="w-full border-b border-border bg-transparent pb-2 text-xs outline-none focus:border-ink"
                  />
                </form>
                <ul className="mt-5 space-y-3">
                  {profile.goals.map((goal, idx) => (
                    <li
                      key={goal}
                      className="group flex items-center justify-between rounded-md border border-border p-3 text-xs"
                    >
                      <span className="text-muted-foreground">
                        {String(idx + 1).padStart(2, "0")} ·{" "}
                        <strong className="text-foreground font-medium">{goal}</strong>
                      </span>
                      <button
                        onClick={() => {
                          updateProfile({ goals: profile.goals.filter((g) => g !== goal) });
                          toast.info("Goal removed.");
                        }}
                        className="text-muted-foreground/60 hover:text-foreground"
                      >
                        <Trash2 size={13} />
                      </button>
                    </li>
                  ))}
                </ul>
              </Panel>

              <Panel
                title="Focus Areas &amp; Interests"
                aside={`${profile.interests.length} areas`}
              >
                <form onSubmit={handleAddInterest} className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Add focus area and press Enter"
                    value={newInterestText}
                    onChange={(e) => setNewInterestText(e.target.value)}
                    className="w-full border-b border-border bg-transparent pb-2 text-xs outline-none focus:border-ink"
                  />
                </form>
                <div className="mt-5 flex flex-wrap gap-2">
                  {profile.interests.map((interest) => (
                    <span
                      key={interest}
                      className="group inline-flex items-center gap-2 rounded-full border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors duration-300 hover:border-ink hover:text-foreground"
                    >
                      {interest}
                      <button
                        onClick={() => {
                          updateProfile({
                            interests: profile.interests.filter((i) => i !== interest),
                          });
                          toast.info("Interest removed.");
                        }}
                        className="text-muted-foreground/60 hover:text-foreground"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              </Panel>
            </div>
          )}

          {/* TAB 4: RESUME & ATS INTELLIGENCE */}
          {activeTab === "resume" && (
            <div className="rise-in space-y-6">
              <Panel
                title="Active Resume Document"
                aside={`ATS Score: ${profile.resume?.atsScore}%`}
              >
                <div className="space-y-5">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                    <div>
                      <p className="text-sm font-medium">{profile.resume?.fileName}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Uploaded on {profile.resume?.uploadedAt} ·{" "}
                        {profile.resume?.parsedSkillsCount} skills parsed
                      </p>
                    </div>
                    <LineButton
                      variant="outline"
                      className="gap-2 text-xs"
                      onClick={() => {
                        uploadResumeSimulated(`${profile.name.replace(/\s+/g, "_")}_CV_2026.pdf`);
                        toast.success("Resume updated & parsed!");
                      }}
                    >
                      <OutlineIcon icon={Upload} size={14} /> Re-parse Resume
                    </LineButton>
                  </div>

                  <div className="border-t border-border pt-4 space-y-3">
                    <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                      ATS Parser Breakdown
                    </p>
                    <div className="space-y-2 text-xs">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Keyword Density</span>
                        <span className="tabular-nums font-medium">95%</span>
                      </div>
                      <div className="h-px w-full bg-border">
                        <div className="h-px bg-ink" style={{ width: "95%" }} />
                      </div>

                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Formatting Structure</span>
                        <span className="tabular-nums font-medium">92%</span>
                      </div>
                      <div className="h-px w-full bg-border">
                        <div className="h-px bg-ink" style={{ width: "92%" }} />
                      </div>

                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Measurable Impact</span>
                        <span className="tabular-nums font-medium">88%</span>
                      </div>
                      <div className="h-px w-full bg-border">
                        <div className="h-px bg-ink" style={{ width: "88%" }} />
                      </div>
                    </div>
                  </div>
                </div>
              </Panel>
            </div>
          )}

          {/* TAB 5: ACTIVITY HISTORY & TAILORED RESUMES */}
          {activeTab === "activity" && (
            <div className="rise-in grid gap-6 md:grid-cols-12">
              {/* Saved Resumes (7 cols) */}
              <div className="md:col-span-7 space-y-4">
                <Panel
                  title="Saved Job-Tailored Resumes"
                  aside={`${(profile.tailoredResumes || []).length} versions`}
                >
                  <div className="space-y-3">
                    {(profile.tailoredResumes || []).length === 0 ? (
                      <p className="text-xs text-muted-foreground italic">
                        No tailored resumes generated yet.
                      </p>
                    ) : (
                      profile.tailoredResumes.map((tres) => (
                        <div
                          key={tres.id}
                          className="group rounded-lg border border-border p-4 transition-colors duration-300 hover:border-ink space-y-2"
                        >
                          <div className="flex items-start justify-between">
                            <div>
                              <div className="flex items-center gap-2">
                                <h4 className="text-sm font-medium">{tres.jobTitle}</h4>
                                <span className="text-xs tabular-nums text-muted-foreground">
                                  ({tres.atsScore}% ATS)
                                </span>
                              </div>
                              <p className="text-xs text-muted-foreground mt-0.5">
                                {tres.company} · {tres.createdAt}
                              </p>
                            </div>
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => setSelectedResumeModal(tres)}
                                className="text-muted-foreground hover:text-ink transition-colors"
                                title="View Tailored Resume"
                              >
                                <OutlineIcon icon={Eye} size={15} />
                              </button>
                              <button
                                onClick={() => {
                                  deleteTailoredResume(tres.id);
                                  toast.info(`Deleted resume for ${tres.company}.`);
                                }}
                                className="text-muted-foreground/50 hover:text-foreground transition-colors"
                                title="Delete"
                              >
                                <Trash2 size={14} />
                              </button>
                            </div>
                          </div>
                          <div className="flex flex-wrap gap-1.5 pt-1">
                            {tres.matchedKeywords.map((kw) => (
                              <span
                                key={kw}
                                className="rounded-full border border-border px-2 py-0.5 text-[10px] text-muted-foreground"
                              >
                                {kw}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </Panel>
              </div>

              {/* Activity Feed (5 cols) */}
              <div className="md:col-span-5">
                <Panel title="Agent Activity Log" aside="Real-time stream">
                  <ol className="relative border-l border-border pl-4 space-y-5 text-xs">
                    {(profile.activities || []).map((act) => (
                      <li key={act.id} className="relative">
                        <span className="absolute -left-[21px] top-1 h-2 w-2 rounded-full border border-ink bg-background" />
                        <p className="font-medium text-foreground">{act.title}</p>
                        <p className="mt-0.5 text-[11px] text-muted-foreground">{act.details}</p>
                        <span className="mt-1 block text-[10px] text-muted-foreground">
                          {act.timestamp}
                        </span>
                      </li>
                    ))}
                  </ol>
                </Panel>
              </div>
            </div>
          )}

          {/* TAB 6: AI SETTINGS */}
          {activeTab === "agent_settings" && (
            <div className="rise-in">
              <Panel title="AI Agent Settings" aside="Applies to all 7 agents">
                <div className="space-y-6 max-w-xl">
                  <div>
                    <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                      Response Tone
                    </span>
                    <div className="mt-3 flex gap-3 text-xs">
                      {(["Professional", "Concise", "Ambitious"] as const).map((t) => (
                        <button
                          key={t}
                          type="button"
                          onClick={() =>
                            updateProfile({
                              aiPreferences: { ...profile.aiPreferences, tone: t },
                            })
                          }
                          className={cn(
                            "rounded-md border px-4 py-2 text-xs font-medium transition-colors duration-300",
                            profile.aiPreferences?.tone === t
                              ? "border-ink text-foreground font-semibold"
                              : "border-border text-muted-foreground hover:text-foreground",
                          )}
                        >
                          {t}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                      Custom Instructions
                    </span>
                    <textarea
                      rows={3}
                      value={profile.aiPreferences?.focusArea || ""}
                      onChange={(e) =>
                        updateProfile({
                          aiPreferences: { ...profile.aiPreferences, focusArea: e.target.value },
                        })
                      }
                      placeholder="Special instructions for agents..."
                      className="mt-2 w-full border-b border-border bg-transparent pb-2 text-xs outline-none focus:border-ink"
                    />
                  </div>

                  <div>
                    <LineButton
                      variant="solid"
                      onClick={() => toast.success("AI preferences saved.")}
                    >
                      Save Preferences
                    </LineButton>
                  </div>
                </div>
              </Panel>
            </div>
          )}
        </section>

        {/* Tailored Resume View Modal */}
        {selectedResumeModal && (
          <Dialog open={!!selectedResumeModal} onOpenChange={() => setSelectedResumeModal(null)}>
            <DialogContent className="max-w-xl">
              <DialogHeader>
                <DialogTitle className="text-base font-medium">
                  {selectedResumeModal.jobTitle} — {selectedResumeModal.company}
                </DialogTitle>
                <p className="text-xs text-muted-foreground">
                  {selectedResumeModal.atsScore}% ATS Match · Created{" "}
                  {selectedResumeModal.createdAt}
                </p>
              </DialogHeader>

              <div className="space-y-4 py-2 text-xs leading-relaxed">
                <div>
                  <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                    Summary
                  </p>
                  <p className="mt-1 text-muted-foreground">{selectedResumeModal.summary}</p>
                </div>

                <div>
                  <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                    Tailored Experience Bullets
                  </p>
                  <ul className="mt-2 space-y-1.5 text-muted-foreground">
                    {selectedResumeModal.bullets.map((b, i) => (
                      <li key={i}>— {b}</li>
                    ))}
                  </ul>
                </div>
              </div>

              <DialogFooter>
                <LineButton
                  variant="solid"
                  onClick={() => setSelectedResumeModal(null)}
                  className="text-xs"
                >
                  Close
                </LineButton>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </div>
    </AppShell>
  );
}
