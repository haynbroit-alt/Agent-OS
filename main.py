from core.llm import LLM
from core.memory import Memory
from core.planner import Planner
from core.tools import Tools
from core.loop import run_agent
from core.policy_cache import PolicyCache, run_audit
from core.utils import pretty

llm = LLM()
memory = Memory()
policy_cache = PolicyCache(conn=memory.conn)
planner = Planner(llm)
tools = Tools()

print("Agent OS ready. Type 'exit' or 'quit' to stop.")
print("Special commands: :audit  :cache  :quit")

while True:
    try:
        q = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nShutting down.")
        break

    if not q:
        continue
    if q in ("exit", "quit", ":quit"):
        break
    if q == ":audit":
        report = run_audit(policy_cache)
        print(pretty(report))
        continue
    if q == ":cache":
        rules = policy_cache.get_all_rules()
        print(pretty(rules))
        continue

    result = run_agent(q, memory, planner, tools, llm, policy_cache=policy_cache)
    print(pretty(result))
