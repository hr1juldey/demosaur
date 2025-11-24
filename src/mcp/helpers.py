"""
Helper functions for MCP server.

Workflow execution and streaming helpers.
Follows SRP: MCP workflow helpers only.
"""

import asyncio
from typing import AsyncIterator, Dict, Any

from src.orchestrator.workflow import WorkflowOrchestrator


async def _run_workflow(task_id: str):
    """
    Run workflow in background.

    Args:
        task_id: Task identifier
    """
    from src.mcp.fastmcp_server import state_manager, task_loggers

    state = state_manager.get_task(task_id)
    if not state:
        return

    orchestrator = WorkflowOrchestrator(state)

    try:
        await orchestrator.run()
    except Exception as e:
        logger = task_loggers.get(task_id)
        if logger:
            from src.orchestrator.logger import LogLevel
            await logger.log(
                LogLevel.ERROR,
                f"Workflow failed: {str(e)}",
                task_id=task_id,
                error=str(e)
            )


async def stream_workflow_progress(
    task_id: str
) -> AsyncIterator[Dict[str, Any]]:
    """
    Stream workflow progress in real-time.

    This is a placeholder for future streaming implementation.

    Args:
        task_id: Task identifier

    Yields:
        Progress events
    """
    from src.mcp.fastmcp_server import state_manager

    state = state_manager.get_task(task_id)
    if not state:
        yield {"error": "Task not found"}
        return

    # TODO: Implement actual streaming from orchestrator
    # For now, poll and yield updates
    while state.status.value not in ["completed", "failed", "stopped"]:
        yield {
            "task_id": task_id,
            "status": state.status.value,
            "current_module": state.current_module,
            "iteration": state.current_iteration,
            "timestamp": asyncio.get_event_loop().time()
        }

        await asyncio.sleep(1)  # Poll every second

    # Final status
    yield {
        "task_id": task_id,
        "status": state.status.value,
        "final": True
    }


def format_logs_as_text(logs: list) -> str:
    """
    Format log entries as human-readable text.

    Args:
        logs: List of log entries

    Returns:
        Formatted text
    """
    lines = []

    for log in logs:
        timestamp = log.get("timestamp", "")
        level = log.get("level", "INFO")
        message = log.get("message", "")

        lines.append(f"[{timestamp}] {level}: {message}")

        # Add metadata if present
        metadata = {
            k: v for k, v in log.items()
            if k not in ["timestamp", "level", "message"]
        }

        if metadata:
            for key, value in metadata.items():
                lines.append(f"  {key}: {value}")

    return "\n".join(lines)
