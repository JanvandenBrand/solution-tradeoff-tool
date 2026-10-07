"""PerspectiveWeighter — calculates the point budget per perspective agent."""

from typing import Any


class PerspectiveWeighter:
    """Calculates the point budget given a count of requirements.

    Args:
        config: The parsed config.yaml dict (must contain 'budget' section).
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self._cfg = config

    def calculate(self, criteria_count: int) -> int:
        """Return the point budget for criteria_count requirements.

        Args:
            criteria_count: Total number of Must + Should requirements.

        Returns:
            Point budget (integer, multiple of round_to, at least minimum).
        """
        budget_cfg = self._cfg["budget"]
        multiplier: float = budget_cfg["multiplier"]
        round_to: int = budget_cfg["round_to"]
        minimum: int = budget_cfg["minimum"]

        raw = criteria_count * multiplier
        rounded = int(round(raw / round_to) * round_to)
        if rounded == 0:
            rounded = round_to
        return max(rounded, minimum)
