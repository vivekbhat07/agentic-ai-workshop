"""NODES for Trip Planner Pro.

intake -> supervisor <-> workers (weather, budget, itinerary) -> review (human) -> finalize

Key idea: the LLM *proposes* the next step, deterministic code *enforces* the rules.
"""
import json
from typing import Any

from langgraph.types import interrupt

from reliability.guardrails import check_input, redact_pii
from travel_agent.llm import LLMClient
from travel_agent.structured import generate_structured
from travel_agent.tools import calculator, convert_currency, get_weather
from trip_planner.schemas import Itinerary, Route, TripBrief, WorkerResult
from trip_planner.state import TripState

MAX_TURNS = 10             # supervisor decisions per run
MAX_REVISIONS = 2          # itinerary self-correction attempts (budget critic)
MAX_HUMAN_ROUNDS = 2       # times a reviewer may send the plan back
WORKERS = ("weather", "budget", "itinerary")
PREREQS: dict[str, tuple[str, ...]] = {"itinerary": ("weather", "budget")}

INTAKE_SYSTEM = (
    "INTAKE. Extract the trip request as JSON: "
    '{"destination": str, "days": int 1-7, "budget": number > 0, "currency": 3-letter code}'
)
SUPERVISOR_SYSTEM = (
    "SUPERVISOR. You coordinate workers: weather, budget, itinerary. "
    "Given the brief and which findings exist, pick the ONE next worker, or finish. "
    'Reply as JSON: {"next": "weather"|"budget"|"itinerary"|"finish", "reason": str}'
)
ITINERARY_SYSTEM = (
    "ITINERARY. Write a day-by-day plan that fits the per-day USD budget and the weather. "
    'Reply as JSON: {"days": [{"day": int, "title": str, "activities": [str, max 4]}], '
    '"cost_per_day_usd": number, "notes": str}. If REVISE is present, fix those problems.'
)


# ------------------------------------------------------------------ intake
def intake(state: TripState, llm: LLMClient) -> TripState:
    request = check_input(state["request"])                 # guardrail before any LLM call
    brief = generate_structured(llm, INTAKE_SYSTEM, request, TripBrief)
    return {
        "brief": brief, "turns": 0, "human_rounds": 0,
        "trace": [f"intake: {brief.destination}, {brief.days} days, "
                  f"{brief.budget:g} {brief.currency}"],
    }


# ------------------------------------------------------------------ supervisor
def enforce_policy(proposed: str, findings: dict[str, WorkerResult], turns: int) -> str:
    """Pure function: turn the LLM's proposal into an allowed step."""
    if turns >= MAX_TURNS:
        return "finish"

    def runnable(w: str) -> bool:
        return w not in findings and all(p in findings for p in PREREQS.get(w, ()))

    if proposed in WORKERS and runnable(proposed):
        return proposed
    pending = [w for w in WORKERS if runnable(w)]
    return pending[0] if pending else "finish"


def supervisor(state: TripState, llm: LLMClient) -> TripState:
    findings = state.get("findings", {})
    summary = {k: "ok" if v.ok else f"failed: {v.error}" for k, v in findings.items()}
    prompt = (f"BRIEF_JSON:{state['brief'].model_dump_json()}\n"
              f"FINDINGS_JSON:{json.dumps(summary)}")
    decision = generate_structured(llm, SUPERVISOR_SYSTEM, prompt, Route)
    chosen = enforce_policy(decision.next, findings, state.get("turns", 0))
    note = "" if chosen == decision.next else f"  (policy override: LLM said {decision.next})"
    return {"next_worker": chosen, "turns": state.get("turns", 0) + 1,
            "trace": [f"supervisor -> {chosen}{note}"]}


def route_from_supervisor(state: TripState) -> str:
    nxt = state["next_worker"]
    return "review" if nxt == "finish" else f"{nxt}_worker"


# ------------------------------------------------------------------ workers
def weather_worker(state: TripState) -> TripState:
    try:
        data = get_weather(state["brief"].destination)
        res = WorkerResult(worker="weather", ok=True, data=data)
    except Exception as exc:  # a failing worker reports back; it never crashes the run
        res = WorkerResult(worker="weather", ok=False, error=str(exc))
    return {"findings": {"weather": res},
            "trace": [f"weather_worker: {'ok' if res.ok else res.error}"]}


