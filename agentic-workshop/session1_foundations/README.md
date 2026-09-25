# Session 1 — Foundations of Agentic Software Engineering (2 hrs)

## Goals
- Understand what makes a system "agentic": **state**, **control flow**, **orchestration**, **tools**.
- Set up a clean Python project (venv + Git) that we reuse all day.
- Read a small agent codebase and name each architectural part.

## Activity A — Project setup (≈25 min)

From the repo root (`agentic-workshop/`):

```bash
# 1. Virtual environment (isolated Python for this project)
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Dependencies
pip install -r requirements.txt

# 3. Secrets (optional — the workshop runs offline without a key)
cp .env.example .env

# 4. Git
git init
git add .
git commit -m "Initial project structure"
```

Check: `git status` should NOT list `.venv/` or `.env` (they are in `.gitignore`).

## Activity B — Explore the sample agent (≈25 min)

Run it:
```bash
cd session1_foundations
python -m sample_agent.main
```

Expected output:
```
step: add({'a': 2, 'b': 3}) = 5
step: multiply({'a': 5.0, 'b': 4}) = 20.0
answer: 20.0
```

Now fill in this table by reading the code:

| Component        | Question to answer                              | File |
|------------------|--------------------------------------------------|------|
| State            | What does the agent remember between steps?      | ?    |
| Tools            | What actions can it take? How is that limited?   | ?    |
| LLM / decision   | Who decides the next step?                        | ?    |
| Control flow     | Where is the loop? How does it stop?             | ?    |
| Orchestration    | What connects decision → tool → state update?    | ?    |
| Safety limit     | What stops an infinite loop?                     | ?    |

<details><summary>Answers</summary>

State → `state.py` · Tools → `tools.py` (the `TOOLS` registry) · Decision → `llm.py` ·
Control flow → the `while` loop in `agent.py` · Orchestration → `run_agent()` in `agent.py` ·
Safety limit → `MAX_STEPS` in `agent.py`.
</details>

## Stretch (if time)
1. Add a `subtract` tool and make the goal `(2 + 3) * 4 - 1`.
2. Set `MAX_STEPS = 1` — what happens to `final_answer`? Why is that important?
