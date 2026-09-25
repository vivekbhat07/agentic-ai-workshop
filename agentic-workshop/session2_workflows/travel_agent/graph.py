"""GRAPH: wires nodes and edges into a runnable workflow.

    START -> planner -> executor <-> (loop) -> responder -> END
"""
from functools import partial
from typing import Any

from langgraph.graph import END, START, StateGraph

from travel_agent.llm import LLMClient, get_llm
from travel_agent.nodes import (
    executor,
    planner,
    responder,
    route_after_executor,
    route_after_planner,
)
from travel_agent.state import AgentState


def build_graph(llm: LLMClient | None = None) -> Any:
    llm = llm or get_llm()
    g = StateGraph(AgentState)

    g.add_node("planner", partial(planner, llm=llm))
    g.add_node("executor", executor)
    g.add_node("responder", partial(responder, llm=llm))

    g.add_edge(START, "planner")
    g.add_conditional_edges("planner", route_after_planner, ["executor", "responder"])
    g.add_conditional_edges("executor", route_after_executor, ["executor", "responder"])
    g.add_edge("responder", END)

    return g.compile()
