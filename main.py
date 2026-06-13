from core.llm import LLM
from core.memory import Memory
from core.planner import Planner
from core.tools import Tools
from core.loop import run_agent
from core.utils import pretty

llm = LLM()
memory = Memory()
planner = Planner(llm)
tools = Tools()

print("Agent OS ready. Type 'exit' or 'quit' to stop.")

while True:
    try:
        q = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nShutting down.")
        break

    if not q:
        continue
    if q in ("exit", "quit"):
        break

    result = run_agent(q, memory, planner, tools, llm)
    print(pretty(result))
