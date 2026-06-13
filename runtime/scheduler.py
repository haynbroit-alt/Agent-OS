"""
Scheduler: wires graph + engine + all modules into a single callable.
This is the public API of the runtime.
"""

import config
from core.engine import Engine
from core.graph import ExecutionGraph
from core.registry import Registry, ModuleSpec
from core.state import SystemState
from runtime.context import RuntimeContext

import modules.memory   as mem_mod
import modules.planner  as plan_mod
import modules.policy   as pol_mod


def _noop(state, ctx) -> None:
    pass
import modules.tools    as tool_mod
import observability.logger as log_mod


class Scheduler:
    def __init__(self, graph: ExecutionGraph = None):
        from graph.definition import build_default_graph
        from graph.validator import validate

        self.graph  = graph or build_default_graph()
        validate(self.graph)

        # Services
        self.memory     = mem_mod.Memory()
        self.llm        = plan_mod.LLM()
        self.planner    = plan_mod.PlannerService(self.llm)
        self.tools      = tool_mod.Tools()
        self.policy          = pol_mod.Policy(conn=self.memory.conn)
        self.policy._memory  = self.memory   # inject for scoring

        # Bootstrap policy from past episodes
        self.policy.bootstrap(self.memory)
        self.policy.meta.fit(self.memory)

        # State
        self.state = SystemState(budget_remaining=config.ACTION_BUDGET)

        # Runtime context
        self.ctx = RuntimeContext(
            llm         = self.llm,
            memory      = self.memory,
            tools       = self.tools,
            policy      = self.policy,
            planner_svc = self.planner,
        )

        # Registry
        self.registry = Registry()
        for name, handler in [
            ("context",  mem_mod.handle),
            ("planner",  plan_mod.handle),
            ("policy",   pol_mod.handle),
            ("executor", tool_mod.handle),
            ("memory",   _noop),        # episode storage happens in observer/logger
            ("observer", log_mod.handle),
            ("terminal", None),
        ]:
            self.registry.register(ModuleSpec(
                name=name, inputs=[], outputs=[], handler=handler
            ))

        # Engine
        self.engine = Engine(self.graph, self.registry, self.state)

    def run(self, user_input: str, dry_run: bool = False) -> dict:
        return self.engine.run(user_input, self.ctx, dry_run=dry_run)
