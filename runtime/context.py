"""
RuntimeContext: dependency container passed to every module handler.
All external services live here — not as globals, not as singletons.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class RuntimeContext:
    llm: Any
    memory: Any
    tools: Any
    policy: Any
    planner_svc: Any
