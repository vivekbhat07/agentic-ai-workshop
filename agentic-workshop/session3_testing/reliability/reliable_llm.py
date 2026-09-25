"""Wrap ANY LLMClient with retries — the graph code doesn't change at all."""
import time
from collections.abc import Callable

from reliability.retry import with_retry
from travel_agent.llm import LLMClient


class ReliableLLM:
    def __init__(
        self,
        inner: LLMClient,
        max_attempts: int = 3,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.inner = inner
        self._generate = with_retry(max_attempts=max_attempts, sleep=sleep)(inner.generate)

    def generate(self, system: str, prompt: str) -> str:
        return self._generate(system, prompt)


class FlakyLLM:
    """Test/demo double: fails `failures` times with the given error, then delegates."""

    def __init__(self, inner: LLMClient, failures: int, error: Exception) -> None:
        self.inner, self.failures, self.error = inner, failures, error
        self.calls = 0

    def generate(self, system: str, prompt: str) -> str:
        self.calls += 1
        if self.calls <= self.failures:
            raise self.error
        return self.inner.generate(system, prompt)
