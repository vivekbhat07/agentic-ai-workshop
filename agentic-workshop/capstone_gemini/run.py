"""Run from capstone_gemini/ (PYTHONPATH set as in the README):

    python run.py "Plan 3 days in Tokyo on a 30000 INR budget"
    python run.py "Plan 2 days in Paris on a 300 EUR budget" --auto-approve

Uses Gemini if GEMINI_API_KEY is set, otherwise the offline FakeTripLLM.
"""
import sys
import uuid

from dotenv import load_dotenv
from langgraph.types import Command

from reliability.guardrails import GuardrailViolation
from travel_agent.structured import StructuredOutputError
from trip_planner.graph import build_graph

load_dotenv()

args = [a for a in sys.argv[1:] if not a.startswith("--")]
request = " ".join(args) or "Plan 3 days in Tokyo on a 30000 INR budget"
auto_approve = "--auto-approve" in sys.argv

app = build_graph()
config = {"configurable": {"thread_id": str(uuid.uuid4())}}  # one checkpoint thread per trip
payload: object = {"request": request}
shown = 0

while True:
    try:
        app.invoke(payload, config)
    except GuardrailViolation as exc:
        sys.exit(f"Blocked by guardrail: {exc}")
    except StructuredOutputError:
        sys.exit("Sorry, I couldn't understand that trip request. Try: "
                 "'Plan 3 days in Tokyo on a 30000 INR budget'")

    snap = app.get_state(config)                 # read the checkpoint
    for line in snap.values.get("trace", [])[shown:]:
        print("  " + line)
    shown = len(snap.values.get("trace", []))

    if not snap.next:                            # graph reached END
        break

    # Paused inside `review` -> show the draft and ask a human.
    itin = snap.values["itinerary"]
    print(f"\n--- DRAFT (paused at {snap.next[0]}) ---")
    for d in itin.days:
        print(f"  Day {d.day}: {', '.join(d.activities)}")
    print(f"  ~${itin.cost_per_day_usd}/day. {itin.notes}\n")
    answer = "y" if auto_approve else input("Approve? [y] or type what to change: ").strip()
    if answer.lower() in ("", "y", "yes"):
        payload = Command(resume={"approve": True})
    else:
        payload = Command(resume={"approve": False, "feedback": answer})

print("\n" + snap.values["final"])
