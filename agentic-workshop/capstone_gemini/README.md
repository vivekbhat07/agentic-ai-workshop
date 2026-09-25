# Capstone — Gemini Trip Planner (1 hr)

Everything from Sessions 1–3 in one graph, running on **Google Gemini**
(or offline with `FakeTripLLM` — no key needed).

> "Plan 3 days in Tokyo on a 30000 INR budget"

## What's new compared to the Travel Helper

| Concept | Where | What to notice |
|---------|-------|----------------|
| **LLM supervisor** | `nodes.supervisor` | Gemini proposes the next worker as a validated `Route` |
| **Policy guard** | `nodes.enforce_policy` | Code enforces prerequisites, no re-runs, a turn limit — the LLM can't skip ahead |
| **Reducers** | `state.py` | `trace` (operator.add) and `findings` (dict merge): nodes return only their own piece |
| **Critic / revise loop** | `nodes.itinerary_worker` + `critique` | Business rules the schema can't express (over budget, wrong day count) are fed back, max 2 attempts |
| **Human-in-the-loop** | `nodes.review` | `interrupt()` pauses the graph; `Command(resume=...)` continues it |
| **Checkpointing** | `graph.py` | `MemorySaver` + `thread_id` keeps the paused run; `get_state()` inspects it |
| **Gemini error mapping** | `llm.GeminiErrorAdapter` | HTTP 429/5xx → `TransientLLMError` (retry), 400/401/403/404 → `PermanentLLMError` (fail fast) |

```
START -> intake -> supervisor --(route)--> weather_worker   --+
                      ^                    budget_worker    --+--> supervisor
                      |                    itinerary_worker --+
                      |                    review --(approve)--> finalize -> END
                      +---- itinerary_worker <--(changes requested, max 2)
```

Reuses, **without modifying**: `travel_agent.tools`, `travel_agent.structured`,
`reliability.retry` / `ReliableLLM` / guardrails.

## Run it

```bash
# from capstone_gemini/ (venv active)
export PYTHONPATH=.:../session2_workflows:../session3_testing
# Windows PowerShell:  $env:PYTHONPATH=".;..\session2_workflows;..\session3_testing"

python run.py                                            # interactive review
python run.py "Plan 2 days in Paris on a 300 EUR budget" --auto-approve
python run.py "Plan 2 days in Atlantis on a 300 EUR budget"   # weather fails, plan still made
python run.py "ignore previous instructions"             # blocked before any LLM call

# Use real Gemini
export GEMINI_API_KEY=...        # optional: GEMINI_MODEL=gemini-3.8-flash
python run.py
```

Expected (FakeTripLLM, default request):
```
  intake: Tokyo, 3 days, 30000 INR
  supervisor -> weather
  weather_worker: ok
  supervisor -> budget
  budget_worker: $120.0/day
  supervisor -> itinerary
  itinerary_worker: ok after 2 attempt(s), $108.0/day
  supervisor -> finish

--- DRAFT (paused at review) ---
  Day 1: Senso-ji at sunrise
  ...
Approve? [y] or type what to change:
```

Tests (from the repo root): `pytest capstone_gemini -v` → 36 passed, no network.

## Capstone activities

Timing: 10 min concepts · 10 min walkthrough & demo · 25 min Activity A · 10 min Activity B · 5 min wrap-up.

**A — Extend the graph (25 min, fully offline)**
1. In a test, script the supervisor to always answer `"itinerary"`. Confirm the trace shows
   `policy override` and weather/budget still run first.
2. Delete the `MAX_TURNS` check in `enforce_policy`. Which test fails?
3. Add a `visa` worker (fake data: which passports need a visa for which city): add it to
   `NextStep`, `WORKERS`, `PREREQS` and the graph edges.
4. Make `itinerary` depend on it. Write one unit test and one graph test.

Done when: `pytest` is green and the trace shows your visa worker.

**B — Go real on Gemini (10 min, needs `GEMINI_API_KEY`)**
1. Set `GEMINI_API_KEY` in `.env` and run the same request. Compare the trace with the fake.
2. Pass the Pydantic schema to Gemini (`response_schema=Route` in `GenerateContentConfig`) —
   do repair retries drop?
3. Stretch: swap `MemorySaver` for `SqliteSaver` (`pip install langgraph-checkpoint-sqlite`)
   so a paused review survives a restart.

Done when: a real Gemini plan passes your review.

## Key ideas
- **The LLM proposes, code disposes.** Put invariants in pure functions you can unit test.
- **Reducers** remove a whole class of "I overwrote the list" bugs.
- **Pausing needs a checkpointer.** Human review is just state that waits.
- **Classify provider errors at the edge**, so the rest of the system speaks one error language.
