from pydantic import BaseModel, Field


class Milestone(BaseModel):
    title: str
    when: str
    note: str


class RoadmapOutput(BaseModel):
    goal: str
    milestones: list[Milestone] = Field(max_length=8)
