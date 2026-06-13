"""
Default execution graph.

planner → policy → executor → memory → observer → terminal
                ↘ (dry-run) ──────────────────────↗
"""

from core.graph import ExecutionGraph


def build_default_graph() -> ExecutionGraph:
    g = ExecutionGraph()

    g.node("context",   "Retrieve semantically relevant past episodes into state.context_str")
    g.node("planner",   "Generate candidate actions from user input and context")
    g.node("policy",    "Score candidates, check LLM bypass, select best action")
    g.node("executor",  "Execute the selected action via sandboxed tools")
    g.node("memory",    "Persist episode to episodic store")
    g.node("observer",  "Log decision, update calibration, extract policy rule")
    g.node("terminal",  "End of execution cycle")

    # Normal execution path
    g.edge("context",   "planner",  weight=1.0)
    g.edge("planner",   "policy",   weight=1.0)
    g.edge("policy",    "executor", condition="state.mode == 'exec'",     weight=1.0)
    g.edge("policy",    "observer", condition="state.mode == 'dry-run'",  weight=0.9)
    g.edge("executor",  "memory",   weight=1.0)
    g.edge("memory",    "observer", weight=1.0)
    g.edge("observer",  "terminal", weight=1.0)

    return g
