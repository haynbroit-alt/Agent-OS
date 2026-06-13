class Planner:
    def __init__(self, llm):
        self.llm = llm

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

        penalty = -2.0 if "error" in sim.get("reason", "").lower() else 0.0

        return success_p * 10 - cost * 0.5 + historical_bonus + penalty
