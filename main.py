import argparse

from core.llm import LLM
from core.memory import Memory
from core.planner import Planner
from core.tools import Tools
from core.loop import run_agent
from core.policy_cache import PolicyCache, run_audit, bootstrap_from_episodes
from core.observer import Observer
from core.meta_learner import MetaLearner
from core.introspect import Introspector
from core.counterfactual import counterfactual
from core.decision_log import tail as log_tail
from core.utils import pretty

parser = argparse.ArgumentParser(description="Agent OS — local-first autonomous agent")
parser.add_argument("--dry-run", action="store_true",
                    help="Plan actions without executing them")
args = parser.parse_args()

llm          = LLM()
memory       = Memory()
policy_cache = PolicyCache(conn=memory.conn)
planner      = Planner(llm)
tools        = Tools()
observer     = Observer(memory, policy_cache, planner)
meta_learner = MetaLearner()
introspector = Introspector(memory, policy_cache)

seeded = bootstrap_from_episodes(policy_cache, memory)
meta_learner.fit(memory)

mode = "[DRY-RUN] " if args.dry_run else ""
print(f"Agent OS ready. {mode}Allowlist: {sorted(tools.allowed)}")
if seeded:
    print(f"  {seeded} policy rule(s) bootstrapped from past episodes.")
ml = meta_learner.stats()
if ml["bypassable_patterns"]:
    print(f"  {ml['bypassable_patterns']} pattern(s) ready for LLM bypass.")
print("Commands: :obs  :clusters  :audit  :cache  :log  :diagnose  :meta")
print("          :cf <action>  :dry <query>  :quit")

_last_query = ""

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
        print(pretty(log_tail(20)))
        continue
    if q == ":diagnose":
        print(introspector.self_diagnosis())
        continue
    if q == ":meta":
        print(pretty(meta_learner.stats()))
        continue
    if q.startswith(":cf "):
        alt = q[4:].strip()
        if not _last_query:
            print("No previous query to compare against. Ask something first.")
        else:
            print(pretty(counterfactual(_last_query, alt, memory, planner)))
        continue

    dry = args.dry_run
    if q.startswith(":dry "):
        q = q[5:].strip()
        dry = True

    _last_query = q
    result = run_agent(q, memory, planner, tools, llm,
                       policy_cache=policy_cache, dry_run=dry,
                       meta_learner=meta_learner)
    print(pretty(result))
