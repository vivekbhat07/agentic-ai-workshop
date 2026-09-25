"""Structured output validation with a repair loop.

1. Ask the LLM for JSON.
2. Validate it against a Pydantic schema.
3. If invalid, send the validation error back and ask again (bounded attempts).
"""
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from travel_agent.llm import LLMClient

T = TypeVar("T", bound=BaseModel)


class StructuredOutputError(Exception):
    """Raised when the LLM never produced valid output."""


def generate_structured(
    llm: LLMClient, system: str, prompt: str, schema: type[T], max_attempts: int = 2
) -> T:
    last_error = ""
    for _ in range(max_attempts):
        full_prompt = prompt if not last_error else (
            f"{prompt}\n\nYour previous reply was invalid:\n{last_error}\n"
            "Return ONLY corrected JSON."
        )
        raw = llm.generate(system, full_prompt)
        try:
            return schema.model_validate_json(raw)
        except ValidationError as exc:
            last_error = str(exc)
    raise StructuredOutputError(f"Invalid {schema.__name__} after {max_attempts} tries: {last_error}")
