"""
Execution Log Capture - Captures subprocess output.

Captures stdout/stderr from code execution and tests.
Follows SRP: Output capture only.
"""

import asyncio
import subprocess
from typing import Optional, List
from pathlib import Path

from src.orchestrator.logger import AsyncLogger, LogLevel


class ExecutionLogCapture:
    """Captures execution output to logger"""

    def __init__(self, logger: AsyncLogger):
        self.logger = logger

    async def run_command(
        self,
        cmd: List[str],
        cwd: Optional[Path] = None,
        timeout: int = 30
    ) -> subprocess.CompletedProcess:
        """
        Run command and capture output to logger.

        Args:
            cmd: Command and arguments
            cwd: Working directory
            timeout: Timeout in seconds

        Returns:
            CompletedProcess with results
        """
        await self.logger.log(
            LogLevel.INFO,
            f"Executing command: {' '.join(cmd)}",
            command=cmd,
            cwd=str(cwd) if cwd else None
        )

        try:
            # Run command with output capture
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )

            # Wait with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                raise TimeoutError(f"Command timed out after {timeout}s")

            # Decode output
            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')

            # Log output
            if stdout_str:
                await self.logger.log(
                    LogLevel.INFO,
                    "Command stdout",
                    stdout=stdout_str
                )

            if stderr_str:
                level = LogLevel.ERROR if proc.returncode != 0 else LogLevel.WARN
                await self.logger.log(
                    level,
                    "Command stderr",
                    stderr=stderr_str
                )

            # Log completion
            await self.logger.log(
                LogLevel.INFO,
                f"Command completed with code {proc.returncode}",
                returncode=proc.returncode
            )

            # Create CompletedProcess-like object
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=proc.returncode,
                stdout=stdout,
                stderr=stderr
            )

        except Exception as e:
            await self.logger.log(
                LogLevel.ERROR,
                f"Command failed: {str(e)}",
                error=str(e),
                command=cmd
            )
            raise
