import React, { createContext, useContext, useState, useEffect } from "react";

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
  details?: string;
  targetCompany?: string;
  atsScore?: number;
}

export interface TailoredResumeItem {
  id: string;
  jobTitle: string;
  company: string;
  location: string;
  createdAt: string;
  atsScore: number;
  matchedKeywords: string[];
  summary: string;
  bullets: string[];
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
  workPreference: "Remote" | "Hybrid" | "Onsite";
  skills: SkillItem[];
  interests: string[];
  goals: string[];
  resume: {
    fileName: string;
    uploadedAt: string;
    atsScore: number;
    parsedSkillsCount: number;
    summary: string;
  };
  aiPreferences: {
    tone: "Professional" | "Concise" | "Ambitious";
    focusArea: string;
    autoRunAgents: boolean;
  };
  activities: ActivityItem[];
  tailoredResumes: TailoredResumeItem[];
}

const DEFAULT_PROFILE: UserProfile = {
  name: "Ada Lovelace",
  email: "ada.lovelace@example.com",
  title: "Senior Full-Stack Engineer",
  bio: "Passionate about full-stack web applications, AI agent tooling, and high-performance system design.",
  location: "San Francisco, CA (Remote)",
  experienceLevel: "Senior (6+ years)",
  targetRoles: ["Senior Software Engineer", "Staff AI Platform Lead", "Tech Lead"],
  targetSalary: "$160,000 - $195,000 / yr",
  workPreference: "Remote",
  skills: [
    { name: "TypeScript", category: "Technical", level: "Expert" },
    { name: "React", category: "Technical", level: "Expert" },
    { name: "Python", category: "Technical", level: "Advanced" },
    { name: "System design", category: "Technical", level: "Advanced" },
    { name: "SQL", category: "Technical", level: "Intermediate" },
    { name: "Figma", category: "Tools", level: "Intermediate" },
    { name: "AI tooling", category: "Technical", level: "Advanced" },
    { name: "Team Leadership", category: "Soft Skills", level: "Advanced" },
  ],
  interests: ["Infrastructure", "AI tooling", "Design systems", "Developer Experience"],
  goals: ["Senior engineer", "Switch to ML", "Remote role", "Lead an AI team"],
  resume: {
    fileName: "Ada_Lovelace_CV_2026.pdf",
    uploadedAt: "August 12, 2026",
    atsScore: 92,
    parsedSkillsCount: 14,
    summary: "Senior Engineer with 6+ yrs leading React, TypeScript & AI system architecture.",
  },
  aiPreferences: {
    tone: "Ambitious",
    focusArea: "High-growth tech startups and AI product engineering",
    autoRunAgents: true,
  },
  activities: [
    {
      id: "act-1",
      type: "resume_generated",
      title: "Generated Tailored Resume for Kepler Systems",
      timestamp: "Just now",
      details: "Tailored for Senior Frontend Engineer role with 96% ATS match.",
      targetCompany: "Kepler Systems",
      atsScore: 96,
    },
    {
      id: "act-2",
      type: "job_searched",
      title: "Ran Job Search Agent",
      timestamp: "2 hours ago",
      details: "Discovered 3 top matches in London & Remote EU.",
    },
    {
      id: "act-3",
      type: "profile_updated",
      title: "Updated Profile Target Criteria",
      timestamp: "Yesterday",
      details: "Added AI Tooling & System Design as key focus skills.",
    },
  ],
  tailoredResumes: [
    {
      id: "tres-1",
      jobTitle: "Senior Frontend Engineer",
      company: "Kepler Systems",
      location: "London · Hybrid",
      createdAt: "August 16, 2026",
      atsScore: 96,
      matchedKeywords: ["TypeScript", "System Design", "Micro-frontends", "Performance"],
      summary: "Senior Engineer specialized in high-performance frontend micro-architecture, TypeScript pipelines, and rendering optimization.",
      bullets: [
        "Architected enterprise frontend infrastructure for 1M+ active users, cutting initial bundle load time by 44%.",
        "Engineered type-safe design token system adoption across 6 product engineering squads.",
        "Pioneered automated ATS & accessibility CI audit check pipelines with 99.8% compliance rate.",
      ],
    },
  ],
};

interface UserProfileContextType {
  profile: UserProfile;
  updateProfile: (updates: Partial<UserProfile>) => void;
  addSkill: (skill: SkillItem) => void;
  removeSkill: (skillName: string) => void;
  updateSkills: (skills: SkillItem[]) => void;
  updateInterests: (interests: string[]) => void;
  updateGoals: (goals: string[]) => void;
  uploadResumeSimulated: (fileName: string) => void;
  logActivity: (activity: Omit<ActivityItem, "id" | "timestamp">) => void;
  saveTailoredResume: (resume: Omit<TailoredResumeItem, "id" | "createdAt">) => void;
  deleteTailoredResume: (id: string) => void;
  completionPercentage: number;
}

