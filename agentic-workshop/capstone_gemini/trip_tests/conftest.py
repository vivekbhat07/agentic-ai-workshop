"""Capstone fixtures. ScriptedLLM answers per ROLE, so one test can script several agents."""
import json
from typing import Any

import pytest

from trip_planner.graph import build_graph
from trip_planner.llm import FakeTripLLM


class ScriptedLLM:
    """Replies from a per-role queue; falls back to FakeTripLLM for roles not scripted."""

    def __init__(self, **replies: list[Any]) -> None:
        self.replies = {role.upper(): list(r) for role, r in replies.items()}
        self.calls: list[tuple[str, str]] = []
        self.fallback = FakeTripLLM()

    def generate(self, system: str, prompt: str) -> str:
        role = system.split(".", 1)[0]
        self.calls.append((role, prompt))
        queue = self.replies.get(role)
        if queue:
            reply = queue.pop(0) if len(queue) > 1 else queue[0]  # last reply repeats
            return reply if isinstance(reply, str) else json.dumps(reply)
        return self.fallback.generate(system, prompt)

    def prompts(self, role: str) -> list[str]:
        return [p for r, p in self.calls if r == role]


@pytest.fixture
def config() -> dict[str, Any]:
    return {"configurable": {"thread_id": "test-thread"}}


@pytest.fixture
def app() -> Any:
    return build_graph(FakeTripLLM())


@pytest.fixture
def no_sleep() -> list[float]:
    """Collects retry delays instead of sleeping."""
    return []


# 30000 INR = 360 USD = 120 USD/day -> the fake's first draft (150/day) is over budget.
TOKYO = "Plan 3 days in Tokyo on a 30000 INR budget"
