import sqlite3
import os

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
