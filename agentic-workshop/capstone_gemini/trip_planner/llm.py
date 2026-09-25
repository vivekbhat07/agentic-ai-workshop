"""LLMs for the capstone.

- FakeTripLLM        : offline, deterministic stand-in that knows the 3 capstone roles.
- GeminiErrorAdapter : translates google-genai errors into Session 3's error classes,
                       so ReliableLLM knows what to retry. (Wrapper pattern, again.)
- build_llm()        : fake by default; real Gemini when GEMINI_API_KEY is set.
"""
import json
import re
from typing import Any

from reliability.errors import PermanentLLMError, TransientLLMError
from reliability.reliable_llm import ReliableLLM
from travel_agent.llm import GeminiLLM, LLMClient, OpenAILLM, pick_provider

# ---------------------------------------------------------------- error mapping
TRANSIENT_CODES = {408, 429, 500, 502, 503, 504}   # 429 = RESOURCE_EXHAUSTED (free tier!)
PERMANENT_CODES = {400, 401, 403, 404}              # bad request / key / model name


def classify_gemini_error(exc: Exception) -> Exception:
    """Map an SDK exception to Transient/Permanent. Unknown errors pass through unchanged.

    google.genai.errors.APIError (and its ClientError/ServerError subclasses) carry an
    HTTP status in `.code`, so we read that instead of importing the SDK — which also
    lets tests use a tiny fake exception.
    """
    code = getattr(exc, "code", None)
    if isinstance(exc, TimeoutError) or "Timeout" in type(exc).__name__:
        return TransientLLMError(f"Gemini timeout: {exc}")
    if code in TRANSIENT_CODES:
        return TransientLLMError(f"Gemini {code}: {exc}")
    if code in PERMANENT_CODES:
        return PermanentLLMError(f"Gemini {code}: {exc}")
    return exc


class GeminiErrorAdapter:
    def __init__(self, inner: LLMClient) -> None:
        self.inner = inner

    def generate(self, system: str, prompt: str) -> str:
        try:
            return self.inner.generate(system, prompt)
        except (TransientLLMError, PermanentLLMError):
            raise
        except Exception as exc:
            mapped = classify_gemini_error(exc)
            if mapped is exc:
                raise
            raise mapped from exc


def build_llm(provider: str | None = None) -> LLMClient:
    """Retries on the outside, error translation on the inside: Retry(Adapter(Gemini))."""
    provider = provider or pick_provider()
    inner: LLMClient
    if provider == "gemini":
        inner = GeminiErrorAdapter(GeminiLLM())
    elif provider == "openai":
        inner = OpenAILLM()
    else:
        inner = FakeTripLLM()
    return ReliableLLM(inner)


# ---------------------------------------------------------------- offline fake
_SIGHTS = {
    "tokyo": ["Senso-ji at sunrise", "Tsukiji outer market", "teamLab Planets", "Shibuya Sky"],
    "paris": ["Louvre (book ahead)", "Seine walk", "Montmartre", "Musée d'Orsay"],
    "bengaluru": ["Lalbagh garden", "Cubbon Park", "VV Puram food street", "Bangalore Palace"],
}


class FakeTripLLM:
    """Pretends to be Gemini. The first word of the system prompt tells it which role to play."""

    def generate(self, system: str, prompt: str) -> str:
        role = system.split(".", 1)[0]
        if role == "INTAKE":
            return json.dumps(self._intake(prompt))
        if role == "SUPERVISOR":
            return json.dumps(self._supervise(prompt))
        if role == "ITINERARY":
            return json.dumps(self._itinerary(prompt))
        raise ValueError(f"FakeTripLLM does not know role {role!r}")

    @staticmethod
    def _intake(request: str) -> dict[str, Any]:
        days = re.search(r"(\d+)\s*days?", request, flags=re.I)
        city = re.search(r"\bin ([A-Z][a-zA-Z]+)", request)
        money = re.search(r"(\d+(?:\.\d+)?)\s*([A-Z]{3})\b", request)
        return {
            "destination": city[1] if city else "",        # "" fails validation on purpose
            "days": int(days[1]) if days else 2,
            "budget": float(money[1]) if money else 0,
            "currency": money[2] if money else "USD",
        }

    @staticmethod
    def _supervise(prompt: str) -> dict[str, Any]:
        done = json.loads(prompt.split("FINDINGS_JSON:", 1)[1])
        for worker in ("weather", "budget", "itinerary"):
            if worker not in done:
                return {"next": worker, "reason": f"{worker} not gathered yet"}
        return {"next": "finish", "reason": "all findings present"}

    @staticmethod
    def _itinerary(prompt: str) -> dict[str, Any]:
        brief = json.loads(prompt.split("BRIEF_JSON:", 1)[1].split("\n", 1)[0])
        ctx = json.loads(prompt.split("CONTEXT_JSON:", 1)[1].split("\n", 1)[0])
        sights = _SIGHTS.get(brief["destination"].lower(), ["Old town walk", "Local museum"])
        extra = ["Food walk (requested)"] if "HUMAN_FEEDBACK:" in prompt else []
        days = [
            {"day": i + 1, "title": f"Day {i + 1} in {brief['destination']}",
             "activities": (extra + [sights[i % len(sights)]])[:4]}
            for i in range(brief["days"])
        ]
        cap = ctx.get("per_day_usd")
        # First draft is deliberately pricey; a REVISE request brings it under budget.
        cost = round(cap * 0.9, 2) if ("REVISE:" in prompt and cap) else 150.0
        condition = ctx.get("weather") or "unknown"
        notes = f"Weather: {condition}." + (" Pack an umbrella." if "rain" in condition else "")
        return {"days": days, "cost_per_day_usd": cost, "notes": notes}
