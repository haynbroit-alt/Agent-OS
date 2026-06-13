"""
Execution engine: traverses the graph node by node, calling registered
module handlers in order.  This is the CPU of the runtime.
"""

from core.graph import ExecutionGraph
from core.state import SystemState
from core.registry import Registry


class Engine:
    def __init__(self, graph: ExecutionGraph, registry: Registry, state: SystemState):
        self.graph = graph
        self.registry = registry
        self.state = state

    def run(self, user_input: str, runtime_ctx, dry_run: bool = False) -> dict:
        self.state.reset(user_input, dry_run=dry_run)

        current = self._root()
        max_steps = 20

        for _ in range(max_steps):
            if not current:
                break

            spec = self.registry.get(current)
            if spec.handler is not None:
                spec.handler(self.state, runtime_ctx)

            self.state.step(current)

            edges = sorted(self.graph.successors(current), key=lambda e: -e.weight)
            current = None
            for edge in edges:
                if edge.condition is None or self._check(edge.condition):
                    current = edge.target
                    break

        return self.state.result()

    def _root(self) -> str:
        """Return the node with no incoming edges (entry point of the graph)."""
        has_incoming = {e.target for e in self.graph.edges}
        for name in self.graph.nodes:
            if name not in has_incoming:
                return name
        return next(iter(self.graph.nodes))  # fallback: first declared node

    def _check(self, condition: str) -> bool:
        s = self.state
        try:
            return bool(eval(condition, {"state": s}))
        except Exception:
            return False
