"""GRAPH: LLM supervisor + workers + human review, with a checkpointer.

  START -> intake -> supervisor --(route)--> weather_worker   --+
                        ^                    budget_worker    --+--> supervisor
                        |                    itinerary_worker --+
                        |                    review --(approve)--> finalize -> END
                        +--- itinerary_worker <--(changes requested)--+
"""
from functools import partial
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from travel_agent.llm import LLMClient
from trip_planner.llm import build_llm
from trip_planner.nodes import (
    budget_worker,
    finalize,
    intake,
    itinerary_worker,
    review,
    route_after_review,
    route_from_supervisor,
    supervisor,
    weather_worker,
)
from trip_planner.state import TripState


def build_graph(llm: LLMClient | None = None, checkpointer: Any = None) -> Any:
    llm = llm or build_llm()
    g = StateGraph(TripState)

    g.add_node("intake", partial(intake, llm=llm))
    g.add_node("supervisor", partial(supervisor, llm=llm))
    g.add_node("weather_worker", weather_worker)
    g.add_node("budget_worker", budget_worker)
    g.add_node("itinerary_worker", partial(itinerary_worker, llm=llm))
    g.add_node("review", review)
    g.add_node("finalize", finalize)

    g.add_edge(START, "intake")
    g.add_edge("intake", "supervisor")
    g.add_conditional_edges(
        "supervisor", route_from_supervisor,
        ["weather_worker", "budget_worker", "itinerary_worker", "review"],
    )
    for worker in ("weather_worker", "budget_worker", "itinerary_worker"):
        g.add_edge(worker, "supervisor")          # workers always report back
    g.add_conditional_edges("review", route_after_review, ["itinerary_worker", "finalize"])
    g.add_edge("finalize", END)

    # A checkpointer is REQUIRED for interrupt(): the paused state has to live somewhere.
    return g.compile(checkpointer=checkpointer or MemorySaver())
