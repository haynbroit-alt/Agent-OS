# Agent OS

Local-first autonomous agent runtime with episodic memory, policy learning, and full observability. Zero cloud dependency at runtime.

## What it is

An agent that plans actions, executes them in a sandbox, learns from outcomes, and compresses that learning into auditable policy rules — all running on your machine against a local LLM.

```
Memory (episodes) → PolicyCache (rules) → Planner → Execution → Observer → Audit
```

## Requirements

- Python 3.9+
- [Ollama](https://ollama.ai) running locally

```bash
pip install -r requirements.txt
ollama pull llama3.2
```

## Run

```bash
python main.py
```

Global dry-run mode (plan without executing):

```bash
python main.py --dry-run
```

## REPL commands

| Command | Description |
|---|---|
| `:dry <query>` | Plan this query without executing |
| `:obs` | Live health snapshot (success rate, reward trend, calibration) |
| `:clusters` | Dominant action strategies from recent episodes |
| `:cache` | All policy rules (active + quarantined) |
| `:audit` | Run policy cache diagnostics and auto-clean |
| `:log` | Last 20 decisions from the structured log |
| `:quit` | Exit |

## Configuration

All settings via environment variables — no config file to edit:

| Variable | Default | Description |
|---|---|---|
| `AGENT_LLM_MODEL` | `llama3.2` | Ollama model name |
| `AGENT_LLM_URL` | `http://localhost:11434` | Ollama endpoint |
| `AGENT_DB_PATH` | `db/agent.db` | SQLite database path |
| `AGENT_LOG_PATH` | `logs/decisions.jsonl` | Structured decision log |
| `AGENT_ACTION_BUDGET` | `20` | Max cost units per session |
| `AGENT_ALLOWED_COMMANDS` | `ls,cat,echo,pwd,wc,date` | Shell command allowlist |

```bash
AGENT_ALLOWED_COMMANDS=ls,cat,grep,git AGENT_LLM_MODEL=llama3.1:8b python main.py
```

## Architecture

```
agent-os/
├── core/
│   ├── llm.py            # Ollama wrapper, robust JSON extraction
│   ├── memory.py         # Episodic store (SQLite WAL) + semantic retrieval
│   ├── planner.py        # Beam search + LLM simulation + calibrated scoring
│   ├── tools.py          # Sandboxed executor (read / shell allowlist / think)
│   ├── loop.py           # Closed agent loop with dry-run support
│   ├── policy_cache.py   # Rule store, health diagnostics, audit, bootstrap
│   ├── observer.py       # Live health metrics + strategy cluster analysis
│   ├── decision_log.py   # Append-only JSONL decision log
│   └── utils.py          # pretty-print helper
├── db/
│   └── schema.sql
├── config.py
├── main.py
└── requirements.txt
```

## How learning works

1. **Execution** — the agent runs a sandboxed action, gets a real success/failure signal
2. **Memory** — the episode is stored with reward and cost
3. **Policy extraction** — successful episodes automatically generate policy rules
4. **Bootstrap** — on next startup, past high-reward episodes re-seed the rule cache
5. **Audit** — dead, unstable, overgeneralized, and obsolete rules are pruned automatically
6. **Calibration** — the planner tracks how often its LLM simulations match reality and discounts overconfident predictions

## Decision log

Every decision is appended to `logs/decisions.jsonl`:

```json
{"ts":"2026-06-13T09:12:00Z","input":"list files","action":"shell:ls","success":true,"score":8.5,"cost":2,"dry_run":false}
```

## Shell sandbox

Only allowlisted commands execute. Everything else is blocked:

```
> shell:rm -rf /
blocked: 'rm' not in allowlist ['cat', 'date', 'echo', 'ls', 'pwd', 'wc']
```

Extend without touching code: `AGENT_ALLOWED_COMMANDS=ls,cat,grep,git python main.py`
