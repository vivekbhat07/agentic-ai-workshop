# Session 3 — Testing, Error Handling & Code Quality (2 hrs)

We make the Session 2 **Travel Helper** production-grade: tests, retries, guardrails, lint and types.
The Session 2 code is **not modified** — reliability is added by *wrapping* it.

## Files

| File | Concept | What happens there |
|------|---------|--------------------|
| `reliability/errors.py` | Error classification | `TransientLLMError` (retry) vs `PermanentLLMError` (don't). |
| `reliability/retry.py` | Retries | `@with_retry` decorator: exponential backoff + jitter, max attempts, injectable `sleep`. |
| `reliability/reliable_llm.py` | Wrapper pattern | `ReliableLLM` adds retries to any LLM. `FlakyLLM` simulates failures. |
| `reliability/guardrails.py` | Guardrails | Input: empty / too long / prompt-injection. Output: redact emails & phones. |
| `reliability/safe_agent.py` | Putting it together | `ask()` = input guardrail → graph with retries → output guardrail. |
| `demo.py` | Demo | Normal run, flaky LLM, injection attempt, empty input. |
| `tests/conftest.py` | Fixtures | `StubLLM` (canned replies + records calls), `fake_llm`, `no_sleep`. |
| `tests/test_tools.py` | Unit tests | Pure tools, `parametrize`, `pytest.raises`, injection-safe calculator. |
| `tests/test_schemas_and_structured.py` | Validation tests | Schemas reject bad data; repair loop recovers / gives up. |
| `tests/test_nodes.py` | Component tests | Each node alone with a stub LLM; router logic. |
| `tests/test_graph.py` | Integration tests | Full graph end-to-end with the deterministic `FakeLLM`. |
| `tests/test_retry.py` | Retry tests | Recovers after transient errors, backoff grows 1→2→4, permanent errors not retried. |
| `tests/test_guardrails.py` | Guardrail tests | Bad input blocked, PII redacted. |

## Run it (from the repo root, venv active)

```bash
# Tests (config lives in pyproject.toml)
pytest -v

# Lint + auto-fix, then format
ruff check . --fix
ruff format .

# Type checking
mypy session2_workflows/travel_agent session3_testing/reliability

# Demo (Linux/macOS)
cd session3_testing && PYTHONPATH=.:../session2_workflows python demo.py
# Windows PowerShell:
#   cd session3_testing; $env:PYTHONPATH=".;..\session2_workflows"; python demo.py
```

Expected demo output:
```
WARNING Attempt 1 failed (429 rate limit); retrying in 0.53s
WARNING Attempt 2 failed (429 rate limit); retrying in 1.08s
1) Normal: Tokyo is 24°C and sunny. convert_currency result: 8333.33.
2) Flaky LLM (2 failures, then OK): Paris is 18°C and cloudy.
3) Injection: Sorry, I can't process that: Possible prompt injection detected
4) Empty: Sorry, I can't process that: Empty question
```

## Workshop activities

**Activity A — Unit tests (≈30 min)**
1. Run `pytest -v`; all green.
2. Write tests for the `get_timezone` tool you added in Session 2.
3. Write a test proving `executor` never raises, even when a tool throws `ZeroDivisionError`
   (hint: `calculator("1/0")`).

**Activity B — Retries & error handling (≈30 min)**
1. Change `FlakyLLM(failures=2)` to `failures=3` in `demo.py`. What happens? Why?
2. Add `max_delay` coverage: a test where the 5th delay is capped at `max_delay`.
3. In `OpenAILLM.generate`, map `openai.RateLimitError` / `APITimeoutError` →
   `TransientLLMError` and `AuthenticationError` → `PermanentLLMError`.
4. Run `ruff check .` and `mypy …` — fix anything they report.

## Key ideas to remember
- Test the **deterministic parts** hard; replace the LLM with **stubs/fakes** in tests.
- Retry only **transient** errors, with **backoff**, and a **max** — never forever.
- Guardrails sit on **both sides** of the LLM.
- Lint + types catch bugs before tests even run.
