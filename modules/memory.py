"""
Memory module: episodic store with semantic retrieval.
Handler: populate state.context_str from relevant past episodes.
"""

import sqlite3
import os
from collections import Counter

import config


class Memory:
    def __init__(self):
        db_path = config.DB_PATH
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self._init_schema()

    def _init_schema(self):
        schema_path = os.path.join(os.path.dirname(__file__), "..", "db", "schema.sql")
        with open(schema_path) as f:
            self.conn.executescript(f.read())
        self.conn.commit()

    def store(self, inp, action, outcome, reward, cost, success, embedding=None):
        self.conn.execute(
            """INSERT INTO episodes
               (user_input, action, outcome, reward, cost, success, embedding)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (inp, action, str(outcome), reward, cost, int(success), embedding),
        )
        self.conn.commit()

    def retrieve(self, limit=5):
        rows = self.conn.execute(
            "SELECT user_input, action, outcome, reward, cost, success "
            "FROM episodes ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return list(reversed(rows))

    def retrieve_relevant(self, query: str, limit: int = 5) -> list:
        if not query.strip():
            return self.retrieve(limit)
        rows = self.conn.execute(
            "SELECT user_input, action, outcome, reward, cost, success, rowid FROM episodes"
        ).fetchall()
        if not rows:
            return []
        q = Counter(query.lower().split())
        max_id = max(r[6] for r in rows)

        def score(r):
            doc = Counter(f"{r[0]} {r[1]}".lower().split())
            dot = sum(q[w] * doc[w] for w in q)
            nq = sum(v * v for v in q.values()) ** 0.5
            nd = sum(v * v for v in doc.values()) ** 0.5
            sem = dot / (nq * nd) if nq and nd else 0.0
            return 0.8 * sem + 0.2 * r[6] / max_id

        top = sorted(rows, key=score, reverse=True)[:limit]
        return [(r[0], r[1], r[2], r[3], r[4], r[5])
                for r in sorted(top, key=lambda r: r[6])]


# ── Graph node handler ─────────────────────────────────────────────────────────

def handle(state, ctx) -> None:
    """Populate state.context_str with semantically relevant past episodes."""
    rows = ctx.memory.retrieve_relevant(state.user_input, limit=state.memory_window)
    state.context_str = "\n".join(str(r) for r in rows) if rows else "(no history)"
