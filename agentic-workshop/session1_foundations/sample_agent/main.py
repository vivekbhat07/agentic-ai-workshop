"""Entry point. Run from session1_foundations/:  python -m sample_agent.main"""
from sample_agent.agent import run_agent

if __name__ == "__main__":
    final = run_agent("compute (2 + 3) * 4")
    for line in final.history:
        print("step:", line)
    print("answer:", final.final_answer)
