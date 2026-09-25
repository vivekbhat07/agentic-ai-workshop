"""SUPERVISOR-WORKER pattern in LangGraph (minimal).

A supervisor looks at the state and decides which specialist worker runs next.
Here the supervisor is rule-based; in production an LLM would make this choice
(returning a structured {"next": "..."} object, validated like in structured.py).

Run:  python supervisor_demo.py
"""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from travel_agent.tools import convert_currency, get_weather


class TeamState(TypedDict):
    task: str
    done: list[str]
    notes: list[str]


def supervisor(state: TeamState) -> TeamState:
    return state  # the decision itself lives in route() below


def route(state: TeamState) -> str:
    if "weather" in state["task"] and "weather_worker" not in state["done"]:
        return "weather_worker"
    if "budget" in state["task"] and "finance_worker" not in state["done"]:
        return "finance_worker"
    return END


def weather_worker(state: TeamState) -> TeamState:
    w = get_weather("Paris")
    return {**state, "done": [*state["done"], "weather_worker"],
            "notes": [*state["notes"], f"Weather: {w['temp_c']}°C, {w['condition']}"]}


def finance_worker(state: TeamState) -> TeamState:
    eur = convert_currency(1000, "USD", "EUR")
    return {**state, "done": [*state["done"], "finance_worker"],
            "notes": [*state["notes"], f"Budget: 1000 USD = {eur} EUR"]}


g = StateGraph(TeamState)
g.add_node("supervisor", supervisor)
g.add_node("weather_worker", weather_worker)
g.add_node("finance_worker", finance_worker)
g.add_edge(START, "supervisor")
g.add_conditional_edges("supervisor", route, ["weather_worker", "finance_worker", END])
g.add_edge("weather_worker", "supervisor")   # workers always report back
g.add_edge("finance_worker", "supervisor")
app = g.compile()

if __name__ == "__main__":
    out = app.invoke({"task": "Plan Paris trip: check weather and budget", "done": [], "notes": []})
    print("\n".join(out["notes"]))
