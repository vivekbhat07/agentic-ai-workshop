"""INTEGRATION tests: the whole graph end-to-end with the deterministic FakeLLM."""
from travel_agent.graph import build_graph
from travel_agent.llm import FakeLLM


def test_multi_tool_question(fake_llm: FakeLLM) -> None:
    out = build_graph(fake_llm).invoke({"question": "weather in Paris and 200 USD to EUR"})
    assert out["answer"].tools_used == ["get_weather", "convert_currency"]
    assert "Paris" in out["answer"].answer
    assert out["answer"].confidence == 1.0


def test_question_with_no_tools_skips_executor(fake_llm: FakeLLM) -> None:
    out = build_graph(fake_llm).invoke({"question": "tell me a joke"})
    assert out["results"] == []
    assert out["answer"].confidence == 0.0


def test_failed_tool_lowers_confidence(fake_llm: FakeLLM) -> None:
    out = build_graph(fake_llm).invoke({"question": "weather in Paris and weather in Atlantis"})
    assert out["answer"].confidence == 0.5
