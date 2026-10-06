from pydantic import BaseModel, Field


class ResumeDraft(BaseModel):
    target_role: str
    summary: str
    bullets: list[str] = Field(max_length=8)
    keywords: list[str] = Field(max_length=20)
