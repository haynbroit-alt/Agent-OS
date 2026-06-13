"""
Global system state: single source of truth for every graph traversal.
All module handlers read from and write to this object.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SystemState:
    # session-level
    mode: str = "exec"           # "exec" | "dry-run"
    budget_remaining: int = 20
    risk_level: str = "low"      # "low" | "medium" | "high"
    memory_window: int = 5

    # per-run (reset each query)
    user_input: str = ""
    context_str: str = ""
    candidate_actions: list = field(default_factory=list)
    best_action: str = ""
    best_score: float = 0.0
    best_sim: dict = field(default_factory=dict)
    execution_output: str = ""
    execution_success: bool = False
    execution_cost: int = 0
    llm_bypassed: bool = False

    # traversal log for this run
    traversal: list[dict] = field(default_factory=list)

    def reset(self, user_input: str, dry_run: bool = False) -> None:
        self.user_input = user_input
        self.mode = "dry-run" if dry_run else "exec"
        self.context_str = ""
        self.candidate_actions = []
        self.best_action = ""
        self.best_score = 0.0
        self.best_sim = {}
        self.execution_output = ""
        self.execution_success = False
        self.execution_cost = 0
        self.llm_bypassed = False
        self.traversal = []

    def step(self, node: str, **data: Any) -> None:
        self.traversal.append({"node": node, **data})

    def result(self) -> dict:
        return {
            "action":       self.best_action,
            "output":       self.execution_output,
            "success":      self.execution_success,
            "dry_run":      self.mode == "dry-run",
            "llm_bypassed": self.llm_bypassed,
            "cost":         self.execution_cost,
            "budget_left":  self.budget_remaining,
            "score":        round(self.best_score, 3) if self.best_score else None,
            "traversal":    [t["node"] for t in self.traversal],
        }
