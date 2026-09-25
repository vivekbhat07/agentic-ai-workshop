"""TOOLS: deterministic functions. Easy to test, no LLM involved."""
import ast
import operator
from collections.abc import Callable
from typing import Any

# Fake data so the workshop runs offline and results are predictable.
_WEATHER = {
    "paris": {"temp_c": 18, "condition": "cloudy"},
    "tokyo": {"temp_c": 24, "condition": "sunny"},
    "bengaluru": {"temp_c": 27, "condition": "light rain"},
}
_RATES_TO_USD = {"USD": 1.0, "EUR": 1.08, "INR": 0.012, "JPY": 0.0067}


def get_weather(city: str) -> dict[str, Any]:
    data = _WEATHER.get(city.strip().lower())
    if data is None:
        raise ValueError(f"No weather data for '{city}'")
    return {"city": city.title(), **data}


def convert_currency(amount: float, from_cur: str, to_cur: str) -> float:
    f, t = from_cur.upper(), to_cur.upper()
    if f not in _RATES_TO_USD or t not in _RATES_TO_USD:
        raise ValueError(f"Unsupported currency pair {f}->{t}")
    if amount < 0:
        raise ValueError("amount must be non-negative")
    return round(amount * _RATES_TO_USD[f] / _RATES_TO_USD[t], 2)


_OPS: dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def calculator(expression: str) -> float:
    """Safe arithmetic. Never use eval() on text that came from an LLM."""

    def _eval(node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
        raise ValueError(f"Unsupported expression: {expression!r}")

    return _eval(ast.parse(expression, mode="eval").body)


TOOLS: dict[str, Callable[..., Any]] = {
    "get_weather": get_weather,
    "convert_currency": convert_currency,
    "calculator": calculator,
}
