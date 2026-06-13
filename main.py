import argparse

from core.llm import LLM
from core.memory import Memory
from core.planner import Planner
from core.tools import Tools
from core.loop import run_agent
from core.policy_cache import PolicyCache, run_audit
from core.observer import Observer
from core.decision_log import tail as log_tail
from core.utils import pretty

parser = argparse.ArgumentParser(description="Agent OS — local-first autonomous agent")
parser.add_argument("--dry-run", action="store_true",
                    help="Plan actions without executing them")
args = parser.parse_args()

llm = LLM()
memory = Memory()
policy_cache = PolicyCache(conn=memory.conn)
planner = Planner(llm)
tools = Tools()
observer = Observer(memory, policy_cache, planner)

mode = "[DRY-RUN] " if args.dry_run else ""
print(f"Agent OS ready. {mode}Shell allowlist: {sorted(tools.allowed)}")
print("Commands: :obs  :clusters  :audit  :cache  :log  :dry <query>  :quit")

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
    if q == ":log":
        entries = log_tail(20)
        print(pretty(entries))
        continue

    # Per-query dry-run: ":dry list files"
    dry = args.dry_run
    if q.startswith(":dry "):
        q = q[5:].strip()
        dry = True

    result = run_agent(q, memory, planner, tools, llm,
                       policy_cache=policy_cache, dry_run=dry)
    print(pretty(result))
