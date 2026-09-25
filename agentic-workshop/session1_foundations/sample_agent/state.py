"""STATE: everything the agent knows at a given moment."""
from dataclasses import dataclass, field


@dataclass
class AgentState:
    goal: str
    history: list[str] = field(default_factory=list)  # short-term memory
    steps_taken: int = 0
    done: bool = False
    final_answer: str | None = None
