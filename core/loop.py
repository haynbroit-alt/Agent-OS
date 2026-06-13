from config import ACTION_BUDGET


def _extract_rule_pattern(user_input, action):
    prefix = action.split(":")[0] if ":" in action else "unknown"
    words = [w.lower() for w in user_input.split() if len(w) > 3]
    key = " + ".join(words[:2]) if words else user_input[:20]
    return f"{prefix} | {key}"


def run_agent(user_input, memory, planner, tools, llm, budget=None, policy_cache=None):
    if budget is None:
        budget = ACTION_BUDGET

    # Semantic retrieval: relevant past episodes, not just the most recent ones.
    context_rows = memory.retrieve_relevant(user_input, limit=3)
    context_str = "\n".join(str(r) for r in context_rows) if context_rows else "(no history)"

    if policy_cache is not None:
        cached_rules = policy_cache.get_rules(status="active")
        if cached_rules:
            hints = "\n".join(
                f"- {r['action']} (success_rate={r['success_rate']:.2f})"
                for r in cached_rules[:3]
            )
            context_str += f"\nCached high-value actions:\n{hints}"

    actions = planner.generate_actions(user_input, context_str)

    best_action = None
    best_score = -999.0
    best_sim = {}

    for action in actions:
        sim = planner.simulate(action, context_str)
        score = planner.score(action, sim, memory, budget)
        if score > best_score:
            best_score = score
            best_action = action
            best_sim = sim

    if best_action is None:
        return {
            "action": None,
            "output": "no viable action found",
            "success": False,
            "budget_left": budget,
        }

    output, success, cost = tools.execute(best_action)

    # Update simulation calibration: did the LLM predict the outcome correctly?
    planner.calibrator.record(best_sim.get("success", False), success)

    reward = 0.8 if success else 0.2
    memory.store(user_input, best_action, output, reward, cost, success)

    # Auto-extract a policy rule from successful episodes.
    if success and policy_cache is not None:
        pattern = _extract_rule_pattern(user_input, best_action)
        existing = [r for r in policy_cache.get_rules("active") if r["pattern"] == pattern]
        if not existing:
            confidence = min(0.75, 0.5 + reward * 0.3)
            policy_cache.add_rule(pattern=pattern, action=best_action, confidence=confidence)

    return {
        "action": best_action,
        "output": output,
        "success": success,
        "score": round(best_score, 3),
        "cost": cost,
        "budget_left": budget - cost,
        "sim_calibration": round(planner.calibrator.accuracy, 3),
    }
