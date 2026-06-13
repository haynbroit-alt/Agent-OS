class SimulationCalibrator:
    """Tracks how often the LLM's simulated success prediction matches reality.
    When calibration is poor, the planner penalises over-confident scores.
    """
    _WINDOW = 50

    def __init__(self):
        self._records = []  # [(predicted: bool, actual: bool)]

    def record(self, predicted_success, actual_success):
        self._records.append((bool(predicted_success), bool(actual_success)))
        if len(self._records) > self._WINDOW:
            self._records.pop(0)

    @property
    def accuracy(self):
        if not self._records:
            return 1.0
        return sum(p == a for p, a in self._records) / len(self._records)

    @property
    def calibration_penalty(self):
        acc = self.accuracy
        return max(0.0, (0.7 - acc) * 5)  # 0 when accurate, up to 3.5 when acc=0


class Planner:
    def __init__(self, llm):
        self.llm = llm
        self.calibrator = SimulationCalibrator()

    def generate_actions(self, user_input, context, n=3):
        prompt = f"""User request: {user_input}
Context: {context}

Return {n} candidate actions, one per line.
Each action must use one of these prefixes:
- read:<filepath>
- shell:<command>
- think:<reasoning>

Only output the actions, nothing else."""
        out = self.llm.generate(prompt, temperature=0.8)
        candidates = [l.strip() for l in out.split("\n") if l.strip() and ":" in l]
        return candidates[:n] if candidates else ["think:no valid actions generated"]

    def simulate(self, action, context):
        prompt = f"""Action: {action}
Context: {context}

Evaluate this action. Return valid JSON only:
{{
  "success": true,
  "reason": "brief explanation",
  "cost": 3
}}"""
        result = self.llm.generate_json(prompt)
        return result if result else {"success": False, "reason": "simulation failed", "cost": 5}

    def score(self, action, sim, memory, budget):
        cost = sim.get("cost", 5)
        if cost > budget:
            return -1.0

        success_p = 1.0 if sim.get("success") else 0.2

        historical_bonus = 0.0
        for episode in memory.retrieve(None, 3):
            if episode[3] and episode[3] > 0.5:
                historical_bonus += 0.2

        error_penalty = -2.0 if "error" in sim.get("reason", "").lower() else 0.0

        # Discount scores when the LLM's simulations have been unreliable.
        calibration_penalty = -self.calibrator.calibration_penalty

        return success_p * 10 - cost * 0.5 + historical_bonus + error_penalty + calibration_penalty
