"""COMPONENT: each worker alone. Tools are real; the LLM is scripted."""
from trip_planner.nodes import budget_worker, itinerary_worker, supervisor, weather_worker
from trip_planner.schemas import TripBrief, WorkerResult
from trip_tests.conftest import ScriptedLLM

TOKYO = TripBrief(destination="Tokyo", days=3, budget=30000, currency="INR")


def test_budget_worker_converts_and_splits_per_day() -> None:
    out = budget_worker({"brief": TOKYO})["findings"]["budget"]
    assert out.ok and out.data == {"total_usd": 360.0, "per_day_usd": 120.0}


def test_weather_worker_reports_failure_instead_of_raising() -> None:
    atlantis = TOKYO.model_copy(update={"destination": "Atlantis"})
    out = weather_worker({"brief": atlantis})["findings"]["weather"]
    assert out.ok is False and "Atlantis" in (out.error or "")


def test_itinerary_worker_revises_when_over_budget() -> None:
    day = {"title": "t", "activities": ["a"]}
    draft = {"days": [{"day": i, **day} for i in (1, 2, 3)], "notes": ""}
    llm = ScriptedLLM(itinerary=[{**draft, "cost_per_day_usd": 900},    # over the 120 cap
                                 {**draft, "cost_per_day_usd": 100}])   # fixed
    state = {"brief": TOKYO, "findings": {
        "budget": WorkerResult(worker="budget", ok=True, data={"per_day_usd": 120.0})}}
    out = itinerary_worker(state, llm=llm)["findings"]["itinerary"]
    assert out.ok and out.attempts == 2
    assert "REVISE: cost_per_day_usd 900" in llm.prompts("ITINERARY")[1]   # critique fed back


def test_supervisor_overrides_an_llm_that_skips_ahead() -> None:
    llm = ScriptedLLM(supervisor=[{"next": "itinerary", "reason": "YOLO"}])
    update = supervisor({"brief": TOKYO, "findings": {}, "turns": 0}, llm=llm)
    assert update["next_worker"] == "weather"
    assert "policy override" in update["trace"][0]
