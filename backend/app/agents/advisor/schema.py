from pydantic import BaseModel, Field


class AdvisorOutput(BaseModel):
    answer: str
    next_steps: list[str] = Field(max_length=5)
