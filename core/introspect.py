"""
Introspector: behavioral analysis engine.

Answers questions the agent cannot answer about itself from within a single
session: Has my behavior drifted? Am I contradicting myself? Why do I fail?
"""

from collections import Counter, defaultdict


class Introspector:
    def __init__(self, memory, policy_cache):
        self.memory = memory
        self.policy_cache = policy_cache

    def behavioral_drift(self) -> dict:
        """Compare action-type distribution in the earliest vs most recent episodes."""
        rows = self.memory.conn.execute(
            "SELECT action FROM episodes ORDER BY id"
        ).fetchall()

        if len(rows) < 10:
            return {"status": "need 10+ episodes"}

        split = max(5, len(rows) // 4)
        early  = [_prefix(r[0]) for r in rows[:split]]
        recent = [_prefix(r[0]) for r in rows[-split:]]

        early_c, recent_c = Counter(early), Counter(recent)
        drift = {}
        for p in set(early_c) | set(recent_c):
            e = early_c.get(p, 0) / len(early)
            r = recent_c.get(p, 0) / len(recent)
            if abs(r - e) > 0.05:
                drift[p] = {
                    "early":   round(e, 3),
                    "recent":  round(r, 3),
                    "delta":   round(r - e, 3),
                    "trend":   "↑" if r > e else "↓",
                }

        return {"episodes": len(rows), "window": split, "drift": drift}

    def contradictions(self, threshold=0.6) -> list[dict]:
        """Find pairs of similar inputs that led to different action types."""
        rows = self.memory.conn.execute(
            "SELECT user_input, action, success FROM episodes ORDER BY id DESC LIMIT 100"
        ).fetchall()

        found = []
        for i, (inp_a, act_a, ok_a) in enumerate(rows):
            for inp_b, act_b, ok_b in rows[i + 1: i + 25]:
                sim = _jaccard(inp_a, inp_b)
                if sim >= threshold and _prefix(act_a) != _prefix(act_b):
                    found.append({
                        "similarity":  round(sim, 3),
                        "input_a":     inp_a[:70],
                        "action_a":    act_a[:60],
                        "success_a":   bool(ok_a),
                        "input_b":     inp_b[:70],
                        "action_b":    act_b[:60],
                        "success_b":   bool(ok_b),
                    })
                    if len(found) >= 5:
                        return found
        return found

    def failure_root_causes(self) -> dict:
        """Group recent failures by action type and surface example outcomes."""
        rows = self.memory.conn.execute(
            "SELECT action, outcome, user_input FROM episodes "
            "WHERE success=0 ORDER BY id DESC LIMIT 60"
        ).fetchall()

        by_type: dict[str, list] = defaultdict(list)
        for action, outcome, user_input in rows:
            by_type[_prefix(action)].append({
                "input":   user_input[:60],
                "outcome": outcome[:80],
            })

        return {
            p: {"failures": len(v), "examples": v[:3]}
            for p, v in sorted(by_type.items(), key=lambda x: -len(x[1]))
        }

    def self_diagnosis(self) -> str:
        row = self.memory.conn.execute(
            "SELECT COUNT(*), AVG(reward), AVG(cost), "
            "CAST(SUM(success) AS REAL)/COUNT(*) FROM episodes"
        ).fetchone()

        if not row or row[0] == 0:
            return "No episodes recorded yet."

        total, avg_r, avg_c, sr = row
        lines = [
            "╔══ Agent Self-Diagnosis ══════════════════════════════╗",
            f"  Episodes      : {total}",
            f"  Success rate  : {sr:.1%}",
            f"  Avg reward    : {avg_r:.3f}",
            f"  Avg cost      : {avg_c:.3f}",
        ]

        drift = self.behavioral_drift()
        if drift.get("drift"):
            lines.append("\n  ── Behavioral Drift ──────────────────────────────────")
            for behavior, info in drift["drift"].items():
                lines.append(
                    f"  {behavior:8s} {info['trend']}  "
                    f"{info['early']:.0%} → {info['recent']:.0%}  (Δ {info['delta']:+.0%})"
                )
        else:
            lines.append("\n  No significant behavioral drift detected.")

        causes = self.failure_root_causes()
        if causes:
            lines.append("\n  ── Failure Root Causes ───────────────────────────────")
            for prefix, info in causes.items():
                lines.append(f"  {prefix}: {info['failures']} failures")
                for ex in info["examples"][:2]:
                    lines.append(f"    > {ex['input']}")
                    lines.append(f"      → {ex['outcome']}")

        rules = self.policy_cache.get_all_rules()
        active = [r for r in rules if r["status"] == "active"]
        quarantined = [r for r in rules if r["status"] == "quarantine"]
        lines.append("\n  ── Policy Cache ──────────────────────────────────────")
        lines.append(f"  Active: {len(active)}   Quarantined: {len(quarantined)}")
        if active:
            best = max(active, key=lambda r: r["success_rate"])
            lines.append(
                f"  Best rule: {best['action']}  "
                f"(sr={best['success_rate']:.2f}, used={best['usage_count']}x)"
            )

        lines.append("╚══════════════════════════════════════════════════════╝")
        return "\n".join(lines)


# ── helpers ───────────────────────────────────────────────────────────────────

def _prefix(action: str) -> str:
    return action.split(":")[0] if action and ":" in action else "unknown"


def _jaccard(a: str, b: str) -> float:
    set_a = set(a.lower().split())
    set_b = set(b.lower().split())
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)
