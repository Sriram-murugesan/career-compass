"use client";

/**
 * The signed-in user's career profile — real data only.
 *
 * - Name and email come from the account (AuthContext).
 * - Everything else is loaded from GET /api/profile and saved with PATCH /api/profile.
 * - Activity history and saved tailored resumes have no backend endpoints yet;
 *   they start empty and are kept in this browser, per user, until those
 *   endpoints exist.
 */

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { API_ENDPOINTS } from "@/lib/api";

export interface SkillItem {
  name: string;
  category: "Technical" | "Soft Skills" | "Tools";
  level: "Beginner" | "Intermediate" | "Advanced" | "Expert";
}

export interface ActivityItem {
  id: string;
  type: "resume_generated" | "job_searched" | "profile_updated" | "interview_practiced";
  title: string;
  timestamp: string;
  details?: string | undefined;
  targetCompany?: string | undefined;
  atsScore?: number | undefined;
}

export interface TailoredResumeItem {
  id: string;
  jobTitle: string;
  company: string;
  location: string;
  createdAt: string;
  atsScore: number | null;
  matchedKeywords: string[];
  summary: string;
  bullets: string[];
}

export type WorkPreference = "Remote" | "Hybrid" | "Onsite" | "";

export interface AiPreferences {
  tone: "Professional" | "Concise" | "Ambitious";
  focusArea: string;
  autoRunAgents: boolean;
}

export interface UserProfile {
  name: string;
  email: string;
  title: string;
  bio: string;
  location: string;
  experienceLevel: string;
  targetRoles: string[];
  targetSalary: string;
  workPreference: WorkPreference;
  skills: SkillItem[];
  interests: string[];
  goals: string[];
  aiPreferences: AiPreferences;
  activities: ActivityItem[];
  tailoredResumes: TailoredResumeItem[];
}

/** The backend's profile shape (GET/PATCH /api/profile). */
interface ApiProfile {
  headline: string;
  bio: string;
  location: string;
  targetSalary: string;
  workPreference: WorkPreference;
  experienceLevel: string;
  targetRoles: string[];
  skills: SkillItem[];
  interests: string[];
  goals: string[];
  aiPreferences: AiPreferences;
}

const EMPTY_PROFILE: UserProfile = {
  name: "",
  email: "",
  title: "",
  bio: "",
  location: "",
  experienceLevel: "",
  targetRoles: [],
  targetSalary: "",
  workPreference: "",
  skills: [],
  interests: [],
  goals: [],
  aiPreferences: { tone: "Professional", focusArea: "", autoRunAgents: true },
  activities: [],
  tailoredResumes: [],
};

interface UserProfileContextType {
  profile: UserProfile;
  updateProfile: (updates: Partial<UserProfile>) => void;
  addSkill: (skill: SkillItem) => void;
  removeSkill: (skillName: string) => void;
  updateSkills: (skills: SkillItem[]) => void;
  updateInterests: (interests: string[]) => void;
  updateGoals: (goals: string[]) => void;
  logActivity: (activity: Omit<ActivityItem, "id" | "timestamp">) => void;
  saveTailoredResume: (resume: Omit<TailoredResumeItem, "id" | "createdAt">) => void;
  deleteTailoredResume: (id: string) => void;
  completionPercentage: number;
  /** False until the profile has been loaded from the API. */
  isHydrated: boolean;
}

const UserProfileContext = createContext<UserProfileContextType | undefined>(undefined);

const localKey = (userId: string) => `career_compass_local_${userId}`;

function fromApi(api: ApiProfile): Partial<UserProfile> {
  return {
    title: api.headline,
    bio: api.bio,
    location: api.location,
    targetSalary: api.targetSalary,
    workPreference: api.workPreference,
    experienceLevel: api.experienceLevel,
    targetRoles: api.targetRoles,
    skills: api.skills,
    interests: api.interests,
    goals: api.goals,
    aiPreferences: api.aiPreferences,
  };
}

/** Only fields the backend stores are sent; name/email belong to the account. */
function toApi(updates: Partial<UserProfile>): Partial<ApiProfile> {
  const body: Partial<ApiProfile> = {};
  if (updates.title !== undefined) body.headline = updates.title;
  if (updates.bio !== undefined) body.bio = updates.bio;
  if (updates.location !== undefined) body.location = updates.location;
  if (updates.targetSalary !== undefined) body.targetSalary = updates.targetSalary;
  if (updates.workPreference !== undefined) body.workPreference = updates.workPreference;
  if (updates.experienceLevel !== undefined) body.experienceLevel = updates.experienceLevel;
  if (updates.targetRoles !== undefined) body.targetRoles = updates.targetRoles;
  if (updates.skills !== undefined) body.skills = updates.skills;
  if (updates.interests !== undefined) body.interests = updates.interests;
  if (updates.goals !== undefined) body.goals = updates.goals;
  if (updates.aiPreferences !== undefined) body.aiPreferences = updates.aiPreferences;
  return body;
}

