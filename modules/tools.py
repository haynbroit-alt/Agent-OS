"""
Tools module: sandboxed action executor.
Supported: read:<path>  shell:<allowlisted-cmd>  think:<text>
"""

import subprocess
import config


class Tools:
    def __init__(self, allowed=None):
        self.allowed = allowed if allowed is not None else config.ALLOWED_COMMANDS

    def would_block(self, action: str) -> bool:
        if not action or ":" not in action:
            return True
        prefix, _, payload = action.partition(":")
        if prefix == "shell":
            base = payload.strip().split()[0] if payload.strip() else ""
            return base not in self.allowed
        return False

    def execute(self, action: str) -> tuple[str, bool, int]:
        if not action or ":" not in action:
            return "invalid action format", False, 0
        prefix, _, payload = action.partition(":")
        payload = payload.strip()
        if prefix == "read":
            return self._read(payload)
        if prefix == "shell":
            return self._shell(payload)
        if prefix == "think":
            return payload, True, 1
        return f"unknown prefix: {prefix}", False, 0

    def _read(self, path):
        try:
            with open(path) as f:
                return f.read(2000), True, 1
        except Exception as e:
            return str(e), False, 1

    def _shell(self, cmd):
        base = cmd.split()[0] if cmd.split() else ""
        if base not in self.allowed:
            return f"blocked: '{base}' not in allowlist {sorted(self.allowed)}", False, 2
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            return res.stdout or res.stderr, res.returncode == 0, 2
        except subprocess.TimeoutExpired:
            return "command timed out", False, 2
        except Exception as e:
            return str(e), False, 2


# ── Graph node handler ─────────────────────────────────────────────────────────

def handle(state, ctx) -> None:
    """Execute state.best_action if not in dry-run mode."""
    if state.mode == "dry-run":
        state.execution_output  = f"[dry-run] would execute: {state.best_action}"
        state.execution_success = not ctx.tools.would_block(state.best_action)
        state.execution_cost    = 0
        return

    output, success, cost = ctx.tools.execute(state.best_action)
    state.execution_output  = output
    state.execution_success = success
    state.execution_cost    = cost
    state.budget_remaining -= cost
