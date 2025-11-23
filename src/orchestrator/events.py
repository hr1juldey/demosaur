"""
Workflow Events for streaming progress.

Defines event types for real-time workflow updates.
Follows SRP: Event definitions only.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Literal
from datetime import datetime


EventType = Literal[
    "TASK_STARTED",
    "REQUIREMENTS_COMPLETE",
    "PLANNING_STARTED",
    "PLANNING_COMPLETE",
    "GENERATION_STARTED",
    "MODULE_STARTED",
    "MODULE_ITERATION",
    "MODULE_COMPLETE",
    "GENERATION_COMPLETE",
    "TASK_COMPLETE",
    "TASK_FAILED",
    "ERROR"
]


@dataclass
class WorkflowEvent:
    """Single event in workflow progress"""

    type: EventType
    task_id: str
    timestamp: str
    data: Dict[str, Any]

    @classmethod
    def create(
        cls,
        event_type: EventType,
        task_id: str,
        **data
    ) -> 'WorkflowEvent':
        """Create event with current timestamp"""
        return cls(
            type=event_type,
            task_id=task_id,
            timestamp=datetime.utcnow().isoformat(),
            data=data
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    def to_json_str(self) -> str:
        """Convert to JSON string"""
        import json
        return json.dumps(self.to_dict())


# Event factory functions for common events
def task_started(task_id: str, goal: str) -> WorkflowEvent:
    """Task started event"""
    return WorkflowEvent.create(
        "TASK_STARTED",
        task_id,
        goal=goal
    )


def planning_started(task_id: str) -> WorkflowEvent:
    """Planning phase started"""
    return WorkflowEvent.create(
        "PLANNING_STARTED",
        task_id
    )


def planning_complete(
    task_id: str,
    module_count: int,
    test_count: int
) -> WorkflowEvent:
    """Planning complete"""
    return WorkflowEvent.create(
        "PLANNING_COMPLETE",
        task_id,
        module_count=module_count,
        test_count=test_count
    )


def module_started(
    task_id: str,
    module_name: str,
    module_index: int,
    total_modules: int
) -> WorkflowEvent:
    """Module generation started"""
    return WorkflowEvent.create(
        "MODULE_STARTED",
        task_id,
        module_name=module_name,
        module_index=module_index,
        total_modules=total_modules,
        progress=module_index / total_modules
    )


def module_iteration(
    task_id: str,
    module_name: str,
    iteration: int,
    score: float
) -> WorkflowEvent:
    """Module iteration complete"""
    return WorkflowEvent.create(
        "MODULE_ITERATION",
        task_id,
        module_name=module_name,
        iteration=iteration,
        score=score
    )
