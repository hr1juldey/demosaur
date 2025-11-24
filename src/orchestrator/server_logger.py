"""
Server Logger - Global singleton for MCP server operations.

Tracks server lifecycle and MCP operations separately from tasks.
Follows SRP: Server logging only.
"""

from typing import Optional

from src.orchestrator.logger import AsyncLogger, LogLevel
from src.common.utils import ensure_directory
from src.common.config import settings


class ServerLogger:
    """Global logger for MCP server operations"""

    _instance: Optional['ServerLogger'] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Only initialize once
        if not ServerLogger._initialized:
            log_dir = ensure_directory(settings.log_directory)
            self.logger = AsyncLogger("mcp-server")
            self.logger.log_file = log_dir / "server.log"
            ServerLogger._initialized = True

    async def log(
        self,
        level: LogLevel,
        message: str,
        **metadata
    ):
        """Log server operation"""
        await self.logger.log(level, message, **metadata)

    async def startup(self):
        """Log server startup"""
        await self.log(
            LogLevel.INFO,
            "MCP Server starting",
            version="1.0.0"
        )

    async def shutdown(self):
        """Log server shutdown"""
        await self.log(
            LogLevel.INFO,
            "MCP Server shutting down"
        )

    async def task_created(self, task_id: str):
        """Log task creation"""
        await self.log(
            LogLevel.INFO,
            f"Task created: {task_id}",
            task_id=task_id
        )

    async def task_completed(self, task_id: str):
        """Log task completion"""
        await self.log(
            LogLevel.INFO,
            f"Task completed: {task_id}",
            task_id=task_id
        )

    async def error(self, message: str, **metadata):
        """Log server error"""
        await self.log(LogLevel.ERROR, message, **metadata)

    def get_logs(
        self,
        level: Optional[LogLevel] = None,
        last_n: Optional[int] = None
    ) -> list:
        """Get server logs"""
        return self.logger.get_logs(level, last_n)


# Global singleton instance
_server_logger: Optional[ServerLogger] = None


def get_server_logger() -> ServerLogger:
    """Get global server logger singleton"""
    global _server_logger
    if _server_logger is None:
        _server_logger = ServerLogger()
    return _server_logger
