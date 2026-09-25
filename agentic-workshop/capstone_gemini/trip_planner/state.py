"""STATE with REDUCERS.

Session 2 nodes returned whole lists ([*old, new]). Here LangGraph does the merging:
- trace    uses operator.add  -> each node returns ONLY its new lines
- findings uses merge_findings -> each worker returns ONLY its own key
"""
import operator
from typing import Annotated, TypedDict

from trip_planner.schemas import Itinerary, TripBrief, WorkerResult


def merge_findings(
    left: dict[str, WorkerResult], right: dict[str, WorkerResult]
) -> dict[str, WorkerResult]:
    return {**left, **right}  # a re-run worker overwrites its own entry


class TripState(TypedDict, total=False):
    request: str                                               # user input
    brief: TripBrief                                           # intake writes
    findings: Annotated[dict[str, WorkerResult], merge_findings]  # workers write
    trace: Annotated[list[str], operator.add]                  # every node appends
    next_worker: str                                           # supervisor writes
    turns: int                                                 # loop guard
    itinerary: Itinerary                                       # itinerary worker writes
    approved: bool                                             # human (review) writes
    human_feedback: str
    human_rounds: int
    final: str                                                 # finalize writes
