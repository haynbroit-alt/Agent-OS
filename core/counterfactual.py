"""
Counterfactual reasoning: "What would have happened if I had taken action X
instead of what I actually did in similar past situations?"

This lets the agent (and its operator) audit decision quality retroactively
and discover better strategies that were never tried.
"""


def counterfactual(query: str, alternative_action: str, memory, planner) -> dict:
    """
    Retrieve similar past episodes and simulate `alternative_action` against
    each of their contexts.  Compare the counterfactual outcome distribution
    against what actually happened.

    Requires a live LLM connection (planner.simulate calls Ollama).
    Use dry_run=True in the main loop if you want to test without Ollama.
    """
    similar = memory.retrieve_relevant(query, limit=5)

    if not similar:
        return {"status": "no similar episodes found for this query"}

    actual_rewards  = [ep[3] for ep in similar]
    actual_success  = [bool(ep[5]) for ep in similar]
    actual_actions  = [ep[1] for ep in similar]

    cf_success, cf_costs = [], []
    for ep in similar:
        sim = planner.simulate(alternative_action, str(ep))
        cf_success.append(bool(sim.get("success")))
        cf_costs.append(sim.get("cost", 5))

    actual_sr   = sum(actual_success)  / len(actual_success)
    actual_avgr = sum(actual_rewards)  / len(actual_rewards)
    cf_sr       = sum(cf_success)      / len(cf_success)
    cf_avgcost  = sum(cf_costs)        / len(cf_costs)

    delta_sr = cf_sr - actual_sr
    if abs(delta_sr) < 0.1:
        verdict = "similar outcome expected"
    elif delta_sr > 0:
        verdict = "alternative likely better"
    else:
        verdict = "actual was better"

    return {
        "query":              query,
        "alternative_action": alternative_action,
        "episodes_compared":  len(similar),
        "actual": {
            "actions":      list(set(actual_actions)),
            "success_rate": round(actual_sr,   3),
            "avg_reward":   round(actual_avgr, 3),
        },
        "counterfactual": {
            "action":       alternative_action,
            "success_rate": round(cf_sr,      3),
            "avg_cost":     round(cf_avgcost, 3),
        },
        "delta_success_rate": round(delta_sr, 3),
        "verdict":            verdict,
    }
