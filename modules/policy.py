"""
Policy module: combines rule-based routing with LLM bypass (MetaLearner).
Selects the best action without being called a "cache" or a "learner".
It's the routing intelligence of the graph.
"""

import json
import os
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime

import config


# ── Rule storage ───────────────────────────────────────────────────────────────

class RuleStore:
    def __init__(self, conn):
        self.conn = conn
        self._init()

    def _init(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS policy_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT NOT NULL,
                action TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                supporting_episodes TEXT DEFAULT '[]',
                last_used TIMESTAMP,
                success_rate REAL DEFAULT 0.0,
                failure_rate REAL DEFAULT 0.0,
                usage_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def add(self, pattern, action, confidence=0.5):
        self.conn.execute(
            "INSERT INTO policy_cache (pattern, action, confidence, last_used, status) "
            "VALUES (?, ?, ?, ?, 'active')",
            (pattern, action, confidence, datetime.utcnow().isoformat()),
        )
        self.conn.commit()

    def get_active(self):
        return self._fetch("status='active'")

    def get_all(self):
        return self._fetch()

    def _fetch(self, where="1=1"):
        rows = self.conn.execute(
            f"SELECT id, pattern, action, confidence, supporting_episodes, "
            f"last_used, success_rate, failure_rate, usage_count, status "
            f"FROM policy_cache WHERE {where} ORDER BY success_rate DESC"
        ).fetchall()
        return [_row(r) for r in rows]

    def set_status(self, rule_id, status):
        self.conn.execute("UPDATE policy_cache SET status=? WHERE id=?", (status, rule_id))
        self.conn.commit()

    def delete(self, rule_id):
        self.conn.execute("DELETE FROM policy_cache WHERE id=?", (rule_id,))
        self.conn.commit()

    def record_usage(self, rule_id, success):
        row = self.conn.execute(
            "SELECT usage_count, success_rate, failure_rate FROM policy_cache WHERE id=?",
            (rule_id,),
        ).fetchone()
        if not row:
            return
        n, sr, fr = row
        nn = n + 1
        new_sr = (sr * n + (1.0 if success else 0.0)) / nn
        new_fr = (fr * n + (0.0 if success else 1.0)) / nn
        self.conn.execute(
            "UPDATE policy_cache SET usage_count=?, success_rate=?, failure_rate=?, last_used=? WHERE id=?",
            (nn, new_sr, new_fr, datetime.utcnow().isoformat(), rule_id),
        )
        self.conn.commit()


def _row(r):
    keys = ["id", "pattern", "action", "confidence", "supporting_episodes",
            "last_used", "success_rate", "failure_rate", "usage_count", "status"]
    d = dict(zip(keys, r))
    try:
        d["supporting_episodes"] = json.loads(d["supporting_episodes"] or "[]")
    except (json.JSONDecodeError, TypeError):
        d["supporting_episodes"] = []
    return d


# ── MetaLearner bypass ─────────────────────────────────────────────────────────

class MetaLearner:
    _MIN = 3
    _THRESHOLD = 0.75

    def __init__(self):
        self._map: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))

    def _key(self, text: str) -> str:
        words = sorted(w.lower() for w in text.split() if len(w) > 3)
        return " ".join(words[:3])

    def fit(self, memory) -> None:
        rows = memory.conn.execute(
            "SELECT user_input, action, reward FROM episodes WHERE success=1"
        ).fetchall()
        self._map.clear()
        for inp, action, reward in rows:
            self._map[self._key(inp)][action].append(reward)

    def update(self, inp: str, action: str, reward: float, success: bool) -> None:
        if success:
            self._map[self._key(inp)][action].append(reward)

    def should_bypass(self, user_input: str) -> tuple[bool, str | None]:
        key = self._key(user_input)
        best, score = None, 0.0
        for action, rewards in self._map.get(key, {}).items():
            if len(rewards) >= self._MIN:
                avg = sum(rewards) / len(rewards)
                if avg > score:
                    score, best = avg, action
        return (True, best) if best and score >= self._THRESHOLD else (False, None)

    def stats(self) -> dict:
        total = len(self._map)
        bypassable = sum(
            1 for cands in self._map.values()
            if any(
                len(r) >= self._MIN and sum(r) / len(r) >= self._THRESHOLD
                for r in cands.values()
            )
        )
        return {"learned_patterns": total, "bypassable_patterns": bypassable}


# ── Audit functions ────────────────────────────────────────────────────────────

