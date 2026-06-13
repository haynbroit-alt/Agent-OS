import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.graph import ExecutionGraph, Node, Edge
from core.state import SystemState
from core.registry import Registry, ModuleSpec
from core.engine import Engine
from graph.definition import build_default_graph
from graph.validator import validate
from graph.visualizer import to_json, to_mermaid


def test_graph_build():
    g = ExecutionGraph()
    g.node("a", "first").node("b", "second")
    g.edge("a", "b")
    assert len(g.nodes) == 2
    assert len(g.edges) == 1
    assert g.successors("a")[0].target == "b"


def test_graph_validate_ok():
    g = build_default_graph()
    errors = g.validate()
    assert errors == [], f"Unexpected errors: {errors}"


def test_graph_validate_bad():
    g = ExecutionGraph()
    g.node("a")
    g.edge("a", "nonexistent")
    errors = g.validate()
    assert len(errors) == 1


def test_visualizer():
    g = build_default_graph()
    j = to_json(g)
    assert "planner" in j
    m = to_mermaid(g)
    assert "graph LR" in m


def test_state_reset():
    s = SystemState()
    s.reset("hello world")
    assert s.user_input == "hello world"
    assert s.mode == "exec"
    assert s.traversal == []
    s.reset("dry", dry_run=True)
    assert s.mode == "dry-run"


def test_engine_traversal():
    g = ExecutionGraph()
    g.node("start").node("end")
    g.edge("start", "end")

    visited = []

    def h_start(state, ctx):
        visited.append("start")

    def h_end(state, ctx):
        visited.append("end")
        state.best_action = "think:done"
        state.execution_output = "ok"
        state.execution_success = True

    reg = Registry()
    reg.register(ModuleSpec("start", [], [], handler=h_start))
    reg.register(ModuleSpec("end",   [], [], handler=h_end))

    state = SystemState()
    engine = Engine(g, reg, state)
    result = engine.run("test", runtime_ctx=None)

    assert visited == ["start", "end"]
    assert result["success"] is True


if __name__ == "__main__":
    test_graph_build()
    test_graph_validate_ok()
    test_graph_validate_bad()
    test_visualizer()
    test_state_reset()
    test_engine_traversal()
    print("All graph tests passed.")
