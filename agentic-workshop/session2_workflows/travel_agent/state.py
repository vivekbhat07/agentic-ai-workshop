"""STATE: the shared data every node reads from and writes to.

Nodes never mutate state directly. They RETURN a dict of updates,
and LangGraph merges those updates into the state.
"""
from typing import TypedDict

from travel_agent.schemas import FinalAnswer, StepResult, ToolCall


class AgentState(TypedDict, total=False):
    question: str               # input from the user
    plan: list[ToolCall]        # written by planner
    current_step: int           # index into plan (control flow)
    results: list[StepResult]   # written by executor
    answer: FinalAnswer         # written by responder
