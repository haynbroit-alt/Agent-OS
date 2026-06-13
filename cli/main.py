"""
Execution Graph OS — CLI entry point.

Usage:
    python cli/main.py
    python cli/main.py --dry-run
"""

import argparse
import sys
import os

# Ensure project root is on the path when called as python cli/main.py
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from runtime.scheduler import Scheduler
from cli.commands import (
    pretty,
    cmd_obs, cmd_graph, cmd_clusters, cmd_audit, cmd_cache,
    cmd_log, cmd_diagnose, cmd_meta, cmd_drift, cmd_registry, cmd_cf,
)

HELP = """Commands:
  :obs        Health snapshot
  :graph      Execution graph (Mermaid + JSON)
  :clusters   Dominant action strategies
  :audit      Policy audit + auto-clean
  :cache      Policy rules
  :log        Last 20 decisions
  :diagnose   Full self-diagnosis
  :meta       MetaLearner stats
  :drift      Behavioral drift report
  :registry   Registered modules
  :cf <act>   Counterfactual for last query
  :dry <q>    Plan without executing
  :quit       Exit"""


def main():
    parser = argparse.ArgumentParser(
        prog="egos",
        description="Execution Graph OS — AI runtime with full observability",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Plan actions without executing them")
    args = parser.parse_args()

    print("Execution Graph OS")
    print(f"  mode      : {'dry-run' if args.dry_run else 'exec'}")

    sched = Scheduler()
    seeded = sched.policy.bootstrap(sched.memory)
    sched.policy.meta.fit(sched.memory)

    print(f"  allowlist : {sorted(sched.tools.allowed)}")
    if seeded:
        print(f"  bootstrapped {seeded} policy rule(s) from past episodes")
    ms = sched.policy.meta.stats()
    if ms["bypassable_patterns"]:
        print(f"  {ms['bypassable_patterns']} pattern(s) ready for LLM bypass")
    print(HELP)

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
        if q == ":obs":           print(cmd_obs(sched));            continue
        if q == ":graph":         print(cmd_graph(sched));          continue
        if q == ":clusters":      print(cmd_clusters(sched));       continue
        if q == ":audit":         print(cmd_audit(sched));          continue
        if q == ":cache":         print(cmd_cache(sched));          continue
        if q == ":log":           print(cmd_log(sched));            continue
        if q == ":diagnose":      print(cmd_diagnose(sched));       continue
        if q == ":meta":          print(cmd_meta(sched));           continue
        if q == ":drift":         print(cmd_drift(sched));          continue
        if q == ":registry":      print(cmd_registry(sched));       continue
        if q.startswith(":cf "):
            print(cmd_cf(sched, _last_query, q[4:].strip()))
            continue

        dry = args.dry_run
        if q.startswith(":dry "):
            q, dry = q[5:].strip(), True

        _last_query = q
        result = sched.run(q, dry_run=dry)
        print(pretty(result))


if __name__ == "__main__":
    main()
