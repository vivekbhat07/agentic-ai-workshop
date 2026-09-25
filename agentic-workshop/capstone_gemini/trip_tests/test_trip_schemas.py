"""UNIT: capstone schemas reject bad LLM output."""
import pytest
from pydantic import ValidationError

from trip_planner.schemas import Itinerary, Route, TripBrief


@pytest.mark.parametrize(
    "bad",
    [
        {"destination": "Tokyo", "days": 0, "budget": 100, "currency": "USD"},
        {"destination": "Tokyo", "days": 3, "budget": -5, "currency": "USD"},
        {"destination": "", "days": 3, "budget": 100, "currency": "USD"},
    ],
)
def test_trip_brief_rejects_bad_values(bad: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        TripBrief.model_validate(bad)


def test_route_rejects_unknown_worker() -> None:
    with pytest.raises(ValidationError):
        Route.model_validate({"next": "book_flights"})


def test_itinerary_days_must_be_in_order() -> None:
    with pytest.raises(ValidationError, match="numbered"):
        Itinerary.model_validate({
            "days": [{"day": 2, "title": "x", "activities": ["a"]},
                     {"day": 1, "title": "y", "activities": ["b"]}],
            "cost_per_day_usd": 10,
        })
