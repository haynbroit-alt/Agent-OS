# Execution Graph OS

**AI Execution Runtime with full observability and safe tool execution.**

Every AI decision is a graph traversal — not a black box.

```
context → planner → policy → executor → memory → observer
```

---

## Why it exists

AI tools can plan. But you cannot see or control what happens.

Execution Graph OS fixes that: every action is an edge in an explicit graph, logged, auditable, and replayable.

---

## Features

- **Execution graph model** — nodes are modules, edges are transitions
- **Safe tool execution** — shell allowlist, `read:`, `think:` prefixes
- **Full decision logs** — append-only JSONL, every run
- **Dry-run mode** — plan without executing
- **LLM bypass** — learned shortcuts skip the LLM after 3+ consistent successes
- **Policy routing** — rule-based action scoring with automatic audit
- **Behavioral drift tracking** — detect shifts in what the agent does over time
- **Counterfactual reasoning** — "what would have happened with action X?"
- **Self-diagnosis** — `:diagnose` renders a structured analysis of agent behavior
- **Local-first** — runs on Ollama, zero cloud dependency at runtime

---

## Install

```bash
pip install -r requirements.txt
ollama pull llama3.2
```

Or install as a package:
```bash
pip install -e .
egos  # CLI entry point
```

---

## Run

```bash
python cli/main.py
python cli/main.py --dry-run
```

---

## REPL commands

| Command | Description |
|---|---|
| `:graph` | Show the execution graph (Mermaid + JSON) |
| `:obs` | Health snapshot: success rate, reward trend, calibration |
| `:clusters` | Dominant action strategies from recent episodes |
| `:audit` | Policy audit — prune dead/unstable/overgeneralized rules |
| `:cache` | All policy rules (active + quarantined) |
| `:log` | Last 20 decisions |
| `:diagnose` | Full behavioral self-analysis |
| `:meta` | MetaLearner stats (learned / bypassable patterns) |
| `:drift` | Behavioral drift report |
| `:registry` | All registered modules and their contracts |
| `:cf <action>` | Counterfactual for last query |
| `:dry <query>` | Plan without executing |

---

## Architecture

```
execution-graph-os/
├── core/
│   ├── graph.py        # Graph model: nodes, edges, traversal
│   ├── engine.py       # Execution engine (graph traversal)
│   ├── state.py        # Global system state (single source of truth)
│   └── registry.py     # Module registry (declarative contracts)
│
├── modules/
│   ├── memory.py       # Episodic store + semantic retrieval
│   ├── planner.py      # LLM wrapper + candidate generation + calibration
│   ├── policy.py       # Routing: rule store + MetaLearner bypass
│   └── tools.py        # Sandboxed executor
│
├── runtime/
│   ├── scheduler.py    # Wires everything into a single callable
│   ├── context.py      # Dependency container (no globals)
│   └── executor.py     # Re-export shim
│
├── graph/
│   ├── definition.py   # Default execution graph
│   ├── validator.py    # Graph consistency checks
│   └── visualizer.py   # Mermaid + JSON export
│
├── observability/
│   ├── logger.py       # JSONL append-only decision log
│   ├── introspect.py   # Self-diagnosis engine
│   ├── counterfactual.py  # Counterfactual reasoning
│   └── drift.py        # Behavioral drift detection
│
├── cli/
│   ├── main.py         # Entry point
│   └── commands.py     # REPL command handlers
│
├── config/
│   ├── config.yaml     # Configuration template
│   └── policies.yaml   # Routing thresholds
│
├── tests/
│   ├── test_graph.py
│   └── test_tools.py
│
├── examples/
│   └── simple_agent.py
│
├── pyproject.toml
└── LICENSE
```

---

## The graph

```
context → planner → policy ─(exec)──→ executor → memory → observer → terminal
                          └─(dry-run)────────────────────────────────↗
```

Each node is a registered module with declared inputs/outputs and a pure handler function. The engine traverses edges, evaluating conditions against the global `SystemState`.

View it live: `:graph`

---

## Configuration

All settings via environment variables:

| Variable | Default | Description |
|---|---|---|
| `AGENT_LLM_MODEL` | `llama3.2` | Ollama model |
| `AGENT_LLM_URL` | `http://localhost:11434` | Ollama endpoint |
| `AGENT_DB_PATH` | `db/agent.db` | SQLite path |
| `AGENT_LOG_PATH` | `logs/decisions.jsonl` | Decision log |
| `AGENT_ACTION_BUDGET` | `20` | Max cost per session |
| `AGENT_ALLOWED_COMMANDS` | `ls,cat,echo,pwd,wc,date` | Shell allowlist |

```bash
AGENT_ALLOWED_COMMANDS=ls,cat,grep,git python cli/main.py
```

---

## Decision log

Every decision appended to `logs/decisions.jsonl`:

```json
{"ts":"2026-06-13T10:00:00Z","input":"list files","action":"shell:ls","success":true,"score":8.5,"cost":2,"dry_run":false,"traversal":["context","planner","policy","executor","memory","observer"]}
```

---

## Use cases

- Local DevOps automation with audit trail
- AI agent sandboxing + observability
- Workflow automation with dry-run preview
- AI decision debugging and replay
