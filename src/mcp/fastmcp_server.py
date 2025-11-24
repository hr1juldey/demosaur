"""
Improved FastMCP Server with proper Tools, Resources, and Streaming.

Uses FastMCP decorators and best practices.
Follows SRP: FastMCP interface only.
"""

from fastmcp import FastMCP
from typing import Dict
import asyncio

from src.common.utils import generate_task_id
from src.orchestrator.state import StateManager
from src.orchestrator.logger import AsyncLogger, LogLevel
from src.requirements.gatherer import RequirementGatherer


# Create FastMCP server
mcp = FastMCP("code-intern")

# Global state
state_manager = StateManager()
active_gatherers: Dict[str, RequirementGatherer] = {}
task_loggers: Dict[str, AsyncLogger] = {}


# ============================================================================
# TOOLS (Actions Claude can perform)
# ============================================================================

@mcp.tool()
async def start_coding_task(initial_prompt: str) -> dict:
    """
    Start a new coding task with the Code Intern.

    Args:
        initial_prompt: Brief description of what to build

    Returns:
        Task ID and first requirement question
    """
    task_id = generate_task_id()

    # Create task state
    state = state_manager.create_task(task_id)

    # Create dedicated logger for this task
    task_loggers[task_id] = AsyncLogger(task_id)

    # Start requirement gathering
    gatherer = RequirementGatherer()
    active_gatherers[task_id] = gatherer
    first_question = gatherer.start()

    await task_loggers[task_id].log(
        LogLevel.INFO,
        f"Task started: {initial_prompt}",
        task_id=task_id
    )

    return {
        "task_id": task_id,
        "status": "gathering_requirements",
        **first_question
    }


@mcp.tool()
async def answer_requirement(task_id: str, answer: str) -> dict:
    """
    Answer a requirement gathering question.

    Args:
        task_id: Task identifier
        answer: Your answer to the current question

    Returns:
        Next question or workflow start confirmation
    """
    gatherer = active_gatherers.get(task_id)
    if not gatherer:
        return {"error": "Task not found or not in gathering phase"}

    result = gatherer.answer(answer)

    # Log the answer
    logger = task_loggers.get(task_id)
    if logger:
        await logger.log(
            LogLevel.INFO,
            f"Answered: {answer[:50]}...",
            task_id=task_id
        )

    # If complete, start workflow
    if result.get("status") == "complete":
        from src.common.types import Requirements

        state = state_manager.get_task(task_id)
        req_dict = result["requirements"]
        state.requirements = Requirements(**req_dict)

        del active_gatherers[task_id]

        # Start workflow in background
        asyncio.create_task(_run_workflow(task_id))

        return {
            "status": "workflow_started",
            "task_id": task_id,
            "message": "Requirements complete! Code generation starting..."
        }

    return result


@mcp.tool()
async def get_task_status(task_id: str) -> dict:
    """
    Get current status of a coding task.

    Args:
        task_id: Task identifier

    Returns:
        Current phase, module, iteration, and progress
    """
    state = state_manager.get_task(task_id)
    if not state:
        return {"error": "Task not found"}

    progress = 0.0
    if state.plan:
        total = len(state.plan.modules)
        complete = len(state.module_results)
        progress = complete / total if total > 0 else 0.0

    return {
        "task_id": task_id,
        "status": state.status.value,
        "current_module": state.current_module,
        "iteration": state.current_iteration,
        "modules_complete": len(state.module_results),
        "total_modules": len(state.plan.modules) if state.plan else 0,
        "progress": progress
    }


# (continued in next file due to 100 line limit)