export const UserProfileProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, authFetch } = useAuth();
  const [profile, setProfile] = useState<UserProfile>(EMPTY_PROFILE);
  const [isHydrated, setIsHydrated] = useState(false);

  // Load (or clear) the profile when the signed-in ACCOUNT changes — not on every token
  // refresh (that yields a new user object for the same account and would discard edits).
  const userId = user?.id ?? null;
  useEffect(() => {
    if (!userId) {
      setProfile(EMPTY_PROFILE);
      setIsHydrated(false);
      return;
    }
    let active = true;
    let local: Pick<UserProfile, "activities" | "tailoredResumes"> = {
      activities: [],
      tailoredResumes: [],
    };
    try {
      const saved = localStorage.getItem(localKey(userId));
      if (saved) local = { ...local, ...JSON.parse(saved) };
    } catch {
      // Unreadable local data: start empty.
    }
    authFetch<ApiProfile>(API_ENDPOINTS.profile.get)
      .then((res) => {
        if (!active) return;
        setProfile((prev) => ({
          ...EMPTY_PROFILE,
          ...fromApi(res.data),
          ...local,
          name: prev.name,
          email: prev.email,
        }));
        setIsHydrated(true);
      })
      .catch(() => {
        if (!active) return;
        setProfile((prev) => ({ ...EMPTY_PROFILE, ...local, name: prev.name, email: prev.email }));
        setIsHydrated(true);
        toast.error("Couldn't load your profile. Please refresh.");
      });
    return () => {
      active = false;
    };
  }, [userId, authFetch]);

  // Name and email belong to the account: keep them in step with it.
  const accountName = user?.name ?? "";
  const accountEmail = user?.email ?? "";
  useEffect(() => {
    setProfile((prev) =>
      prev.name === accountName && prev.email === accountEmail
        ? prev
        : { ...prev, name: accountName, email: accountEmail },
    );
  }, [accountName, accountEmail]);

  // Persist the browser-only lists, per user.
  useEffect(() => {
    if (!user || !isHydrated) return;
    try {
      localStorage.setItem(
        localKey(user.id),
        JSON.stringify({
          activities: profile.activities,
          tailoredResumes: profile.tailoredResumes,
        }),
      );
    } catch {
      // Storage full or blocked: the lists still work for this session.
    }
  }, [user, isHydrated, profile.activities, profile.tailoredResumes]);

  const save = useCallback(
    (updates: Partial<UserProfile>) => {
      const body = toApi(updates);
      if (Object.keys(body).length === 0) return;
      authFetch<ApiProfile>(API_ENDPOINTS.profile.update, {
        method: "PATCH",
        body: JSON.stringify(body),
      })
        .then((res) => setProfile((prev) => ({ ...prev, ...fromApi(res.data) })))
        .catch(() => toast.error("Couldn't save your profile. Please try again."));
    },
    [authFetch],
  );

  const updateProfile = useCallback(
    (updates: Partial<UserProfile>) => {
      setProfile((prev) => ({ ...prev, ...updates })); // instant UI; the server's answer follows
      save(updates);
    },
    [save],
  );

  const updateSkills = useCallback(
    (skills: SkillItem[]) => updateProfile({ skills }),
    [updateProfile],
  );
  const updateInterests = useCallback(
    (interests: string[]) => updateProfile({ interests }),
    [updateProfile],
  );
  const updateGoals = useCallback((goals: string[]) => updateProfile({ goals }), [updateProfile]);

  const addSkill = useCallback(
    (skill: SkillItem) => {
      if (profile.skills.some((s) => s.name.toLowerCase() === skill.name.toLowerCase())) return;
      updateSkills([...profile.skills, skill]);
    },
    [profile.skills, updateSkills],
  );

  const removeSkill = useCallback(
    (skillName: string) =>
      updateSkills(profile.skills.filter((s) => s.name.toLowerCase() !== skillName.toLowerCase())),
    [profile.skills, updateSkills],
  );

  const logActivity = useCallback((activity: Omit<ActivityItem, "id" | "timestamp">) => {
    const item: ActivityItem = {
      ...activity,
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
    };
    setProfile((prev) => ({ ...prev, activities: [item, ...prev.activities].slice(0, 50) }));
  }, []);

  const saveTailoredResume = useCallback(
    (resume: Omit<TailoredResumeItem, "id" | "createdAt">) => {
      const item: TailoredResumeItem = {
        ...resume,
        id: crypto.randomUUID(),
        createdAt: new Date().toISOString(),
      };
      setProfile((prev) => ({
        ...prev,
        tailoredResumes: [
          item,
          ...prev.tailoredResumes.filter(
            (r) => !(r.company === resume.company && r.jobTitle === resume.jobTitle),
          ),
        ],
      }));
      logActivity({
        type: "resume_generated",
        title: `Saved a resume tailored to ${resume.jobTitle}${resume.company ? ` at ${resume.company}` : ""}`,
        details: resume.summary,
        targetCompany: resume.company || undefined,
        atsScore: resume.atsScore ?? undefined,
      });
    },
    [logActivity],
  );

  const deleteTailoredResume = useCallback((id: string) => {
    setProfile((prev) => ({
      ...prev,
      tailoredResumes: prev.tailoredResumes.filter((r) => r.id !== id),
    }));
  }, []);

  // Each item is something the agents actually use.
  const completionPercentage = useMemo(() => {
    const filled = [
      profile.title,
      profile.bio,
      profile.location,
      profile.experienceLevel,
      profile.targetRoles.length,
      profile.skills.length,
      profile.interests.length,
      profile.goals.length,
    ].filter(Boolean).length;
    return Math.round((filled / 8) * 100);
  }, [profile]);

  return (
    <UserProfileContext.Provider
      value={{
        profile,
        updateProfile,
        addSkill,
        removeSkill,
        updateSkills,
        updateInterests,
        updateGoals,
        logActivity,
        saveTailoredResume,
        deleteTailoredResume,
        completionPercentage,
        isHydrated,
      }}
    >
      {children}
    </UserProfileContext.Provider>
  );
};

export const useUserProfile = () => {
  const context = useContext(UserProfileContext);
  if (!context) {
    throw new Error("useUserProfile must be used within a UserProfileProvider");
  }
  return context;
};

/** "2026-10-12T…" → "Oct 12, 2026" (falls back to the raw value). */
export function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}
