from config import ACTION_BUDGET
from core import decision_log


def _extract_rule_pattern(user_input, action):
    prefix = action.split(":")[0] if ":" in action else "unknown"
    words = [w.lower() for w in user_input.split() if len(w) > 3]
    key = " + ".join(words[:2]) if words else user_input[:20]
    return f"{prefix} | {key}"


def run_agent(user_input, memory, planner, tools, llm,
              budget=None, policy_cache=None, dry_run=False):
    if budget is None:
        budget = ACTION_BUDGET

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
        result = {
            "action": None,
            "output": "no viable action found",
            "success": False,
            "budget_left": budget,
            "dry_run": dry_run,
        }
        decision_log.log({"input": user_input, **result})
        return result

    # ── Dry-run: plan without executing ───────────────────────────
    if dry_run:
        result = {
            "dry_run": True,
            "action": best_action,
            "estimated_cost": best_sim.get("cost", "?"),
            "sim_success": best_sim.get("success"),
            "sim_reason": best_sim.get("reason"),
            "score": round(best_score, 3),
            "would_be_blocked": tools.would_block(best_action),
        }
        decision_log.log({"input": user_input, **result})
        return result

    # ── Real execution ─────────────────────────────────────────────
    output, success, cost = tools.execute(best_action)

    planner.calibrator.record(best_sim.get("success", False), success)

    reward = 0.8 if success else 0.2
    memory.store(user_input, best_action, output, reward, cost, success)

    if success and policy_cache is not None:
        pattern = _extract_rule_pattern(user_input, best_action)
        existing = [r for r in policy_cache.get_rules("active") if r["pattern"] == pattern]
        if not existing:
            confidence = min(0.75, 0.5 + reward * 0.3)
            policy_cache.add_rule(pattern=pattern, action=best_action, confidence=confidence)

    result = {
        "dry_run": False,
        "action": best_action,
        "output": output,
        "success": success,
        "score": round(best_score, 3),
        "cost": cost,
        "budget_left": budget - cost,
        "sim_calibration": round(planner.calibrator.accuracy, 3),
    }
    decision_log.log({"input": user_input, **result})
    return result
