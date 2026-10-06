from typing import Literal

from pydantic import BaseModel, Field


class ValidationCheck(BaseModel):
    label: str
    state: Literal["pass", "warn", "fail"]
    note: str


class ValidationOutput(BaseModel):
    ats_score: int = Field(ge=0, le=100)
    checks: list[ValidationCheck]
