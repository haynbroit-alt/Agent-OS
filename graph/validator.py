from core.graph import ExecutionGraph


def validate(graph: ExecutionGraph) -> None:
    errors = graph.validate()
    if errors:
        raise ValueError("Graph validation failed:\n" + "\n".join(f"  - {e}" for e in errors))
