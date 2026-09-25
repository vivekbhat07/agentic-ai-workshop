"""LLM clients.

Every client implements one method: generate(system, prompt) -> str (a JSON string).
- FakeLLM   : offline, rule-based, deterministic. Default for the workshop.
- GeminiLLM : Google Gemini via the google-genai SDK (GEMINI_API_KEY).
- OpenAILLM : OpenAI via the openai SDK (OPENAI_API_KEY).

Which one you get is decided by pick_provider() — see the bottom of this file.
"""
import json
import os
import re
from collections.abc import Mapping
from typing import Any, Protocol

PROVIDERS = ("fake", "gemini", "openai")


class LLMClient(Protocol):
    def generate(self, system: str, prompt: str) -> str: ...


class FakeLLM:
    """Pretends to be an LLM so the graph runs without network or cost."""

    def generate(self, system: str, prompt: str) -> str:
        if system.startswith("PLANNER"):
            return json.dumps(self._plan(prompt))
        if system.startswith("RESPONDER"):
            return json.dumps(self._respond(prompt))
        raise ValueError("FakeLLM does not know this role")

    @staticmethod
    def _plan(question: str) -> dict[str, Any]:
        steps: list[dict[str, Any]] = []
        for city in re.findall(r"weather in ([A-Za-z]+)", question, flags=re.I):
            steps.append({"tool": "get_weather", "args": {"city": city}})
        m = re.search(r"(\d+(?:\.\d+)?)\s*([A-Z]{3})\s+(?:to|in)\s+([A-Z]{3})", question)
        if m:
            steps.append({"tool": "convert_currency",
                          "args": {"amount": float(m[1]), "from_cur": m[2], "to_cur": m[3]}})
        m = re.search(r"calculate\s+([\d\s+\-*/().]+)", question, flags=re.I)
        if m:
            steps.append({"tool": "calculator", "args": {"expression": m[1].strip()}})
        return {"steps": steps, "reasoning": f"Found {len(steps)} sub-task(s)."}

    @staticmethod
    def _respond(prompt: str) -> dict[str, Any]:
        results = json.loads(prompt.split("RESULTS_JSON:", 1)[1])
        parts: list[str] = []
        used: list[str] = []
        for r in results:
            used.append(r["tool"])
            if not r["ok"]:
                parts.append(f"I couldn't complete {r['tool']}: {r['error']}")
            elif r["tool"] == "get_weather":
                o = r["output"]
                parts.append(f"{o['city']} is {o['temp_c']}°C and {o['condition']}.")
            else:
                parts.append(f"{r['tool']} result: {r['output']}.")
        if not parts:
            parts = ["I don't have a tool that can answer that."]
        ok_ratio = sum(r["ok"] for r in results) / len(results) if results else 0.0
        return {"answer": " ".join(parts), "tools_used": used, "confidence": round(ok_ratio, 2)}


class OpenAILLM:
    """Real model via the OpenAI SDK, forced into JSON mode."""

    def __init__(self, model: str | None = None) -> None:
        from openai import OpenAI  # imported lazily so the SDK is optional

        self.client = OpenAI()
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def generate(self, system: str, prompt: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content or ""


class GeminiLLM:
    """Real model via Google's google-genai SDK, forced into JSON output.

    Note: Gemini 3.x models ignore temperature/top_p/top_k, so we don't pass them.
    Determinism is NOT a setting you can buy — which is why tests use fakes.
    """

    def __init__(self, model: str | None = None) -> None:
        from google import genai  # imported lazily so the SDK is optional
        from google.genai import types

        self._types = types
        self.client = genai.Client()  # reads GEMINI_API_KEY (or GOOGLE_API_KEY)
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    def generate(self, system: str, prompt: str) -> str:
        resp = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=self._types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",  # Gemini's JSON mode
            ),
        )
        return resp.text or ""


def pick_provider(env: Mapping[str, str] = os.environ) -> str:
    """Pure function (easy to test): LLM_PROVIDER wins, else the first key found, else offline."""
    explicit = env.get("LLM_PROVIDER", "").strip().lower()
    if explicit:
        if explicit not in PROVIDERS:
            raise ValueError(f"LLM_PROVIDER must be one of {PROVIDERS}, got {explicit!r}")
        return explicit
    if env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY"):
        return "gemini"
    if env.get("OPENAI_API_KEY"):
        return "openai"
    return "fake"


def get_llm() -> LLMClient:
    provider = pick_provider()
    if provider == "gemini":
        return GeminiLLM()
    if provider == "openai":
        return OpenAILLM()
    return FakeLLM()