def budget_worker(state: TripState) -> TripState:
    b = state["brief"]
    try:
        total_usd = convert_currency(b.budget, b.currency, "USD")
        per_day = calculator(f"{total_usd} / {b.days}")
        res = WorkerResult(worker="budget", ok=True,
                           data={"total_usd": total_usd, "per_day_usd": round(per_day, 2)})
    except Exception as exc:
        res = WorkerResult(worker="budget", ok=False, error=str(exc))
    msg = f"${res.data['per_day_usd']}/day" if res.ok else res.error
    return {"findings": {"budget": res}, "trace": [f"budget_worker: {msg}"]}


def critique(itin: Itinerary, brief: TripBrief, cap_usd: float | None) -> list[str]:
    """Pure business-rule check the schema can't express. Empty list = good."""
    problems: list[str] = []
    if len(itin.days) != brief.days:
        problems.append(f"plan has {len(itin.days)} days, expected {brief.days}")
    if cap_usd is not None and itin.cost_per_day_usd > cap_usd:
        problems.append(f"cost_per_day_usd {itin.cost_per_day_usd} exceeds budget {cap_usd}")
    return problems


def itinerary_worker(state: TripState, llm: LLMClient) -> TripState:
    brief, findings = state["brief"], state.get("findings", {})
    weather, budget = findings.get("weather"), findings.get("budget")
    cap = budget.data["per_day_usd"] if budget and budget.ok else None
    context: dict[str, Any] = {
        "weather": weather.data["condition"] if weather and weather.ok else None,
        "per_day_usd": cap,
    }
    base = f"BRIEF_JSON:{brief.model_dump_json()}\nCONTEXT_JSON:{json.dumps(context)}"
    if state.get("human_feedback"):
        base += f"\nHUMAN_FEEDBACK: {state['human_feedback']}"

    prompt, attempt = base, 0
    problems: list[str] = []
    for attempt in range(1, MAX_REVISIONS + 1):             # bounded self-correction
        itin = generate_structured(llm, ITINERARY_SYSTEM, prompt, Itinerary)
        problems = critique(itin, brief, cap)
        if not problems:
            break
        prompt = f"{base}\nREVISE: {'; '.join(problems)}"

    res = WorkerResult(worker="itinerary", ok=not problems, data=itin.model_dump(),
                       error="; ".join(problems) or None, attempts=attempt)
    status = "ok" if res.ok else f"still failing: {res.error}"
    return {"itinerary": itin, "findings": {"itinerary": res},
            "trace": [f"itinerary_worker: {status} after {attempt} attempt(s), "
                      f"${itin.cost_per_day_usd}/day"]}


# ------------------------------------------------------------------ human in the loop
def review(state: TripState) -> TripState:
    """Pauses the graph. The run resumes with Command(resume={"approve": bool, "feedback": str})."""
    itin = state.get("itinerary")
    warning = state.get("findings", {}).get("itinerary")
    decision = interrupt({
        "itinerary": itin.model_dump() if itin else None,
        "warning": warning.error if warning else "no itinerary produced",
    })
    if decision.get("approve"):
        return {"approved": True, "trace": ["review: approved"]}
    feedback = str(decision.get("feedback", "")).strip()
    return {"approved": False, "human_feedback": feedback,
            "human_rounds": state.get("human_rounds", 0) + 1,
            "trace": [f"review: changes requested - {feedback!r}"]}


def route_after_review(state: TripState) -> str:
    if state.get("approved") or state.get("human_rounds", 0) >= MAX_HUMAN_ROUNDS:
        return "finalize"
    return "itinerary_worker"


def finalize(state: TripState) -> TripState:
    """Deterministic formatting, no LLM. Output guardrail applied last."""
    itin, brief = state.get("itinerary"), state["brief"]
    if not state.get("approved") or itin is None:
        rounds = state.get("human_rounds", 0)
        text = f"Plan for {brief.destination} not approved after {rounds} review round(s)."
    else:
        lines = [f"{brief.days}-day plan for {brief.destination} "
                 f"(about ${itin.cost_per_day_usd}/day). {itin.notes}"]
        lines += [f"  Day {d.day}: {', '.join(d.activities)}" for d in itin.days]
        text = "\n".join(lines)
    return {"final": redact_pii(text), "trace": ["finalize: done"]}
