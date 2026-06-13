from core.llm import LLM
from core.memory import Memory
from core.planner import Planner
from core.tools import Tools
from core.loop import run_agent
from core.policy_cache import PolicyCache, run_audit
from core.observer import Observer
from core.utils import pretty

llm = LLM()
memory = Memory()
policy_cache = PolicyCache(conn=memory.conn)
planner = Planner(llm)
tools = Tools()
observer = Observer(memory, policy_cache, planner)

print("Agent OS ready.")
print("Commands: :obs  :clusters  :audit  :cache  :quit")

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
    if q == ":obs":
        print(pretty(observer.snapshot()))
        continue
    if q == ":clusters":
        print(pretty(observer.trajectory_clusters()))
        continue
    if q == ":audit":
        print(pretty(run_audit(policy_cache)))
        continue
    if q == ":cache":
        print(pretty(policy_cache.get_all_rules()))
        continue

    result = run_agent(q, memory, planner, tools, llm, policy_cache=policy_cache)
    print(pretty(result))
