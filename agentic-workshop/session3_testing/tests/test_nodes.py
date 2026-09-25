"""COMPONENT tests: each node in isolation, with a stub LLM."""
import json

from tests.conftest import StubLLM
from travel_agent.nodes import executor, planner, route_after_executor
from travel_agent.schemas import ToolCall


def test_planner_writes_plan_and_resets_counters() -> None:
    llm = StubLLM([json.dumps({"steps": [{"tool": "get_weather", "args": {"city": "Tokyo"}}]})])
    update = planner({"question": "weather in Tokyo"}, llm=llm)
    assert update["plan"] == [ToolCall(tool="get_weather", args={"city": "Tokyo"})]
    assert update["current_step"] == 0
    assert update["results"] == []


def test_executor_runs_one_step_and_advances() -> None:
    state = {"plan": [ToolCall(tool="calculator", args={"expression": "1+1"})],
             "current_step": 0, "results": []}
    update = executor(state)
    assert update["current_step"] == 1
    assert update["results"][0].ok and update["results"][0].output == 2.0


def test_executor_captures_tool_failure_instead_of_crashing() -> None:
    state = {"plan": [ToolCall(tool="get_weather", args={"city": "Atlantis"})],
             "current_step": 0, "results": []}
    result = executor(state)["results"][0]
    assert result.ok is False
    assert "Atlantis" in (result.error or "")


def test_router_loops_until_plan_is_done() -> None:
    plan = [ToolCall(tool="calculator", args={}), ToolCall(tool="calculator", args={})]
    assert route_after_executor({"plan": plan, "current_step": 1}) == "executor"
    assert route_after_executor({"plan": plan, "current_step": 2}) == "responder"
