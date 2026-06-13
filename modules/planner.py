"""
Planner module: generate candidate actions + simulate + score.
"""

import json
import re
import requests

import config


class LLM:
    def __init__(self):
        self.model = config.LLM_MODEL
        self.url   = config.LLM_URL

    def generate(self, prompt, temperature=0.7):
        try:
            r = requests.post(
                f"{self.url}/api/generate",
                json={"model": self.model, "prompt": prompt,
                      "stream": False, "temperature": temperature},
                timeout=60,
            )
            r.raise_for_status()
            return r.json().get("response", "")
        except requests.RequestException as e:
            return f"LLM error: {e}"

    def generate_json(self, prompt):
        raw = self.generate(prompt)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        m = re.search(r"\{.*\}", raw, re.S)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
        return {}


class SimulationCalibrator:
    _WINDOW = 50

    def __init__(self):
        self._records = []

    def record(self, predicted: bool, actual: bool) -> None:
        self._records.append((bool(predicted), bool(actual)))
        if len(self._records) > self._WINDOW:
            self._records.pop(0)

    @property
    def accuracy(self) -> float:
        if not self._records:
            return 1.0
        return sum(p == a for p, a in self._records) / len(self._records)

    @property
    def penalty(self) -> float:
        return max(0.0, (0.7 - self.accuracy) * 5)


class PlannerService:
    def __init__(self, llm: LLM):
        self.llm = llm
        self.calibrator = SimulationCalibrator()

    def generate(self, user_input: str, context: str, n: int = 3) -> list[str]:
        prompt = f"""User request: {user_input}
Context: {context}

Return {n} candidate actions, one per line.
Prefixes: read:<path>  shell:<cmd>  think:<reasoning>
Output actions only."""
        out = self.llm.generate(prompt, temperature=0.8)
        candidates = [l.strip() for l in out.split("\n") if l.strip() and ":" in l]
        return candidates[:n] or ["think:no valid actions generated"]

    def simulate(self, action: str, context: str) -> dict:
        prompt = f"""Action: {action}
Context: {context}

Return JSON only:
{{"success": true, "reason": "brief", "cost": 2}}"""
        r = self.llm.generate_json(prompt)
        return r or {"success": False, "reason": "simulation failed", "cost": 5}

    def score(self, action: str, sim: dict, memory, budget: int) -> float:
        cost = sim.get("cost", 5)
        if cost > budget:
            return -1.0
        success_p = 1.0 if sim.get("success") else 0.2
        hist = sum(0.2 for e in memory.retrieve(3) if e[3] and e[3] > 0.5)
        err = -2.0 if "error" in sim.get("reason", "").lower() else 0.0
        return success_p * 10 - cost * 0.5 + hist + err - self.calibrator.penalty


# ── Graph node handler ─────────────────────────────────────────────────────────

def handle(state, ctx) -> None:
    """Generate candidate actions from state.user_input + state.context_str."""
    state.candidate_actions = ctx.planner_svc.generate(
        state.user_input, state.context_str
    )
