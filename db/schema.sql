CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_input TEXT,
    action TEXT,
    outcome TEXT,
    reward REAL,
    cost REAL,
    success INTEGER,
    embedding BLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
