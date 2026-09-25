"""Structured output: schemas reject bad data; the repair loop retries once."""
import pytest
from pydantic import ValidationError

from tests.conftest import StubLLM
from travel_agent.schemas import FinalAnswer, Plan
from travel_agent.structured import StructuredOutputError, generate_structured


def test_final_answer_rejects_confidence_out_of_range() -> None:
    with pytest.raises(ValidationError):
        FinalAnswer(answer="hi", confidence=1.7)


def test_plan_rejects_unknown_tool() -> None:
    with pytest.raises(ValidationError):
        Plan.model_validate({"steps": [{"tool": "delete_database", "args": {}}]})


def test_repair_loop_recovers_after_one_bad_reply(valid_answer_json: str) -> None:
    llm = StubLLM(["not json at all", valid_answer_json])
    result = generate_structured(llm, "RESPONDER", "q", FinalAnswer)
    assert result.answer == "It is sunny."
    assert len(llm.calls) == 2
    assert "previous reply was invalid" in llm.calls[1][1]  # error was fed back


def test_repair_loop_gives_up_after_max_attempts() -> None:
    llm = StubLLM(['{"answer": ""}', '{"answer": ""}'])
    with pytest.raises(StructuredOutputError):
        generate_structured(llm, "RESPONDER", "q", FinalAnswer, max_attempts=2)
