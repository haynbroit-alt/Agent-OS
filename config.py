import os

DB_PATH = os.environ.get("AGENT_DB_PATH", "db/agent.db")
LLM_MODEL = os.environ.get("AGENT_LLM_MODEL", "llama3.2")
LLM_URL = os.environ.get("AGENT_LLM_URL", "http://localhost:11434")
ACTION_BUDGET = int(os.environ.get("AGENT_ACTION_BUDGET", "20"))
LOG_PATH = os.environ.get("AGENT_LOG_PATH", "logs/decisions.jsonl")

_default_allowed = "ls,cat,echo,pwd,wc,date"
ALLOWED_COMMANDS = set(os.environ.get("AGENT_ALLOWED_COMMANDS", _default_allowed).split(","))
