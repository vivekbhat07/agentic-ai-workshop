"""UNIT: the deterministic rules that keep the LLM supervisor honest."""
import pytest

from trip_planner.nodes import MAX_TURNS, critique, enforce_policy
from trip_planner.schemas import DayPlan, Itinerary, TripBrief, WorkerResult

OK = WorkerResult(worker="x", ok=True)


@pytest.mark.parametrize(
    ("proposed", "done", "turns", "expected"),
    [
        ("budget", [], 0, "budget"),                        # valid choice is kept
        ("itinerary", [], 0, "weather"),                    # prerequisites first
        ("weather", ["weather"], 1, "budget"),              # never re-run a finished worker
        ("finish", [], 0, "weather"),                       # can't finish with work pending
        ("weather", ["weather", "budget", "itinerary"], 3, "finish"),
        ("weather", [], MAX_TURNS, "finish"),               # loop guard beats everything
    ],
)
def test_enforce_policy(proposed: str, done: list[str], turns: int, expected: str) -> None:
    assert enforce_policy(proposed, {w: OK for w in done}, turns) == expected


BRIEF = TripBrief(destination="Tokyo", days=2, budget=500, currency="USD")


def _itin(n_days: int, cost: float) -> Itinerary:
    days = [DayPlan(day=i + 1, title="t", activities=["a"]) for i in range(n_days)]
    return Itinerary(days=days, cost_per_day_usd=cost)


def test_critique_passes_good_plan() -> None:
    assert critique(_itin(2, 100), BRIEF, cap_usd=250) == []


def test_critique_flags_over_budget_and_wrong_length() -> None:
    problems = critique(_itin(3, 400), BRIEF, cap_usd=250)
    assert len(problems) == 2
    assert any("exceeds budget" in p for p in problems)
