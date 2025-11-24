"""
Async logging system with switchable output.

Provides structured logging that Claude can monitor.
Follows SRP: Logging only.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from enum import Enum

from src.common.config import settings
from src.common.utils import ensure_directory


class LogLevel(Enum):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    PROGRESS = "PROGRESS"


class AsyncLogger:
    """Async logger with in-memory buffer"""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.logs: List[Dict[str, Any]] = []
        self.log_file: Optional[Path] = None
        self.enabled = True

        if settings.log_to_file:
            self._setup_file_logging()

    def _setup_file_logging(self):
        """Setup file logging"""
        log_dir = ensure_directory(settings.log_directory)
        self.log_file = log_dir / f"{self.task_id}.log"

    async def log(
        self,
        level: LogLevel,
        message: str,
        **metadata
    ):
        """
        Log a message asynchronously.

        Args:
            level: Log level
            message: Log message
            **metadata: Additional metadata
        """
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level.value,
            "message": message,
            **metadata
        }

        # Add to in-memory buffer
        self.logs.append(log_entry)

        # Write to file if enabled
        if self.log_file:
            await self._write_to_file(log_entry)

    async def _write_to_file(self, entry: Dict[str, Any]):
        """Write log entry to file"""
        line = (
            f"[{entry['timestamp']}] "
            f"{entry['level']}: "
            f"{entry['message']}\n"
        )

        # Async file write
        await asyncio.to_thread(
            self.log_file.write_text,
            self.log_file.read_text() + line if self.log_file.exists() else line
        )

    def get_logs(
        self,
        level: Optional[LogLevel] = None,
        last_n: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get logs from buffer.

        Args:
            level: Filter by log level
            last_n: Return only last N logs

        Returns: List of log entries
        """
        logs = self.logs

        # Filter by level
        if level:
            logs = [log for log in logs if log["level"] == level.value]

        # Get last N
        if last_n:
            logs = logs[-last_n:]

        return logs

    def clear_logs(self):
        """Clear in-memory log buffer"""
        self.logs = []

    def disable(self):
        """Disable logging"""
        self.enabled = False

    def enable(self):
        """Enable logging"""
        self.enabled = True


# Convenience methods
class TaskLogger:
    """Wrapper with convenience methods"""

    def __init__(self, logger: AsyncLogger):
        self.logger = logger

    async def debug(self, message: str, **metadata):
        await self.logger.log(LogLevel.DEBUG, message, **metadata)

    async def info(self, message: str, **metadata):
        await self.logger.log(LogLevel.INFO, message, **metadata)

    async def warn(self, message: str, **metadata):
        await self.logger.log(LogLevel.WARN, message, **metadata)

    async def error(self, message: str, **metadata):
        await self.logger.log(LogLevel.ERROR, message, **metadata)

    async def progress(self, message: str, progress: float, **metadata):
        await self.logger.log(
            LogLevel.PROGRESS,
            message,
            progress=progress,
            **metadata
        )
