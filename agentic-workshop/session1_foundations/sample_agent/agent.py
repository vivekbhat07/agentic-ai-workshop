"""CONTROL FLOW + ORCHESTRATION: the loop that ties state, LLM and tools together."""
from sample_agent.llm import decide_next_action
from sample_agent.state import AgentState
from sample_agent.tools import TOOLS

MAX_STEPS = 5  # safety limit: agents must never loop forever


def run_agent(goal: str) -> AgentState:
    state = AgentState(goal=goal)

    while not state.done and state.steps_taken < MAX_STEPS:
        decision = decide_next_action(state.goal, state.history)   # 1. THINK

        if decision["action"] == "finish":                        # 2. BRANCH
            state.final_answer = decision["answer"]
            state.done = True
            break

        tool = TOOLS[decision["tool"]]                            # 3. ACT
        result = tool(**decision["args"])

        state.history.append(f"{decision['tool']}({decision['args']}) = {result}")  # 4. UPDATE
        state.steps_taken += 1

    return state
