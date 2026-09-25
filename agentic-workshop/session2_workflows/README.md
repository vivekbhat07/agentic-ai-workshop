# Session 2 — Designing Agentic Workflows & State Management (2 hrs)

We build **Travel Helper**, a stateful **planner → executor → responder** agent in **LangGraph**,
with every LLM reply validated by **Pydantic** (structured outputs).

It runs fully **offline** using `FakeLLM`. Set `GEMINI_API_KEY` (or `OPENAI_API_KEY`) in `.env` to
use a real model — no code changes needed. `pick_provider()` in `llm.py` decides which one you get.

## The graph

```
START ─► planner ─► executor ─┐
             │          ▲     │ more steps?  yes → executor (loop)
             │          └─────┘              no  → responder
             └── empty plan ─────────────────────► responder ─► END
```

## Files — read them in this order

| File | Concept | What happens there |
|------|---------|--------------------|
| `travel_agent/schemas.py` | Structured outputs | Pydantic models `Plan`, `ToolCall`, `StepResult`, `FinalAnswer`. Constraints like `confidence` between 0 and 1 and max 5 steps. |
| `travel_agent/state.py` | State management | `AgentState` TypedDict — the single shared object all nodes read. |
| `travel_agent/tools.py` | Tools | Deterministic functions: weather, currency, safe calculator (no `eval`). |
| `travel_agent/llm.py` | LLM abstraction | `LLMClient` protocol, `FakeLLM` (offline), `GeminiLLM` and `OpenAILLM` (JSON mode), `pick_provider()`. |
| `travel_agent/structured.py` | Validation + repair | Validate JSON → if invalid, feed the error back to the LLM and retry (bounded). |
| `travel_agent/nodes.py` | Nodes + routing | `planner`, `executor` (one step per call), `responder`, and the routing functions. |
| `travel_agent/graph.py` | Workflow wiring | `StateGraph`, nodes, normal + conditional edges, `compile()`. |
| `run.py` | Entry point | Streams each node's state update so you can watch the state evolve. |
| `supervisor_demo.py` | Supervisor–worker pattern | A supervisor routes to specialist workers that report back. |

## Run it

From `session2_workflows/` (venv active):

```bash
python run.py "What's the weather in Paris and 200 USD to EUR?"
```

Expected (FakeLLM):
```
--- planner ---
  plan: [ToolCall(tool='get_weather', args={'city': 'Paris'}), ToolCall(tool='convert_currency', ...)]
  current_step: 0
  results: []
--- executor ---
  results: [StepResult(tool='get_weather', ok=True, output={'city': 'Paris', 'temp_c': 18, ...})]
  current_step: 1
--- executor ---
  results: [..., StepResult(tool='convert_currency', ok=True, output=185.19)]
  current_step: 2
--- responder ---
  answer: answer='Paris is 18°C and cloudy. convert_currency result: 185.19.' tools_used=[...] confidence=1.0
```

Try the other cases:
```bash
python run.py "weather in Atlantis"        # tool fails -> ok=False, agent still answers
python run.py "tell me a joke"             # empty plan -> goes straight to responder
python run.py "calculate (12 + 8) * 3"
python supervisor_demo.py
```

## Workshop activities

**Activity A — Stateful workflow (≈35 min)**
1. Run `run.py` and trace which node wrote which state key.
2. Add a new tool `get_timezone(city)` in `tools.py`, add it to `TOOLS` and to `ToolName` in `schemas.py`.
3. Teach `FakeLLM._plan` to detect "time in <city>".

**Activity B — Structured output validation (≈25 min)**
1. In a Python shell, try `FinalAnswer.model_validate_json('{"answer": "hi", "confidence": 1.7}')`. Read the error.
2. Make `FakeLLM._respond` return `confidence: 2` once — watch `generate_structured` retry, then fail after 2 attempts.
3. Add a rule to `Plan`: no duplicate tool calls (use a `@model_validator`).

## Key ideas to remember
- Nodes **return updates**; they don't mutate shared state.
- Control flow lives in **edges**, not hidden inside prompts.
- LLM output is **untrusted input** — validate it before using it.
- Always bound loops (max plan length, max repair attempts).
