"""
MCP Resources for exposing logs and generated code.

Resources are read-only data sources Claude can access.
Follows SRP: Resource definitions only.
"""

from fastmcp import FastMCP
from typing import Optional

# Import from fastmcp_server
from src.mcp.fastmcp_server import (
    mcp,
    state_manager,
    task_loggers
)
from src.orchestrator.logger import LogLevel


# ============================================================================
# RESOURCES (Read-only data Claude can access)
# ============================================================================

@mcp.resource("logs://server")
async def get_server_logs(level: Optional[str] = None) -> str:
    """
    Get MCP server operation logs.

    These are logs about the server itself, not task-specific logs.

    Args:
        level: Optional filter (DEBUG, INFO, WARN, ERROR)

    Returns:
        Server logs as formatted text
    """
    from src.orchestrator.server_logger import get_server_logger

    server_logger = get_server_logger()

    # Parse level filter
    log_level = None
    if level:
        try:
            log_level = LogLevel[level.upper()]
        except KeyError:
            pass

    logs = server_logger.get_logs(level=log_level)

    # Format logs
    lines = ["=" * 60, "MCP Server Logs", "=" * 60, ""]

    for log in logs:
        lines.append(
            f"[{log['timestamp']}] {log['level']}: {log['message']}"
        )

    return "\n".join(lines)


@mcp.resource("logs://task/{task_id}/workflow")
async def get_task_workflow_logs(task_id: str, level: Optional[str] = None) -> str:
    """
    Get workflow logs for a task (planning, code generation, refinement).

    Args:
        task_id: Task identifier
        level: Optional filter (DEBUG, INFO, WARN, ERROR, PROGRESS)

    Returns:
        Workflow logs as formatted text
    """
    from src.orchestrator.log_manager import get_log_manager

    try:
        log_mgr = get_log_manager(task_id)
    except KeyError:
        return f"No logs found for task {task_id}"

    # Parse level filter
    log_level = None
    if level:
        try:
            log_level = LogLevel[level.upper()]
        except KeyError:
            pass

    logs = log_mgr.get_workflow_logs(level=log_level)

    # Format logs
    lines = ["=" * 60, f"Workflow Logs: {task_id}", "=" * 60, ""]

    for log in logs:
        lines.append(
            f"[{log['timestamp']}] {log['level']}: {log['message']}"
        )

    return "\n".join(lines)


@mcp.resource("logs://task/{task_id}/progress")
async def get_task_progress_logs(task_id: str) -> str:
    """
    Get only PROGRESS level logs for a task.

    Useful for monitoring high-level progress without details.

    Args:
        task_id: Task identifier

    Returns:
        Progress logs only
    """
    return await get_task_workflow_logs(task_id, level="PROGRESS")


@mcp.resource("logs://task/{task_id}/execution")
async def get_task_execution_logs(task_id: str, level: Optional[str] = None) -> str:
    """
    Get execution logs for a task (code/test execution output).

    Args:
        task_id: Task identifier
        level: Optional filter (DEBUG, INFO, WARN, ERROR)

    Returns:
        Execution logs as formatted text
    """
    from src.orchestrator.log_manager import get_log_manager

    try:
        log_mgr = get_log_manager(task_id)
    except KeyError:
        return f"No execution logs found for task {task_id}"

    # Parse level filter
    log_level = None
    if level:
        try:
            log_level = LogLevel[level.upper()]
        except KeyError:
            pass

    logs = log_mgr.get_execution_logs(level=log_level)

    # Format logs
    lines = ["=" * 60, f"Execution Logs: {task_id}", "=" * 60, ""]

    for log in logs:
        lines.append(
            f"[{log['timestamp']}] {log['level']}: {log['message']}"
        )
        # Add stdout/stderr if present
        if 'stdout' in log and log['stdout']:
            lines.append("  STDOUT:")
            lines.extend(f"    {line}" for line in log['stdout'].split('\n'))
        if 'stderr' in log and log['stderr']:
            lines.append("  STDERR:")
            lines.extend(f"    {line}" for line in log['stderr'].split('\n'))

    return "\n".join(lines)


@mcp.resource("code://task/{task_id}/module/{module_name}")
async def get_generated_code(task_id: str, module_name: str) -> str:
    """
    Get generated code for a specific module.

    Args:
        task_id: Task identifier
        module_name: Name of the module

    Returns:
        Generated Python code
    """
    state = state_manager.get_task(task_id)
    if not state:
        return f"Task {task_id} not found"

    result = state.module_results.get(module_name)
    if not result:
        return f"Module {module_name} not found in task {task_id}"

    return f"""# Generated Code: {module_name}
# Score: {result.final_score:.2f}
# Iterations: {result.iterations}
# Status: {result.status}

{result.code}
"""


@mcp.resource("tests://task/{task_id}/module/{module_name}")
async def get_generated_tests(task_id: str, module_name: str) -> str:
    """
    Get generated tests for a specific module.

    Args:
        task_id: Task identifier
        module_name: Name of the module

    Returns:
        Generated pytest test code
    """
    state = state_manager.get_task(task_id)
    if not state:
        return f"Task {task_id} not found"

    result = state.module_results.get(module_name)
    if not result:
        return f"Module {module_name} not found"

    return result.tests


@mcp.resource("report://task/{task_id}")
async def get_task_report(task_id: str) -> str:
    """
    Get comprehensive development report for a task.

    Includes all modules, metrics, error trails.

    Args:
        task_id: Task identifier

    Returns:
        Formatted development report
    """
    state = state_manager.get_task(task_id)
    if not state:
        return f"Task {task_id} not found"

    report = state.generate_report()

    lines = [
        "=" * 60,
        f"Development Report: {task_id}",
        "=" * 60,
        "",
        f"Status: {state.status.value}",
        f"Total Iterations: {report.total_iterations}",
        f"Success Rate: {report.success_rate * 100:.1f}%",
        "",
        "Modules:",
    ]

    for module in report.modules:
        lines.extend([
            f"\n  {module.module_name}:",
            f"    Score: {module.final_score:.2f}",
            f"    Iterations: {module.iterations}",
            f"    Status: {module.status}",
            f"    Tests: {module.test_results.passed}/{module.test_results.total}"
        ])

    return "\n".join(lines)
