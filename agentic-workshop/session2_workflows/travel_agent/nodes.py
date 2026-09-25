"""NODES: each node is a function  state -> partial state update."""
import json

from travel_agent.llm import LLMClient
from travel_agent.schemas import FinalAnswer, Plan, StepResult
from travel_agent.state import AgentState
from travel_agent.structured import generate_structured
from travel_agent.tools import TOOLS

PLANNER_SYSTEM = (
    "PLANNER. Break the user's question into tool calls. "
    "Tools: get_weather(city), convert_currency(amount, from_cur, to_cur), "
    "calculator(expression). Reply as JSON: "
    '{"steps": [{"tool": str, "args": {...}}], "reasoning": str}'
)
RESPONDER_SYSTEM = (
    "RESPONDER. Write a short answer using ONLY the tool results. Reply as JSON: "
    '{"answer": str, "tools_used": [str], "confidence": float 0-1}'
)


def planner(state: AgentState, llm: LLMClient) -> AgentState:
    plan = generate_structured(llm, PLANNER_SYSTEM, state["question"], Plan)
    return {"plan": plan.steps, "current_step": 0, "results": []}


def executor(state: AgentState) -> AgentState:
    """Runs ONE step of the plan, then hands control back to the graph."""
    step = state["plan"][state["current_step"]]
    try:
        output = TOOLS[step.tool](**step.args)
        result = StepResult(tool=step.tool, ok=True, output=output)
    except Exception as exc:  # a failing tool must not crash the whole agent
        result = StepResult(tool=step.tool, ok=False, error=str(exc))
    return {
        "results": [*state["results"], result],
        "current_step": state["current_step"] + 1,
    }


def responder(state: AgentState, llm: LLMClient) -> AgentState:
    results_json = json.dumps([r.model_dump() for r in state["results"]])
    prompt = f"Question: {state['question']}\nRESULTS_JSON:{results_json}"
    answer = generate_structured(llm, RESPONDER_SYSTEM, prompt, FinalAnswer)
    return {"answer": answer}


def route_after_executor(state: AgentState) -> str:
    """CONDITIONAL EDGE: loop back to executor until the plan is finished."""
    return "executor" if state["current_step"] < len(state["plan"]) else "responder"


def route_after_planner(state: AgentState) -> str:
    return "executor" if state["plan"] else "responder"
