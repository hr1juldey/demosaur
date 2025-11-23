"""
Event type definitions.

Merges with existing orchestrator/events.py types.
"""

from enum import Enum


class EventType(str, Enum):
    """Event types for workflow tracking"""

    # Task lifecycle
    TASK_STARTED = "TASK_STARTED"
    TASK_COMPLETE = "TASK_COMPLETE"
    TASK_FAILED = "TASK_FAILED"

    # Requirements phase
    REQUIREMENTS_COMPLETE = "REQUIREMENTS_COMPLETE"

    # Planning phase
    PLANNING_STARTED = "PLANNING_STARTED"
    PLANNING_COMPLETE = "PLANNING_COMPLETE"

    # Generation phase
    GENERATION_STARTED = "GENERATION_STARTED"
    GENERATION_COMPLETE = "GENERATION_COMPLETE"

    # Module lifecycle
    MODULE_STARTED = "MODULE_STARTED"
    MODULE_ITERATION = "MODULE_ITERATION"
    MODULE_COMPLETE = "MODULE_COMPLETE"

    # Code generation (with versioning)
    CODE_GENERATED = "CODE_GENERATED"

    # Testing
    TEST_STARTED = "TEST_STARTED"
    TEST_PASSED = "TEST_PASSED"
    TEST_FAILED = "TEST_FAILED"

    # Corrections and refinement
    CORRECTION_STARTED = "CORRECTION_STARTED"
    CORRECTION_COMPLETED = "CORRECTION_COMPLETED"

    # Bug reports and interventions
    BUG_REPORT_RECEIVED = "BUG_REPORT_RECEIVED"
    USER_INTERVENTION = "USER_INTERVENTION"

    # Errors
    ERROR = "ERROR"
