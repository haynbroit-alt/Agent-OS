"""Counterfactual reasoning: what would have happened with a different action?"""


def run(query: str, alternative_action: str, memory, planner_svc) -> dict:
    similar = memory.retrieve_relevant(query, limit=5)
    if not similar:
        return {"status": "no similar episodes found"}

    actual_rewards  = [ep[3] for ep in similar]
    actual_success  = [bool(ep[5]) for ep in similar]
    actual_actions  = list({ep[1] for ep in similar})

    cf_success, cf_costs = [], []
    for ep in similar:
        sim = planner_svc.simulate(alternative_action, str(ep))
        cf_success.append(bool(sim.get("success")))
        cf_costs.append(sim.get("cost", 5))

    actual_sr  = sum(actual_success) / len(actual_success)
    cf_sr      = sum(cf_success)     / len(cf_success)
    delta      = cf_sr - actual_sr

    return {
        "query":              query,
        "alternative_action": alternative_action,
        "episodes_compared":  len(similar),
        "actual":   {"actions": actual_actions,
                     "success_rate": round(actual_sr, 3),
                     "avg_reward":   round(sum(actual_rewards) / len(actual_rewards), 3)},
        "counterfactual": {"success_rate": round(cf_sr, 3),
                           "avg_cost":     round(sum(cf_costs) / len(cf_costs), 3)},
        "delta_success_rate": round(delta, 3),
        "verdict": ("alternative likely better" if delta > 0.1 else
                    "actual was better"          if delta < -0.1 else
                    "similar outcome expected"),
    }