const UserProfileContext = createContext<UserProfileContextType | undefined>(undefined);

const STORAGE_KEY = "career_compass_user_profile_v2";

export const UserProfileProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [profile, setProfile] = useState<UserProfile>(() => {
    if (typeof window === "undefined") return DEFAULT_PROFILE;
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        return { ...DEFAULT_PROFILE, ...JSON.parse(saved) };
      }
    } catch (e) {
      console.error("Failed to load profile from localStorage:", e);
    }
    return DEFAULT_PROFILE;
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
    } catch (e) {
      console.error("Failed to save profile to localStorage:", e);
    }
  }, [profile]);

  const updateProfile = (updates: Partial<UserProfile>) => {
    setProfile((prev) => ({ ...prev, ...updates }));
  };

  const addSkill = (skill: SkillItem) => {
    setProfile((prev) => {
      if (prev.skills.some((s) => s.name.toLowerCase() === skill.name.toLowerCase())) {
        return prev;
      }
      return { ...prev, skills: [...prev.skills, skill] };
    });
  };

  const removeSkill = (skillName: string) => {
    setProfile((prev) => ({
      ...prev,
      skills: prev.skills.filter((s) => s.name.toLowerCase() !== skillName.toLowerCase()),
    }));
  };

  const updateSkills = (skills: SkillItem[]) => {
    setProfile((prev) => ({ ...prev, skills }));
  };

  const updateInterests = (interests: string[]) => {
    setProfile((prev) => ({ ...prev, interests }));
  };

  const updateGoals = (goals: string[]) => {
    setProfile((prev) => ({ ...prev, goals }));
  };

  const uploadResumeSimulated = (fileName: string) => {
    setProfile((prev) => ({
      ...prev,
      resume: {
        fileName,
        uploadedAt: new Date().toLocaleDateString("en-US", {
          month: "long",
          day: "numeric",
          year: "numeric",
        }),
        atsScore: Math.floor(88 + Math.random() * 8), // 88 - 95 score
        parsedSkillsCount: prev.skills.length + 3,
        summary: `Parsed resume for ${prev.name}: Verified ${prev.skills.length} skills with high ATS keyword matching.`,
      },
    }));
  };

  const logActivity = (activity: Omit<ActivityItem, "id" | "timestamp">) => {
    const newItem: ActivityItem = {
      ...activity,
      id: `act-${Date.now()}`,
      timestamp: "Just now",
    };
    setProfile((prev) => ({
      ...prev,
      activities: [newItem, ...(prev.activities || [])],
    }));
  };

  const saveTailoredResume = (resume: Omit<TailoredResumeItem, "id" | "createdAt">) => {
    const newResume: TailoredResumeItem = {
      ...resume,
      id: `tres-${Date.now()}`,
      createdAt: new Date().toLocaleDateString("en-US", {
        month: "long",
        day: "numeric",
        year: "numeric",
      }),
    };

    setProfile((prev) => {
      // Remove any previous tailored resume for the same company to keep top version clean
      const filtered = (prev.tailoredResumes || []).filter(
        (r) => r.company.toLowerCase() !== resume.company.toLowerCase()
      );
      return {
        ...prev,
        tailoredResumes: [newResume, ...filtered],
      };
    });

    logActivity({
      type: "resume_generated",
      title: `Generated Tailored Resume for ${resume.company}`,
      details: `Customized for ${resume.jobTitle} with ${resume.atsScore}% ATS compatibility.`,
      targetCompany: resume.company,
      atsScore: resume.atsScore,
    });
  };

  const deleteTailoredResume = (id: string) => {
    setProfile((prev) => ({
      ...prev,
      tailoredResumes: (prev.tailoredResumes || []).filter((r) => r.id !== id),
    }));
  };

  const calculateCompletion = (p: UserProfile): number => {
    let score = 0;
    if (p.name) score += 15;
    if (p.email) score += 10;
    if (p.title) score += 15;
    if (p.bio) score += 15;
    if (p.skills.length > 0) score += 15;
    if (p.interests.length > 0) score += 10;
    if (p.goals.length > 0) score += 10;
    if (p.resume?.fileName) score += 10;
    return Math.min(100, score);
  };

  const completionPercentage = calculateCompletion(profile);

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
        uploadResumeSimulated,
        logActivity,
        saveTailoredResume,
        deleteTailoredResume,
        completionPercentage,
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
