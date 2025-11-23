"""
Task state management.

Manages state for concurrent coding tasks.
Follows SRP: State persistence and retrieval only.
"""

from typing import Dict, Optional, Any
from dataclasses import asdict
import json

from src.common.types import (
    TaskStatus,
    Requirements,
    CodePlan,
    ModuleResult,
    DevelopmentReport
)


class TaskState:
    """State for a single coding task"""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.status = TaskStatus.CREATED
        self.requirements: Optional[Requirements] = None
        self.plan: Optional[CodePlan] = None
        self.current_module: Optional[str] = None
        self.current_iteration: int = 0
        self.module_results: Dict[str, ModuleResult] = {}
        self.error_trail: list[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary"""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "requirements": asdict(self.requirements) if self.requirements else None,
            "plan": asdict(self.plan) if self.plan else None,
            "current_module": self.current_module,
            "current_iteration": self.current_iteration,
            "module_results": {
                name: asdict(result)
                for name, result in self.module_results.items()
            },
            "error_trail": self.error_trail,
            "metadata": self.metadata
        }

    def generate_report(self) -> DevelopmentReport:
        """Generate development report from state"""
        total_iterations = sum(
            result.iterations
            for result in self.module_results.values()
        )

        success_count = sum(
            1 for result in self.module_results.values()
            if result.status == "success"
        )

        success_rate = (
            success_count / len(self.module_results)
            if self.module_results else 0.0
        )

        return DevelopmentReport(
            task_id=self.task_id,
            modules=list(self.module_results.values()),
            total_iterations=total_iterations,
            success_rate=success_rate,
            error_trail=self.error_trail,
            timestamp=datetime.utcnow().isoformat()
        )


class StateManager:
    """Manages state for all tasks"""

    def __init__(self):
        self.tasks: Dict[str, TaskState] = {}

    def create_task(self, task_id: str) -> TaskState:
        """Create new task state"""
        state = TaskState(task_id)
        self.tasks[task_id] = state
        return state

    def get_task(self, task_id: str) -> Optional[TaskState]:
        """Get task state"""
        return self.tasks.get(task_id)

    def delete_task(self, task_id: str):
        """Delete task state"""
        if task_id in self.tasks:
            del self.tasks[task_id]

    def list_tasks(self) -> list[str]:
        """List all task IDs"""
        return list(self.tasks.keys())


# Import datetime
from datetime import datetime
