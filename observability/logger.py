"""Append-only JSONL decision log."""

import json
import os
from datetime import datetime, timezone

import config


def log(entry: dict) -> None:
    path = config.LOG_PATH
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    record = {"ts": datetime.now(timezone.utc).isoformat(), **entry}
    with open(path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")


def tail(n: int = 20) -> list[dict]:
    path = config.LOG_PATH
    if not os.path.exists(path):
        return []
    with open(path) as f:
        lines = f.readlines()
    out = []
    for line in lines[-n:]:
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


# ── Graph node handler ─────────────────────────────────────────────────────────

def handle(state, ctx) -> None:
    """Persist decision, update calibration, extract policy rule."""
    if state.mode != "dry-run":
        ctx.memory.store(
            state.user_input, state.best_action, state.execution_output,
            0.8 if state.execution_success else 0.2,
            state.execution_cost, state.execution_success,
        )
        ctx.policy.learn(state, ctx.planner_svc)

    log({
        "input":        state.user_input,
        "action":       state.best_action,
        "success":      state.execution_success,
        "dry_run":      state.mode == "dry-run",
        "llm_bypassed": state.llm_bypassed,
        "score":        state.best_score,
        "cost":         state.execution_cost,
        "traversal":    [t["node"] for t in state.traversal],
    })
