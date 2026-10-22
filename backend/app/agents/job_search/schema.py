from typing import Literal

from pydantic import BaseModel, Field

Eligibility = Literal["eligible", "check", "unlikely"]

# ── What the agent returns (the API camelCases these) ───────────────────────


class FitBreakdown(BaseModel):
    """How well one posting fits, per dimension (0-100). Final score = weighted mix."""

    skills: int = Field(ge=0, le=100)
    experience: int = Field(ge=0, le=100)
    location: int = Field(ge=0, le=100)
    goals: int = Field(ge=0, le=100)


class JobMatch(BaseModel):
    role: str
    company: str
    location: str
    match_score: int = Field(ge=0, le=100)
    reason: str
    # Re-ranking detail (live postings ranked by the AI; absent for keyword ranking):
    fit: FitBreakdown | None = None
    eligibility: Eligibility | None = None  # can the user apply from where they are?
    matched_skills: list[str] = Field(default_factory=list)  # the user's skills it asks for
    missing_skills: list[str] = Field(default_factory=list)  # asked for, not on the profile
    next_step: str = ""  # one concrete thing to do before applying
    # Live listings only — straight from the job board, never written by the LLM:
    apply_url: str | None = None
    posted_at: str | None = None
    salary: str | None = None
    source: str | None = None


class JobSearchOutput(BaseModel):
    # "live" = real postings from a job board; "suggested" = role ideas (no board / board down)
    mode: Literal["live", "suggested"] = "suggested"
    query: str = ""  # what was searched, e.g. "Senior Frontend Engineer in Chennai"
    notice: str = ""  # shown to the user when results are limited
    ranking: Literal["ai", "keyword", ""] = ""  # how live postings were ordered
    considered: int = 0  # live postings reviewed to pick the matches
    matches: list[JobMatch] = Field(default_factory=list, max_length=5)


# ── What the LLM is asked for along the way ─────────────────────────────────


class SearchPlan(BaseModel):
    queries: list[str] = Field(min_length=1, max_length=2)  # job-title keywords
    location: str = ""  # city/region, "" = anywhere


class JobAssessment(BaseModel):
    """The model's rubric for one posting. Lists/strings are trimmed in code, not rejected."""

    index: int  # position in the listing table shown to the model
    skills_fit: int = Field(ge=0, le=100)
    experience_fit: int = Field(ge=0, le=100)
    location_fit: int = Field(ge=0, le=100)
    goals_fit: int = Field(ge=0, le=100)
    eligibility: Eligibility = "check"
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    reason: str
    next_step: str = ""


class Ranking(BaseModel):
    picks: list[JobAssessment]
