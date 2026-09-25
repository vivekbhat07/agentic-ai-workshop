"""Putting it together: guardrails + retries around the Session 2 graph."""
from reliability.guardrails import GuardrailViolation, check_input, redact_pii
from reliability.reliable_llm import ReliableLLM
from travel_agent.graph import build_graph
from travel_agent.llm import LLMClient, get_llm
from travel_agent.structured import StructuredOutputError


def ask(question: str, llm: LLMClient | None = None) -> str:
    try:
        question = check_input(question)                      # input guardrail
    except GuardrailViolation as exc:
        return f"Sorry, I can't process that: {exc}"

    app = build_graph(ReliableLLM(llm or get_llm()))          # retries
    try:
        state = app.invoke({"question": question})
    except StructuredOutputError:
        return "Sorry, I couldn't produce a reliable answer. Please try again."

    return redact_pii(state["answer"].answer)                 # output guardrail
