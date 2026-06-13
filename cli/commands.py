"""
REPL command handlers.  Each returns a string to print, or None to skip output.
"""

import json
from graph.visualizer import to_json, to_mermaid
from observability import introspect, counterfactual, drift as drift_mod
from observability.logger import tail as log_tail


def pretty(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, default=str)


def cmd_obs(sched) -> str:
    rows = sched.memory.conn.execute(
        "SELECT reward, cost, success FROM episodes ORDER BY id DESC LIMIT 20"
    ).fetchall()
    n = len(rows)
    if n == 0:
        return "No episodes yet."
    sr  = sum(r[2] for r in rows) / n
    ar  = sum(r[0] for r in rows) / n
    ac  = sum(r[1] for r in rows) / n
    trend = "insufficient data"
    if n >= 10:
        re = sum(r[0] for r in rows[:5]) / 5
        ol = sum(r[0] for r in rows[5:10]) / 5
        trend = "improving" if re > ol + 0.05 else "degrading" if re < ol - 0.05 else "stable"
    rules = sched.policy.store.get_all()
    return pretty({
        "episodes": n,
        "success_rate": round(sr, 3),
        "avg_reward": round(ar, 3),
        "avg_cost": round(ac, 3),
        "reward_trend": trend,
        "sim_calibration": round(sched.planner.calibrator.accuracy, 3),
        "active_rules": sum(1 for r in rules if r["status"] == "active"),
        "quarantined_rules": sum(1 for r in rules if r["status"] == "quarantine"),
    })


def cmd_graph(sched) -> str:
    return to_mermaid(sched.graph) + "\n\n" + to_json(sched.graph)


def cmd_clusters(sched) -> str:
    from collections import defaultdict
    rows = sched.memory.conn.execute(
        "SELECT action, reward, success FROM episodes ORDER BY id DESC LIMIT 50"
    ).fetchall()
    by = defaultdict(list)
    for action, reward, success in rows:
        p = action.split(":")[0] if action and ":" in action else "unknown"
        by[p].append((reward, bool(success)))
    clusters = {}
    for p, items in by.items():
        n = len(items)
        clusters[p] = {
            "count": n,
            "avg_reward": round(sum(r for r, _ in items) / n, 3),
            "success_rate": round(sum(s for _, s in items) / n, 3),
        }
    top3 = dict(sorted(clusters.items(), key=lambda x: -x[1]["count"] * x[1]["avg_reward"])[:3])
    return pretty(top3)


def cmd_audit(sched) -> str:
    from modules.policy import audit
    return pretty(sched.policy.audit())


def cmd_cache(sched) -> str:
    return pretty(sched.policy.store.get_all())


def cmd_log(_sched) -> str:
    return pretty(log_tail(20))


def cmd_diagnose(sched) -> str:
    return introspect.self_diagnosis(sched.memory, sched.policy)


def cmd_meta(sched) -> str:
    return pretty(sched.policy.meta.stats())


def cmd_drift(sched) -> str:
    return pretty(drift_mod.detect(sched.memory))


def cmd_registry(sched) -> str:
    return pretty(sched.registry.to_dict())


def cmd_cf(sched, last_query: str, alt_action: str) -> str:
    if not last_query:
        return "No previous query. Ask something first."
    return pretty(counterfactual.run(last_query, alt_action, sched.memory, sched.planner))
