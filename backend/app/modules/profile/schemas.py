from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.core.schema import ApiModel


class Skill(ApiModel):
    name: str = Field(min_length=1, max_length=60)
    category: Literal["Technical", "Soft Skills", "Tools"] = "Technical"
    level: Literal["Beginner", "Intermediate", "Advanced", "Expert"] = "Intermediate"


class AiPreferences(ApiModel):
    tone: Literal["Professional", "Concise", "Ambitious"] = "Professional"
    focus_area: str = Field(default="", max_length=200)
    auto_run_agents: bool = True


WorkPreference = Literal["Remote", "Hybrid", "Onsite", ""]


class ProfileOut(ApiModel):
    headline: str
    bio: str
    location: str
    target_salary: str
    work_preference: WorkPreference
    experience_level: str
    target_roles: list[str]
    skills: list[Skill]
    interests: list[str]
    goals: list[str]
    ai_preferences: AiPreferences


class ProfileUpdate(ApiModel):
    """PATCH body: every field optional; only the ones sent are changed."""

    headline: str | None = Field(default=None, max_length=200)
    bio: str | None = Field(default=None, max_length=1000)
    location: str | None = Field(default=None, max_length=200)
    target_salary: str | None = Field(default=None, max_length=100)
    work_preference: WorkPreference | None = None
    experience_level: str | None = Field(default=None, max_length=100)
    target_roles: list[str] | None = Field(default=None, max_length=20)
    skills: list[Skill] | None = Field(default=None, max_length=100)
    interests: list[str] | None = Field(default=None, max_length=50)
    goals: list[str] | None = Field(default=None, max_length=50)
    ai_preferences: AiPreferences | None = None
