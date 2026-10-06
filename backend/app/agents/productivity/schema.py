from pydantic import BaseModel, Field


class ProductivityOutput(BaseModel):
    focus_this_week: str
    suggestions: list[str] = Field(max_length=5)
