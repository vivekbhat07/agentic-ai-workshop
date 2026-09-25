"""UNIT: provider selection and Gemini error mapping — no SDK or API key needed."""
import pytest

from reliability.errors import PermanentLLMError, TransientLLMError
from reliability.reliable_llm import FlakyLLM, ReliableLLM
from travel_agent.llm import pick_provider
from trip_planner.llm import FakeTripLLM, GeminiErrorAdapter, classify_gemini_error


class FakeGeminiAPIError(Exception):
    """Same shape as google.genai.errors.APIError: an HTTP status in .code."""

    def __init__(self, code: int) -> None:
        super().__init__(f"HTTP {code}")
        self.code = code


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({}, "fake"),
        ({"GEMINI_API_KEY": "k"}, "gemini"),
        ({"OPENAI_API_KEY": "k"}, "openai"),
        ({"GEMINI_API_KEY": "k", "OPENAI_API_KEY": "k"}, "gemini"),
        ({"GEMINI_API_KEY": "k", "LLM_PROVIDER": "fake"}, "fake"),   # explicit wins
    ],
)
def test_pick_provider(env: dict[str, str], expected: str) -> None:
    assert pick_provider(env) == expected


def test_pick_provider_rejects_typos() -> None:
    with pytest.raises(ValueError):
        pick_provider({"LLM_PROVIDER": "gemnii"})


@pytest.mark.parametrize(
    ("code", "kind"),
    [(429, TransientLLMError), (503, TransientLLMError),
     (401, PermanentLLMError), (404, PermanentLLMError)],
)
def test_classify_gemini_error(code: int, kind: type[Exception]) -> None:
    assert isinstance(classify_gemini_error(FakeGeminiAPIError(code)), kind)


def test_unknown_errors_pass_through_unchanged() -> None:
    exc = KeyError("boom")
    assert classify_gemini_error(exc) is exc


def test_rate_limited_gemini_is_retried_then_succeeds(no_sleep: list[float]) -> None:
    flaky = FlakyLLM(FakeTripLLM(), failures=2, error=FakeGeminiAPIError(429))
    llm = ReliableLLM(GeminiErrorAdapter(flaky), max_attempts=3, sleep=no_sleep.append)
    assert "destination" in llm.generate("INTAKE.", "Plan 2 days in Paris on a 300 EUR budget")
    assert flaky.calls == 3 and len(no_sleep) == 2


def test_bad_gemini_key_fails_fast(no_sleep: list[float]) -> None:
    flaky = FlakyLLM(FakeTripLLM(), failures=5, error=FakeGeminiAPIError(401))
    llm = ReliableLLM(GeminiErrorAdapter(flaky), max_attempts=3, sleep=no_sleep.append)
    with pytest.raises(PermanentLLMError):
        llm.generate("INTAKE.", "x")
    assert flaky.calls == 1 and no_sleep == []
