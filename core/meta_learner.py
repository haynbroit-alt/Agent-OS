"""
MetaLearner: builds a direct input→action mapping from episode history.

When a pattern has been observed enough times with consistent high reward,
the agent bypasses the LLM entirely and uses the learned shortcut.

Effect: the agent gets measurably faster the more it runs, without retraining
any model. Common requests become instant after ~3 successful episodes.
"""

from collections import defaultdict


_CONFIDENCE_THRESHOLD = 0.75
_MIN_EPISODES = 3


class MetaLearner:
    def __init__(self):
        # key → {action → [rewards]}
        self._map: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))

    def _key(self, user_input: str) -> str:
        words = sorted(w.lower() for w in user_input.split() if len(w) > 3)
        return " ".join(words[:3])

    def fit(self, memory) -> None:
        """Bootstrap from all successful episodes in the DB."""
        rows = memory.conn.execute(
            "SELECT user_input, action, reward FROM episodes WHERE success=1"
        ).fetchall()
        self._map.clear()
        for user_input, action, reward in rows:
            self._map[self._key(user_input)][action].append(reward)

    def update(self, user_input: str, action: str, reward: float, success: bool) -> None:
        """Incrementally record one episode — O(1)."""
        if success:
            self._map[self._key(user_input)][action].append(reward)

    def should_bypass(self, user_input: str) -> tuple[bool, str | None]:
        """Return (True, action) when a high-confidence shortcut exists, else (False, None)."""
        key = self._key(user_input)
        best_action, best_score = None, 0.0

        for action, rewards in self._map.get(key, {}).items():
            if len(rewards) < _MIN_EPISODES:
                continue
            avg_r = sum(rewards) / len(rewards)
            if avg_r > best_score:
                best_score = avg_r
                best_action = action

        if best_action and best_score >= _CONFIDENCE_THRESHOLD:
            return True, best_action
        return False, None

    def stats(self) -> dict:
        total = len(self._map)
        bypassable = sum(
            1 for candidates in self._map.values()
            if any(
                len(r) >= _MIN_EPISODES and sum(r) / len(r) >= _CONFIDENCE_THRESHOLD
                for r in candidates.values()
            )
        )
        return {"learned_patterns": total, "bypassable_patterns": bypassable}
