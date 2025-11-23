"""
Additional MCP Tools - Streaming and Intervention.

Extra tools beyond basic task management.
Follows SRP: Tool definitions only.
"""

from src.mcp.fastmcp_server import mcp, state_manager


@mcp.tool()
async def stream_task_progress(task_id: str):
    """
    Stream real-time progress updates for a task.

    Instead of polling get_task_status(), this streams events as they happen.

    Args:
        task_id: Task identifier

    Yields:
        Progress events in real-time
    """
    from src.orchestrator.streaming import StreamingWorkflowOrchestrator

    state = state_manager.get_task(task_id)
    if not state:
        yield {"error": "Task not found"}
        return

    orchestrator = StreamingWorkflowOrchestrator(state)

    async for event in orchestrator.run_with_streaming():
        yield event.to_dict()


@mcp.tool()
async def intervene_in_task(task_id: str, guidance: str) -> dict:
    """
    Send guidance or correction to a running task.

    The intern will apply this in the next refinement iteration.

    Args:
        task_id: Task identifier
        guidance: Your guidance or correction

    Returns:
        Acknowledgment
    """
    from src.orchestrator.intervention import add_intervention

    state = state_manager.get_task(task_id)
    if not state:
        return {"error": "Task not found"}

    add_intervention(task_id, guidance)

    return {
        "status": "intervention_queued",
        "message": f"Guidance queued for task {task_id}",
        "guidance": guidance
    }


@mcp.tool()
async def cancel_task(task_id: str, reason: str = "") -> dict:
    """
    Cancel a running task.

    Args:
        task_id: Task identifier
        reason: Optional reason for cancellation

    Returns:
        Cancellation confirmation
    """
    from src.common.types import TaskStatus

    state = state_manager.get_task(task_id)
    if not state:
        return {"error": "Task not found"}

    state.status = TaskStatus.STOPPED
    state.metadata['stop_reason'] = reason

    return {
        "status": "stopped",
        "task_id": task_id,
        "reason": reason
    }
