"""TOOLS: plain Python functions the agent is allowed to call."""


def add(a: float, b: float) -> float:
    return a + b


def multiply(a: float, b: float) -> float:
    return a * b


# Tool registry: the agent can only call what is listed here.
TOOLS = {"add": add, "multiply": multiply}
