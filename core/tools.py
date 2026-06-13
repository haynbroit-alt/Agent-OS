import subprocess


ALLOWED_COMMANDS = {"ls", "cat", "echo", "pwd", "wc", "date"}


class Tools:
    def __init__(self, allowed=None):
        self.allowed = allowed or ALLOWED_COMMANDS

    def execute(self, action):
        if not action or ":" not in action:
            return "invalid action format", False, 0

        prefix, _, payload = action.partition(":")
        payload = payload.strip()

        if prefix == "read":
            return self._read(payload)
        if prefix == "shell":
            return self._shell(payload)
        if prefix == "think":
            return payload, True, 1
        return f"unknown action prefix: {prefix}", False, 0

    def _read(self, path):
        try:
            with open(path) as f:
                return f.read(2000), True, 1
        except Exception as e:
            return str(e), False, 1

    def _shell(self, cmd):
        base = cmd.split()[0] if cmd.split() else ""
        if base not in self.allowed:
            return f"blocked: '{base}' not in allowlist {self.allowed}", False, 2
        try:
            res = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=10
            )
            output = res.stdout or res.stderr
            return output, res.returncode == 0, 2
        except subprocess.TimeoutExpired:
            return "command timed out", False, 2
        except Exception as e:
            return str(e), False, 2
