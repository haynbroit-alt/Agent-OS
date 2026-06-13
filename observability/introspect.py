"""Self-diagnosis: contradictions, failure root causes, full report."""

from collections import defaultdict
from observability import drift as drift_mod


def contradictions(memory, threshold: float = 0.6) -> list[dict]:
    rows = memory.conn.execute(
        "SELECT user_input, action, success FROM episodes ORDER BY id DESC LIMIT 100"
    ).fetchall()
    found = []
    for i, (ia, aa, oa) in enumerate(rows):
        for ib, ab, ob in rows[i + 1: i + 25]:
            sim = _jaccard(ia, ib)
            if sim >= threshold and _prefix(aa) != _prefix(ab):
                found.append({
                    "similarity": round(sim, 3),
                    "input_a": ia[:70], "action_a": aa[:60], "success_a": bool(oa),
                    "input_b": ib[:70], "action_b": ab[:60], "success_b": bool(ob),
                })
                if len(found) >= 5:
                    return found
    return found


def failure_causes(memory) -> dict:
    rows = memory.conn.execute(
        "SELECT action, outcome, user_input FROM episodes WHERE success=0 ORDER BY id DESC LIMIT 60"
    ).fetchall()
    by_type: dict = defaultdict(list)
    for action, outcome, inp in rows:
        by_type[_prefix(action)].append({"input": inp[:60], "outcome": outcome[:80]})
    return {p: {"failures": len(v), "examples": v[:3]}
            for p, v in sorted(by_type.items(), key=lambda x: -len(x[1]))}


def self_diagnosis(memory, policy) -> str:
    row = memory.conn.execute(
        "SELECT COUNT(*), AVG(reward), AVG(cost), "
        "CAST(SUM(success) AS REAL)/COUNT(*) FROM episodes"
    ).fetchone()
    if not row or row[0] == 0:
        return "No episodes recorded yet."

    total, avg_r, avg_c, sr = row
    lines = [
        "╔══ Execution Graph OS — Self-Diagnosis ══════════════════╗",
        f"  Episodes      : {total}",
        f"  Success rate  : {sr:.1%}",
        f"  Avg reward    : {avg_r:.3f}",
        f"  Avg cost      : {avg_c:.3f}",
    ]

    d = drift_mod.detect(memory)
    if d.get("drift"):
        lines.append("\n  ── Behavioral Drift ──────────────────────────────────")
        for b, info in d["drift"].items():
            lines.append(f"  {b:8s} {info['trend']}  "
                         f"{info['early']:.0%} → {info['recent']:.0%}  (Δ {info['delta']:+.0%})")
    else:
        lines.append("\n  No significant behavioral drift detected.")

    causes = failure_causes(memory)
    if causes:
        lines.append("\n  ── Failure Root Causes ───────────────────────────────")
        for p, info in causes.items():
            lines.append(f"  {p}: {info['failures']} failures")
            for ex in info["examples"][:2]:
                lines.append(f"    > {ex['input']}")
                lines.append(f"      → {ex['outcome']}")

    rules = policy.store.get_all()
    active = [r for r in rules if r["status"] == "active"]
    quarantined = [r for r in rules if r["status"] == "quarantine"]
    lines.append("\n  ── Policy Routing ────────────────────────────────────")
    lines.append(f"  Active rules: {len(active)}   Quarantined: {len(quarantined)}")
    if active:
        best = max(active, key=lambda r: r["success_rate"])
        lines.append(f"  Best: {best['action']}  (sr={best['success_rate']:.2f}, n={best['usage_count']})")

    lines.append("╚═════════════════════════════════════════════════════════╝")
    return "\n".join(lines)


def _jaccard(a: str, b: str) -> float:
    sa, sb = set(a.lower().split()), set(b.lower().split())
    return len(sa & sb) / len(sa | sb) if sa or sb else 0.0


def _prefix(action: str) -> str:
    return action.split(":")[0] if action and ":" in action else "unknown"
