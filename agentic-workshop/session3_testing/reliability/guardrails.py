"""GUARDRAILS: checks before the LLM sees input, and before the user sees output."""
import re

MAX_INPUT_CHARS = 500
_INJECTION_PATTERNS = [
    r"ignore (all |any )?(previous|prior) instructions",
    r"reveal (your )?system prompt",
    r"you are now",
]
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_PHONE = re.compile(r"\+?\d[\d\s-]{8,}\d")


class GuardrailViolation(Exception):
    pass


def check_input(text: str) -> str:
    """Input guardrail: reject empty, oversized, or prompt-injection input."""
    cleaned = text.strip()
    if not cleaned:
        raise GuardrailViolation("Empty question")
    if len(cleaned) > MAX_INPUT_CHARS:
        raise GuardrailViolation(f"Question longer than {MAX_INPUT_CHARS} chars")
    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, cleaned, flags=re.I):
            raise GuardrailViolation("Possible prompt injection detected")
    return cleaned


def redact_pii(text: str) -> str:
    """Output guardrail: never echo emails or phone numbers back to the user."""
    text = _EMAIL.sub("[email redacted]", text)
    return _PHONE.sub("[phone redacted]", text)
