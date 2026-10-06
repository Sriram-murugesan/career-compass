from pydantic import BaseModel, Field


class InterviewOutput(BaseModel):
    focus: str
    questions: list[str] = Field(max_length=10)
