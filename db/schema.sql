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
);
