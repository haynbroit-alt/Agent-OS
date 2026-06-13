from config import ACTION_BUDGET


def run_agent(user_input, memory, planner, tools, llm, budget=None, policy_cache=None):
    if budget is None:
        budget = ACTION_BUDGET

    context_rows = memory.retrieve(None, 3)
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

    for action in actions:
        sim = planner.simulate(action, context_str)
        score = planner.score(action, sim, memory, budget)
        if score > best_score:
            best_score = score
            best_action = action

    if best_action is None:
        return {
            "action": None,
            "output": "no viable action found",
            "success": False,
            "budget_left": budget,
        }

    output, success, cost = tools.execute(best_action)

    reward = 0.8 if success else 0.2
    memory.store(user_input, best_action, output, reward, cost, success)

    return {
        "action": best_action,
        "output": output,
        "success": success,
        "score": round(best_score, 3),
        "cost": cost,
        "budget_left": budget - cost,
    }
