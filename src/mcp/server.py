"""
MCP Server implementation for Code Intern.

Exposes tools for Claude to delegate coding tasks.
Follows SRP: MCP protocol handling only.
"""

import asyncio
from typing import Dict, Any

from src.common.utils import generate_task_id
from src.orchestrator.state import StateManager
from src.orchestrator.workflow import WorkflowOrchestrator
from src.requirements.gatherer import RequirementGatherer


class CodeInternMCPServer:
    """MCP Server for code generation delegation"""

    def __init__(self):
        self.state_manager = StateManager()
        self.active_gatherers: Dict[str, RequirementGatherer] = {}

    async def start_task(self, initial_prompt: str) -> Dict[str, Any]:
        """Start new coding task"""
        task_id = generate_task_id()

        # Create task state
        state = self.state_manager.create_task(task_id)

        # Start requirement gathering
        gatherer = RequirementGatherer()
        self.active_gatherers[task_id] = gatherer

        first_question = gatherer.start()

        return {
            "status": "started",
            "task_id": task_id,
            "next_step": "requirements_gathering",
            **first_question
        }

    async def answer_question(
        self,
        task_id: str,
        answer: str
    ) -> Dict[str, Any]:
        """Answer requirement gathering question"""
        gatherer = self.active_gatherers.get(task_id)
        if not gatherer:
            return {
                "error": "Task not found or not in gathering phase"
            }

        result = gatherer.answer(answer)

        # If complete, start workflow
        if result.get("status") == "complete":
            state = self.state_manager.get_task(task_id)
            from src.common.types import Requirements

            # Convert dict to Requirements object
            req_dict = result["requirements"]
            state.requirements = Requirements(**req_dict)

            # Clean up gatherer
            del self.active_gatherers[task_id]

            # Start workflow in background
            asyncio.create_task(self._run_workflow(task_id))

            return {
                "status": "workflow_started",
                "task_id": task_id,
                "message": "Requirements complete, starting code generation"
            }

        return result

    async def _run_workflow(self, task_id: str):
        """Run workflow in background"""
        state = self.state_manager.get_task(task_id)
        if not state:
            return

        orchestrator = WorkflowOrchestrator(state)
        try:
            await orchestrator.run()
        except Exception as e:
            print(f"Workflow error: {e}")

    async def get_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status"""
        state = self.state_manager.get_task(task_id)
        if not state:
            return {"error": "Task not found"}

        return {
            "status": state.status.value,
            "current_module": state.current_module,
            "iteration": state.current_iteration,
            "modules_complete": len(state.module_results),
            "total_modules": len(state.plan.modules) if state.plan else 0
        }

    async def get_results(self, task_id: str) -> Dict[str, Any]:
        """Get final results"""
        state = self.state_manager.get_task(task_id)
        if not state:
            return {"error": "Task not found"}

        report = state.generate_report()
        return {
            "status": "completed",
            "report": report.__dict__
        }


# Global server instance
_server = None


def get_server() -> CodeInternMCPServer:
    """Get global server instance"""
    global _server
    if _server is None:
        _server = CodeInternMCPServer()
    return _server
