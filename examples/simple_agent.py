"""
Minimal example: run a single query through the Execution Graph OS runtime.

Usage:
    python examples/simple_agent.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import config
config.DB_PATH = "db/example.db"

from runtime.scheduler import Scheduler

sched = Scheduler()

result = sched.run(":dry list project files", dry_run=True)
print("Dry-run result:", result)
