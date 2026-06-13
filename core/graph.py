"""
Execution graph model: nodes are modules, edges are transitions.
Every AI decision is a graph traversal — not a black box.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Node:
    name: str
    description: str = ""


@dataclass
class Edge:
    source: str
    target: str
    condition: Optional[str] = None
    weight: float = 1.0
    cost: float = 0.0


class ExecutionGraph:
    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []

    def node(self, name: str, description: str = "") -> "ExecutionGraph":
        self.nodes[name] = Node(name=name, description=description)
        return self

    def edge(self, source: str, target: str,
             condition: Optional[str] = None,
             weight: float = 1.0, cost: float = 0.0) -> "ExecutionGraph":
        self.edges.append(Edge(source, target, condition, weight, cost))
        return self

    def successors(self, node_name: str) -> list[Edge]:
        return [e for e in self.edges if e.source == node_name]

    def validate(self) -> list[str]:
        names = set(self.nodes)
        errors = []
        for e in self.edges:
            if e.source not in names:
                errors.append(f"edge source '{e.source}' not declared as node")
            if e.target not in names:
                errors.append(f"edge target '{e.target}' not declared as node")
        return errors

    def to_dict(self) -> dict:
        return {
            "nodes": [{"name": n.name, "description": n.description}
                      for n in self.nodes.values()],
            "edges": [{"source": e.source, "target": e.target,
                       "condition": e.condition, "weight": e.weight, "cost": e.cost}
                      for e in self.edges],
        }
