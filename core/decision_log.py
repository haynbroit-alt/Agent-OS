"""
Append-only JSONL decision log.
Every agent decision (real or dry-run) is written here for external
consumption: dashboards, grep, post-mortem analysis.
"""

import json
import os
from datetime import datetime, timezone

import config


def log(entry: dict) -> None:
    log_path = config.LOG_PATH
    parent = os.path.dirname(log_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    record = {"ts": datetime.now(timezone.utc).isoformat(), **entry}
    with open(log_path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")


def tail(n=20) -> list[dict]:
    """Return the last n log entries."""
    log_path = config.LOG_PATH
    if not os.path.exists(log_path):
        return []
    with open(log_path) as f:
        lines = f.readlines()
    entries = []
    for line in lines[-n:]:
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries
