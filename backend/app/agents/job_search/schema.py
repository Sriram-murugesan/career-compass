from pydantic import BaseModel, Field


class JobMatch(BaseModel):
    role: str
    company: str
    location: str
    match_score: int = Field(ge=0, le=100)
    reason: str


class JobSearchOutput(BaseModel):
    matches: list[JobMatch] = Field(max_length=5)
