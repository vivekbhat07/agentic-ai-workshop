"""Shared FIXTURES: reusable test setup that pytest injects by argument name."""
import json

import pytest

from travel_agent.llm import FakeLLM


class StubLLM:
    """Returns pre-written replies in order and records every call (a 'spy')."""

    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.calls: list[tuple[str, str]] = []

    def generate(self, system: str, prompt: str) -> str:
        self.calls.append((system, prompt))
        return self.replies.pop(0)


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def no_sleep() -> list[float]:
    """Collects delays instead of sleeping, so retry tests run instantly."""
    return []


@pytest.fixture
def valid_answer_json() -> str:
    return json.dumps({"answer": "It is sunny.", "tools_used": ["get_weather"], "confidence": 0.9})
