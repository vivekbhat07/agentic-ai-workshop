"""STRUCTURED OUTPUTS for the capstone. Every LLM reply must match one of these."""
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

NextStep = Literal["weather", "budget", "itinerary", "finish"]


class TripBrief(BaseModel):
    """What INTAKE extracts from the user's free-text request."""

    destination: str = Field(min_length=2)
    days: int = Field(ge=1, le=7)
    budget: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)


class Route(BaseModel):
    """What the SUPERVISOR returns: which worker runs next, and why."""

    next: NextStep
    reason: str = ""


class DayPlan(BaseModel):
    day: int = Field(ge=1)
    title: str = Field(min_length=1)
    activities: list[str] = Field(min_length=1, max_length=4)


class Itinerary(BaseModel):
    """What the ITINERARY worker returns."""

    days: list[DayPlan] = Field(min_length=1, max_length=7)
    cost_per_day_usd: float = Field(ge=0)
    notes: str = ""

    @model_validator(mode="after")
    def days_numbered_in_order(self) -> "Itinerary":
        if [d.day for d in self.days] != list(range(1, len(self.days) + 1)):
            raise ValueError("days must be numbered 1..N in order")
        return self


class WorkerResult(BaseModel):
    """What every worker reports back to the supervisor."""

    worker: str
    ok: bool
    data: Any = None
    error: str | None = None
    attempts: int = 1
