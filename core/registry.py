"""
Module registry: every module is declared with its contract.
No hidden side-effects. No magic imports.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class ModuleSpec:
    name: str
    inputs: list[str]
    outputs: list[str]
    description: str = ""
    side_effects: bool = False
    handler: Optional[Callable] = None


class Registry:
    def __init__(self):
        self._modules: dict[str, ModuleSpec] = {}

    def register(self, spec: ModuleSpec) -> None:
        self._modules[spec.name] = spec

    def get(self, name: str) -> ModuleSpec:
        if name not in self._modules:
            raise KeyError(f"module '{name}' not registered")
        return self._modules[name]

    def all(self) -> list[ModuleSpec]:
        return list(self._modules.values())

    def to_dict(self) -> list[dict]:
        return [
            {
                "name":         m.name,
                "description":  m.description,
                "inputs":       m.inputs,
                "outputs":      m.outputs,
                "side_effects": m.side_effects,
            }
            for m in self._modules.values()
        ]