def _health(rule, days_ago=7):
    decay = max(0.1, 1.0 - days_ago / 30)
    h = (0.3 * rule["confidence"]
         + 0.3 * rule["success_rate"]
         - 0.2 * rule["failure_rate"]
         + 0.2 * decay)
    if rule["usage_count"] < 3:
        h -= 0.2
    return max(0.0, min(1.0, h))


def audit(store: RuleStore, days_ago: int = 7) -> dict:
    rules = store.get_all()
    keep, remove, quarantine = [], [], []
    for r in rules:
        h = _health(r, days_ago)
        if r["usage_count"] == 0:
            remove.append(r)
        elif r["confidence"] > 0.85 and r["failure_rate"] > 0.3:
            quarantine.append(r)
        elif days_ago > 14 and r["success_rate"] < 0.5:
            remove.append(r)
        elif h < 0.4:
            quarantine.append(r)
        else:
            keep.append(r)
    for r in remove:
        store.delete(r["id"])
    for r in quarantine:
        store.set_status(r["id"], "quarantine")
    cache_health = (
        sum(_health(r) for r in rules) / len(rules)
        * len(set(r["pattern"] for r in rules)) / len(rules)
    ) if rules else 1.0
    return {
        "kept": len(keep),
        "removed": len(remove),
        "quarantined": len(quarantine),
        "cache_health": round(cache_health, 3),
    }


def bootstrap(store: RuleStore, memory, min_occ: int = 2) -> int:
    rows = memory.conn.execute(
        "SELECT user_input, action, reward FROM episodes WHERE success=1 AND reward >= 0.7"
    ).fetchall()
    counts: Counter = Counter()
    best_action, rewards_map = {}, defaultdict(list)
    for inp, action, reward in rows:
        p = _extract_pattern(inp, action)
        counts[p] += 1
        best_action[p] = action
        rewards_map[p].append(reward)
    existing = {r["pattern"] for r in store.get_active()}
    inserted = 0
    for p, n in counts.items():
        if n >= min_occ and p not in existing:
            avg_r = sum(rewards_map[p]) / len(rewards_map[p])
            conf = min(0.80, 0.50 + avg_r * 0.35 + n * 0.02)
            store.add(p, best_action[p], conf)
            inserted += 1
    return inserted


def _extract_pattern(user_input: str, action: str) -> str:
    prefix = action.split(":")[0] if ":" in action else "unknown"
    words = [w.lower() for w in user_input.split() if len(w) > 3]
    key = " + ".join(words[:2]) if words else user_input[:20]
    return f"{prefix} | {key}"


# ── Policy: the routing brain ──────────────────────────────────────────────────

class Policy:
    def __init__(self, conn):
        self.store  = RuleStore(conn)
        self.meta   = MetaLearner()
        self._memory = None  # injected by Scheduler after Memory is created

    def route(self, state, planner_svc) -> tuple[str, dict]:
        bypass, shortcut = self.meta.should_bypass(state.user_input)
        if bypass:
            return shortcut, {"bypassed": True, "score": None, "sim": {}}

        best, score, best_sim = None, -999.0, {}
        for action in state.candidate_actions:
            sim = planner_svc.simulate(action, state.context_str)
            s   = planner_svc.score(action, sim, self._memory, state.budget_remaining)
            if s > score:
                score, best, best_sim = s, action, sim
        return best, {"bypassed": False, "score": round(score, 3), "sim": best_sim}

    def learn(self, state, planner_svc) -> None:
        self.meta.update(state.user_input, state.best_action,
                         0.8 if state.execution_success else 0.2,
                         state.execution_success)
        planner_svc.calibrator.record(
            state.best_sim.get("success", False), state.execution_success
        )
        if state.execution_success:
            p = _extract_pattern(state.user_input, state.best_action)
            if not any(r["pattern"] == p for r in self.store.get_active()):
                self.store.add(p, state.best_action, confidence=min(0.75, 0.74))

    def audit(self) -> dict:
        return audit(self.store)

    def bootstrap(self, memory) -> int:
        return bootstrap(self.store, memory)


# ── Graph node handler ─────────────────────────────────────────────────────────

def handle(state, ctx) -> None:
    """Select best action from candidates; check LLM bypass."""
    action, meta = ctx.policy.route(state, ctx.planner_svc)
    state.best_action = action or "think:no viable action"
    state.best_score  = meta.get("score") or 0.0
    state.best_sim    = meta.get("sim") or {}
    state.llm_bypassed = meta.get("bypassed", False)
