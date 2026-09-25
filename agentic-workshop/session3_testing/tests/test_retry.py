"""Retry logic: retries transient errors, never retries permanent ones."""
import pytest

from reliability.errors import PermanentLLMError, TransientLLMError
from reliability.reliable_llm import FlakyLLM, ReliableLLM
from reliability.retry import with_retry
from travel_agent.llm import FakeLLM


def test_succeeds_after_transient_failures(no_sleep: list[float]) -> None:
    flaky = FlakyLLM(FakeLLM(), failures=2, error=TransientLLMError("429"))
    llm = ReliableLLM(flaky, max_attempts=3, sleep=no_sleep.append)
    assert "steps" in llm.generate("PLANNER", "weather in Paris")
    assert flaky.calls == 3
    assert len(no_sleep) == 2


def test_backoff_delays_grow_exponentially(no_sleep: list[float]) -> None:
    @with_retry(max_attempts=4, base_delay=1.0, sleep=no_sleep.append)
    def always_fails() -> None:
        raise TimeoutError

    with pytest.raises(TimeoutError):
        always_fails()
    # 1s, 2s, 4s (+ up to 10% jitter)
    assert [round(d) for d in no_sleep] == [1, 2, 4]


def test_permanent_error_is_not_retried(no_sleep: list[float]) -> None:
    flaky = FlakyLLM(FakeLLM(), failures=5, error=PermanentLLMError("bad API key"))
    llm = ReliableLLM(flaky, max_attempts=3, sleep=no_sleep.append)
    with pytest.raises(PermanentLLMError):
        llm.generate("PLANNER", "x")
    assert flaky.calls == 1
    assert no_sleep == []
