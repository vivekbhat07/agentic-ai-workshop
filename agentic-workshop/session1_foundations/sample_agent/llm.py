"""LLM: the 'brain'. Here it is a fake, rule-based stand-in so the demo runs offline.

A real LLM would read the goal + history and return the next action as JSON.
"""


def decide_next_action(goal: str, history: list[str]) -> dict:
    # Goal format for the demo: "compute (2 + 3) * 4"
    if not history:
        return {"action": "tool", "tool": "add", "args": {"a": 2, "b": 3}}
    if len(history) == 1:
        last = float(history[-1].split("=")[-1])
        return {"action": "tool", "tool": "multiply", "args": {"a": last, "b": 4}}
    return {"action": "finish", "answer": history[-1].split("=")[-1].strip()}
