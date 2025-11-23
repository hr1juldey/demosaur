"""
Priority system for task orchestration.

Defines priority levels and assignment logic for different task types.
"""

from enum import IntEnum
from typing import Optional

from src.events.event_types import EventType


class TaskPriority(IntEnum):
    """
    Task priority levels (lower number = higher priority).

    Passing criteria:
    - CRITICAL < HIGH < MEDIUM < LOW < BACKGROUND
    - Values are 0, 10, 20, 30, 40 (10-point increments)
    - Preemption requires ≥20 priority difference
    """

    CRITICAL = 0
    HIGH = 10
    MEDIUM = 20
    LOW = 30
    BACKGROUND = 40


class TaskPriorityAssigner:
    """
    Assigns priority to tasks based on event type.

    Passing criteria:
    - assign_priority() maps event types correctly
    - should_preempt() returns True only if priority diff ≥20
    - Unknown events default to BACKGROUND
    """

    # Event type to priority mapping
    _PRIORITY_MAP = {
        # Critical: User interventions and bug reports
        EventType.USER_INTERVENTION: TaskPriority.CRITICAL,
        EventType.BUG_REPORT_RECEIVED: TaskPriority.CRITICAL,
        EventType.TASK_FAILED: TaskPriority.CRITICAL,

        # High: Code generation and corrections
        EventType.CODE_GENERATED: TaskPriority.HIGH,
        EventType.CORRECTION_STARTED: TaskPriority.HIGH,
        EventType.CORRECTION_COMPLETED: TaskPriority.HIGH,
        EventType.GENERATION_STARTED: TaskPriority.HIGH,
        EventType.GENERATION_COMPLETE: TaskPriority.HIGH,

        # Medium: Testing and module work
        EventType.TEST_STARTED: TaskPriority.MEDIUM,
        EventType.TEST_PASSED: TaskPriority.MEDIUM,
        EventType.TEST_FAILED: TaskPriority.MEDIUM,
        EventType.MODULE_STARTED: TaskPriority.MEDIUM,
        EventType.MODULE_ITERATION: TaskPriority.MEDIUM,
        EventType.MODULE_COMPLETE: TaskPriority.MEDIUM,

        # Low: Planning and requirements
        EventType.PLANNING_STARTED: TaskPriority.LOW,
        EventType.PLANNING_COMPLETE: TaskPriority.LOW,
        EventType.REQUIREMENTS_COMPLETE: TaskPriority.LOW,

        # Background: Task lifecycle events
        EventType.TASK_STARTED: TaskPriority.BACKGROUND,
        EventType.TASK_COMPLETE: TaskPriority.BACKGROUND,
        EventType.ERROR: TaskPriority.BACKGROUND,
    }

    @classmethod
    def assign_priority(cls, event_type: Optional[EventType]) -> TaskPriority:
        """
        Assign priority based on event type.

        Returns BACKGROUND for unknown event types.
        """
        if event_type is None:
            return TaskPriority.BACKGROUND

        return cls._PRIORITY_MAP.get(event_type, TaskPriority.BACKGROUND)

    @staticmethod
    def should_preempt(new_priority: TaskPriority, current_priority: TaskPriority) -> bool:
        """
        Check if new task should preempt current task.

        Returns True only if priority difference is ≥20 (2 levels).

        Example:
        - CRITICAL (0) should preempt MEDIUM (20) → True (diff=20)
        - CRITICAL (0) should preempt HIGH (10) → False (diff=10)
        - HIGH (10) should preempt BACKGROUND (40) → True (diff=30)
        """
        priority_diff = current_priority - new_priority
        return priority_diff >= 20

    @staticmethod
    def get_priority_name(priority: TaskPriority) -> str:
        """Get human-readable name for priority level"""
        return priority.name
