"""Behavioral drift tracking: detect shifts in action-type distribution over time."""

from collections import Counter


def detect(memory, min_episodes: int = 10) -> dict:
    rows = memory.conn.execute("SELECT action FROM episodes ORDER BY id").fetchall()
    if len(rows) < min_episodes:
        return {"status": f"need {min_episodes}+ episodes (have {len(rows)})"}

    split = max(5, len(rows) // 4)
    early  = [_prefix(r[0]) for r in rows[:split]]
    recent = [_prefix(r[0]) for r in rows[-split:]]
    ec, rc = Counter(early), Counter(recent)

    drift = {}
    for p in set(ec) | set(rc):
        e = ec.get(p, 0) / len(early)
        r = rc.get(p, 0) / len(recent)
        if abs(r - e) > 0.05:
            drift[p] = {"early": round(e, 3), "recent": round(r, 3),
                        "delta": round(r - e, 3), "trend": "↑" if r > e else "↓"}

    return {"total_episodes": len(rows), "window": split, "drift": drift}


def _prefix(action: str) -> str:
    return action.split(":")[0] if action and ":" in action else "unknown"
