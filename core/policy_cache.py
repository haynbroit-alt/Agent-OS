"""
Policy cache: a compressed, auditable layer of action rules derived from episodes.
Sits between episodic memory and the planner to accelerate decision-making
and prevent pattern hallucinations.

Architecture:
  Memory (episodes) → PolicyCache (rules) → Planner → Execution → Audit
"""

import json
import os
import sqlite3
from datetime import datetime

import config


# ─── Storage ──────────────────────────────────────────────────────────────────

class PolicyCache:
    def __init__(self, conn=None):
        if conn is None:
            db_path = config.DB_PATH
            parent = os.path.dirname(db_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL;")
        self.conn = conn
        self._init_schema()

    def _init_schema(self):
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

    def add_rule(self, pattern, action, confidence=0.5, supporting_episodes=None):
        self.conn.execute(
            """INSERT INTO policy_cache
               (pattern, action, confidence, supporting_episodes, last_used, status)
               VALUES (?, ?, ?, ?, ?, 'active')""",
            (pattern, action, confidence,
             json.dumps(supporting_episodes or []),
             datetime.utcnow().isoformat()),
        )
        self.conn.commit()

    def get_rules(self, status="active"):
        rows = self.conn.execute(
            "SELECT id, pattern, action, confidence, supporting_episodes, "
            "last_used, success_rate, failure_rate, usage_count, status "
            "FROM policy_cache WHERE status = ? ORDER BY success_rate DESC",
            (status,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def get_all_rules(self):
        rows = self.conn.execute(
            "SELECT id, pattern, action, confidence, supporting_episodes, "
            "last_used, success_rate, failure_rate, usage_count, status "
            "FROM policy_cache ORDER BY id"
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def record_usage(self, rule_id, success):
        row = self.conn.execute(
            "SELECT usage_count, success_rate, failure_rate FROM policy_cache WHERE id = ?",
            (rule_id,),
        ).fetchone()
        if not row:
            return
        n, sr, fr = row
        new_n = n + 1
        if success:
            new_sr = (sr * n + 1.0) / new_n
            new_fr = fr * n / new_n
        else:
            new_sr = sr * n / new_n
            new_fr = (fr * n + 1.0) / new_n
        self.conn.execute(
            "UPDATE policy_cache "
            "SET usage_count=?, success_rate=?, failure_rate=?, last_used=? WHERE id=?",
            (new_n, new_sr, new_fr, datetime.utcnow().isoformat(), rule_id),
        )
        self.conn.commit()

    def set_status(self, rule_id, status):
        self.conn.execute(
            "UPDATE policy_cache SET status = ? WHERE id = ?", (status, rule_id)
        )
        self.conn.commit()

    def delete_rule(self, rule_id):
        self.conn.execute("DELETE FROM policy_cache WHERE id = ?", (rule_id,))
        self.conn.commit()


def _row_to_dict(row):
    keys = ["id", "pattern", "action", "confidence", "supporting_episodes",
            "last_used", "success_rate", "failure_rate", "usage_count", "status"]
    d = dict(zip(keys, row))
    try:
        d["supporting_episodes"] = json.loads(d["supporting_episodes"] or "[]")
    except (json.JSONDecodeError, TypeError):
        d["supporting_episodes"] = []
    return d


# ─── Diagnostic functions ──────────────────────────────────────────────────────

def rule_health(rule, now_days_ago=7):
    recency_decay = max(0.1, 1.0 - (now_days_ago / 30))
    health = (
        0.3 * rule.get("confidence", 0.5)
        + 0.3 * rule.get("success_rate", 0.0)
        - 0.2 * rule.get("failure_rate", 0.0)
        + 0.2 * recency_decay
    )
    if rule.get("usage_count", 0) < 3:
        health -= 0.2
    return max(0.0, min(1.0, health))


def is_dead(rule):
    return rule.get("usage_count", 0) == 0


def is_unstable(rule):
    return abs(rule.get("success_rate", 0.0) - rule.get("failure_rate", 0.0)) < 0.1


def is_obsolete(rule, now_days_ago=7):
    return now_days_ago > 14 and rule.get("success_rate", 0.0) < 0.5


def is_overgeneralized(rule):
    return rule.get("confidence", 0.0) > 0.85 and rule.get("failure_rate", 0.0) > 0.3


def audit_policy_cache(rules, now_days_ago=7):
    keep, remove, quarantine = [], [], []
    for rule in rules:
        health = rule_health(rule, now_days_ago)
        if is_dead(rule):
            remove.append(rule)
        elif is_overgeneralized(rule):
            quarantine.append(rule)
        elif is_obsolete(rule, now_days_ago):
            remove.append(rule)
        elif health < 0.4:
            quarantine.append(rule)
        else:
            keep.append(rule)
    return {"keep": keep, "remove": remove, "quarantine": quarantine}


def policy_cache_health(rules):
    if not rules:
        return 1.0
    scores = [rule_health(r, 7) for r in rules]
    avg_health = sum(scores) / len(scores)
    diversity = len(set(r["pattern"] for r in rules)) / len(rules)
    return avg_health * diversity


# ─── Auto-repair cycle ─────────────────────────────────────────────────────────

_AUTO_REPAIR_THRESHOLD = 0.3


def run_audit(cache, now_days_ago=7, auto_repair_threshold=_AUTO_REPAIR_THRESHOLD):
    """
    Apply audit decisions to the cache and return a summary report.

    Rules classified as 'remove' are deleted.
    Rules classified as 'quarantine' are disabled but retained for analysis.
    If overall cache health drops below auto_repair_threshold, all non-quarantined
    rules are purged and the cache rebuilds from scratch on next episode ingestion.
    """
    rules = cache.get_all_rules()
    cache_health = policy_cache_health(rules)
    auto_repaired = False

    if cache_health < auto_repair_threshold and rules:
        for rule in rules:
            if rule["status"] != "quarantine":
                cache.delete_rule(rule["id"])
        auto_repaired = True
        kept, removed, quarantined = 0, len(rules), 0
    else:
        result = audit_policy_cache(rules, now_days_ago)
        for rule in result["remove"]:
            cache.delete_rule(rule["id"])
        for rule in result["quarantine"]:
            cache.set_status(rule["id"], "quarantine")
        kept = len(result["keep"])
        removed = len(result["remove"])
        quarantined = len(result["quarantine"])

    return {
        "kept": kept,
        "removed": removed,
        "quarantined": quarantined,
        "cache_health": round(cache_health, 3),
        "auto_repaired": auto_repaired,
    }
