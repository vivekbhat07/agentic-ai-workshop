# Agentic Software Engineering — Day 1 Workshop (6 hrs)

Companion code for the slide deck `Agentic_Software_Engineering_Day1.pptx`.

| Session | Topic | Folder |
|---------|-------|--------|
| 1 (2 h) | Foundations: state, control flow, orchestration, SDKs | `session1_foundations/` |
| 2 (2 h) | Stateful workflows, structured outputs, planner-executor & supervisor-worker (LangGraph) | `session2_workflows/` |
| 3 (2 h) | Unit tests, retries, guardrails, lint & type checking | `session3_testing/` |
| Capstone (1 h) | **Gemini Trip Planner**: LLM supervisor, reducers, budget critic, checkpointing, human-in-the-loop | `capstone_gemini/` |

Each folder has its own README with run commands, expected output and exercises.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # optional; leave the API keys empty to run offline

cd session1_foundations && python -m sample_agent.main && cd ..
cd session2_workflows && python run.py "What's the weather in Paris and 200 USD to EUR?" && cd ..
pytest -v                            # 66 tests: Session 3 (30) + capstone (36)

# Capstone (Linux/macOS)
cd capstone_gemini && PYTHONPATH=.:../session2_workflows:../session3_testing python run.py
```

## Requirements
- Python 3.10+
- No API key needed: every session runs with a deterministic `FakeLLM`.
- To use a real model, set `GEMINI_API_KEY` or `OPENAI_API_KEY` in `.env`.
  `LLM_PROVIDER=fake|gemini|openai` forces a choice. No code changes either way.

## Structure
```
agentic-workshop/
├── README.md, requirements.txt, pyproject.toml, .env.example, .gitignore
├── session1_foundations/
│   └── sample_agent/        state.py · tools.py · llm.py · agent.py · main.py
├── session2_workflows/
│   ├── travel_agent/        schemas · state · tools · llm · structured · nodes · graph
│   ├── run.py
│   └── supervisor_demo.py
├── session3_testing/
│   ├── reliability/         errors · retry · reliable_llm · guardrails · safe_agent
│   ├── tests/               conftest + 6 test files (30 cases)
│   └── demo.py
└── capstone_gemini/
    ├── trip_planner/        schemas · state · llm · nodes · graph
    ├── trip_tests/          conftest + 5 test files (36 cases)
    └── run.py
```
