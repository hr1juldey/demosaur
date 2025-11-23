"""
Log Manager - Separates 3 types of logs.

Manages server, workflow, and execution log streams separately.
Follows SRP: Log stream separation only.
"""

from pathlib import Path
from typing import Optional

from src.orchestrator.logger import AsyncLogger, LogLevel
from src.common.utils import ensure_directory
from src.common.config import settings


class LogManager:
    """Manages separate log streams for a task"""

    def __init__(self, task_id: str):
        self.task_id = task_id

        # Ensure log directory exists
        log_dir = ensure_directory(settings.log_directory)

        # Three separate loggers
        self.workflow_logger = AsyncLogger(f"{task_id}-workflow")
        self.workflow_logger.log_file = log_dir / f"task-{task_id}.log"

        self.execution_logger = AsyncLogger(f"{task_id}-exec")
        self.execution_logger.log_file = log_dir / f"task-{task_id}-execution.log"

    async def log_workflow(
        self,
        level: LogLevel,
        message: str,
        **metadata
    ):
        """Log workflow events (planning, generation, refinement)"""
        await self.workflow_logger.log(
            level,
            message,
            task_id=self.task_id,
            **metadata
        )

    async def log_execution(
        self,
        level: LogLevel,
        message: str,
        **metadata
    ):
        """Log code/test execution output"""
        await self.execution_logger.log(
            level,
            message,
            task_id=self.task_id,
            **metadata
        )

    def get_workflow_logs(
        self,
        level: Optional[LogLevel] = None,
        last_n: Optional[int] = None
    ) -> list:
        """Get workflow logs"""
        return self.workflow_logger.get_logs(level, last_n)

    def get_execution_logs(
        self,
        level: Optional[LogLevel] = None,
        last_n: Optional[int] = None
    ) -> list:
        """Get execution logs"""
        return self.execution_logger.get_logs(level, last_n)

    def cleanup(self):
        """Cleanup log resources"""
        self.workflow_logger.clear_logs()
        self.execution_logger.clear_logs()


# Global registry of log managers
_log_managers: dict[str, LogManager] = {}


def get_log_manager(task_id: str) -> LogManager:
    """Get or create LogManager for task"""
    if task_id not in _log_managers:
        _log_managers[task_id] = LogManager(task_id)
    return _log_managers[task_id]


def cleanup_log_manager(task_id: str):
    """Cleanup and remove LogManager"""
    if task_id in _log_managers:
        _log_managers[task_id].cleanup()
        del _log_managers[task_id]
