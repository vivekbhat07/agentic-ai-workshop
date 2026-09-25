"""STRUCTURED OUTPUTS: Pydantic models describe exactly what the LLM must return.

If the LLM output doesn't match these shapes, validation fails loudly
instead of letting bad data flow through the program.
"""
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

ToolName = Literal["get_weather", "convert_currency", "calculator"]


class ToolCall(BaseModel):
    """One step of the plan: which tool to call, with which arguments."""

    tool: ToolName
    args: dict[str, Any] = Field(default_factory=dict)


class Plan(BaseModel):
    """What the PLANNER returns."""

    steps: list[ToolCall] = Field(max_length=5)  # cap the plan size
    reasoning: str = ""


class StepResult(BaseModel):
    """What the EXECUTOR records after running one tool."""

    tool: str
    ok: bool
    output: Any = None
    error: str | None = None


class FinalAnswer(BaseModel):
    """What the RESPONDER returns to the user."""

    answer: str = Field(min_length=1)
    tools_used: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("answer")
    @classmethod
    def not_just_whitespace(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("answer must not be blank")
        return v.strip()
