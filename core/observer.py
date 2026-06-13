"""
Observer: live health snapshot and trajectory analysis for Agent OS.
Answers the question: "is my agent learning, drifting, or stagnating?"
"""

from collections import defaultdict

from core.policy_cache import policy_cache_health


class Observer:
    def __init__(self, memory, policy_cache, planner):
        self.memory = memory
        self.policy_cache = policy_cache
        self.planner = planner

    def snapshot(self):
        rows = self.memory.conn.execute(
            "SELECT reward, cost, success FROM episodes ORDER BY id DESC LIMIT 20"
        ).fetchall()

        n = len(rows)
        if n == 0:
            return {"status": "no episodes yet"}

        success_rate = sum(r[2] for r in rows) / n
        avg_reward = sum(r[0] for r in rows) / n
        avg_cost = sum(r[1] for r in rows) / n

        trend = "insufficient data"
        if n >= 10:
            recent = sum(r[0] for r in rows[:5]) / 5
            older = sum(r[0] for r in rows[5:10]) / 5
            delta = recent - older
            trend = "improving" if delta > 0.05 else "degrading" if delta < -0.05 else "stable"

        rules = self.policy_cache.get_all_rules()
        cache_h = policy_cache_health(rules)

        return {
            "episodes_sampled": n,
            "success_rate": round(success_rate, 3),
            "avg_reward": round(avg_reward, 3),
            "avg_cost": round(avg_cost, 3),
            "reward_trend": trend,
            "sim_calibration_accuracy": round(self.planner.calibrator.accuracy, 3),
            "calibration_window": len(self.planner.calibrator._records),
            "policy_cache_health": round(cache_h, 3),
            "active_rules": len(self.policy_cache.get_rules("active")),
            "quarantined_rules": len(self.policy_cache.get_rules("quarantine")),
        }

    def trajectory_clusters(self, top_n=3):
        """Group recent episodes by action prefix to surface dominant strategies."""
        rows = self.memory.conn.execute(
            "SELECT action, reward, success FROM episodes ORDER BY id DESC LIMIT 50"
        ).fetchall()

        by_prefix = defaultdict(list)
        for action, reward, success in rows:
            prefix = action.split(":")[0] if action and ":" in action else "unknown"
            by_prefix[prefix].append((reward, bool(success)))

        clusters = {}
        for prefix, items in by_prefix.items():
            n = len(items)
            avg_r = sum(r for r, _ in items) / n
            sr = sum(s for _, s in items) / n
            clusters[prefix] = {
                "count": n,
                "avg_reward": round(avg_r, 3),
                "success_rate": round(sr, 3),
            }

        # Rank by count × avg_reward: dominant AND effective strategies first.
        return dict(
            sorted(clusters.items(), key=lambda kv: -kv[1]["count"] * kv[1]["avg_reward"])[:top_n]
        )
