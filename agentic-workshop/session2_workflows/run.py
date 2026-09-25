"""Run from session2_workflows/:  python run.py "What's the weather in Paris and 200 USD to EUR?" """
import sys

from dotenv import load_dotenv

from travel_agent.graph import build_graph

load_dotenv()

question = " ".join(sys.argv[1:]) or "What's the weather in Tokyo and 150 USD to JPY?"
app = build_graph()

# stream() yields one update per node, so we can watch the state change.
for update in app.stream({"question": question}):
    for node, change in update.items():
        print(f"--- {node} ---")
        for key, value in change.items():
            print(f"  {key}: {value}")
