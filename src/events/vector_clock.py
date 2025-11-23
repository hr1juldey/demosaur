"""
Vector clock implementation for distributed causality tracking.

Lamport vector clocks track happens-before relationships across distributed processes.
"""

from typing import Dict


def _validate_clock(clock: Dict[str, int], name: str = "clock") -> None:
    """Validate clock format and values"""
    if not isinstance(clock, dict):
        raise ValueError(f"{name} must be Dict[str, int]")

    for process_id, value in clock.items():
        if not isinstance(process_id, str):
            raise ValueError(f"process_id must be str, got {type(process_id)}")
        if not isinstance(value, int):
            raise ValueError(f"clock value must be int, got {type(value)}")
        if value < 0:
            raise ValueError(f"clock value must be >= 0, got {value}")


class VectorClock:
    """
    Lamport vector clock for tracking causality in distributed events.

    Passing criteria:
    - tick() increments process counter by exactly 1
    - merge() takes max of each process value
    - happens_before() correctly identifies A → B
    - concurrent() returns True when neither A → B nor B → A
    - Rejects negative clock values
    """

    def __init__(self, clock: Dict[str, int] | None = None):
        """Initialize vector clock"""
        self._clock: Dict[str, int] = {}

        if clock is not None:
            _validate_clock(clock, "initial clock")
            self._clock = clock.copy()

    def tick(self, process_id: str) -> Dict[str, int]:
        """Increment clock for process_id and return new clock"""
        if not isinstance(process_id, str) or not process_id:
            raise ValueError("process_id must be non-empty string")

        self._clock[process_id] = self._clock.get(process_id, 0) + 1
        return self._clock.copy()

    def merge(self, other: Dict[str, int]) -> Dict[str, int]:
        """Merge with other clock (max of each process) and return new clock"""
        _validate_clock(other, "other clock")

        # Merge: take max of each process
        for process_id, value in other.items():
            self._clock[process_id] = max(self._clock.get(process_id, 0), value)

        return self._clock.copy()

    def get_clock(self) -> Dict[str, int]:
        """Get current clock state (copy)"""
        return self._clock.copy()

    @staticmethod
    def happens_before(clock1: Dict[str, int], clock2: Dict[str, int]) -> bool:
        """
        Check if clock1 causally precedes clock2 (clock1 → clock2).

        Returns True if:
        - For all processes in clock1: clock1[p] <= clock2[p]
        - For at least one process: clock1[p] < clock2[p]

        Edge cases:
        - {} vs {} → False (equal)
        - {} vs {"p1": 1} → True (empty happens before non-empty)
        - {"p1": 1} vs {} → False
        """
        _validate_clock(clock1, "clock1")
        _validate_clock(clock2, "clock2")

        # Empty clocks edge case
        if not clock1 and not clock2:
            return False  # Equal clocks are concurrent
        if not clock1:
            return True  # Empty happens before any non-empty
        if not clock2:
            return False  # Non-empty cannot happen before empty

        # Check if all clock1 values <= clock2 values
        at_least_one_less = False

        # Get all process IDs from both clocks
        all_processes = set(clock1.keys()) | set(clock2.keys())

        for process_id in all_processes:
            value1 = clock1.get(process_id, 0)
            value2 = clock2.get(process_id, 0)

            if value1 > value2:
                return False  # clock1 has higher value, cannot happen before
            if value1 < value2:
                at_least_one_less = True

        return at_least_one_less

    @staticmethod
    def concurrent(clock1: Dict[str, int], clock2: Dict[str, int]) -> bool:
        """
        Check if clocks are concurrent (neither happens before the other).

        Returns True when no causal relationship exists.
        """
        return not VectorClock.happens_before(clock1, clock2) and \
               not VectorClock.happens_before(clock2, clock1)
