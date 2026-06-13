import json
from core.graph import ExecutionGraph


def to_json(graph: ExecutionGraph, indent: int = 2) -> str:
    return json.dumps(graph.to_dict(), indent=indent)


def to_mermaid(graph: ExecutionGraph) -> str:
    lines = ["graph LR"]
    for edge in graph.edges:
        label = f"|{edge.condition}|" if edge.condition else ""
        lines.append(f"    {edge.source} --{label}--> {edge.target}")
    return "\n".join(lines)
