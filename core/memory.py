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

    def retrieve(self, query_embedding=None, limit=5):
        rows = self.conn.execute(
            "SELECT user_input, action, outcome, reward, cost, success FROM episodes ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return list(reversed(rows))

    def retrieve_relevant(self, query, limit=5):
        """Return the most semantically relevant past episodes using bag-of-words cosine
        similarity blended with a recency bias (80/20 split).  Falls back to recency-only
        when the query is empty or the table is empty.
        """
        if not query or not query.strip():
            return self.retrieve(None, limit)

        rows = self.conn.execute(
            "SELECT user_input, action, outcome, reward, cost, success, rowid FROM episodes"
        ).fetchall()
        if not rows:
            return []

        query_vec = Counter(query.lower().split())
        max_id = max(r[6] for r in rows)

        def _score(row):
            doc_vec = Counter(f"{row[0]} {row[1]}".lower().split())
            dot = sum(query_vec[w] * doc_vec[w] for w in query_vec)
            norm_q = sum(v * v for v in query_vec.values()) ** 0.5
            norm_d = sum(v * v for v in doc_vec.values()) ** 0.5
            semantic = dot / (norm_q * norm_d) if norm_q and norm_d else 0.0
            recency = row[6] / max_id
            return 0.8 * semantic + 0.2 * recency

        top = sorted(rows, key=_score, reverse=True)[:limit]
        # Return in chronological order so the planner sees a coherent timeline.
        top_chrono = sorted(top, key=lambda r: r[6])
        return [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in top_chrono]
