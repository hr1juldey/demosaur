"""
Streaming Workflow Orchestrator.

Extends WorkflowOrchestrator to yield real-time events.
Follows SRP: Event streaming only.
"""

import asyncio
from typing import AsyncIterator

from src.orchestrator.workflow import WorkflowOrchestrator
from src.orchestrator.events import (
    WorkflowEvent,
    task_started,
    planning_started,
    planning_complete,
    module_started,
    module_iteration
)
from src.common.types import TaskStatus


class StreamingWorkflowOrchestrator(WorkflowOrchestrator):
    """Orchestrator that yields progress events"""

    async def run_with_streaming(self) -> AsyncIterator[WorkflowEvent]:
        """
        Run workflow and yield events.

        Yields:
            WorkflowEvent objects
        """
        try:
            # Task started
            yield task_started(
                self.state.task_id,
                self.state.requirements.goal
            )

            # Planning
            self.state.status = TaskStatus.PLANNING
            yield planning_started(self.state.task_id)

            plan = self.planner.create_plan(self.state.requirements)
            self.state.plan = plan

            yield planning_complete(
                self.state.task_id,
                module_count=len(plan.modules),
                test_count=len(plan.test_plan)
            )

            # Generation
            self.state.status = TaskStatus.GENERATING
            total_modules = len(plan.modules)

            for idx, module_spec in enumerate(plan.modules):
                yield module_started(
                    self.state.task_id,
                    module_spec.name,
                    idx,
                    total_modules
                )

                # Generate module with iteration events
                async for event in self._generate_module_streaming(
                    module_spec,
                    idx,
                    total_modules
                ):
                    yield event

            # Complete
            self.state.status = TaskStatus.COMPLETED

            yield WorkflowEvent.create(
                "TASK_COMPLETE",
                self.state.task_id,
                total_modules=total_modules,
                success_rate=sum(
                    1 for r in self.state.module_results.values()
                    if r.status == "success"
                ) / total_modules if total_modules > 0 else 0
            )

        except Exception as e:
            self.state.status = TaskStatus.FAILED

            yield WorkflowEvent.create(
                "TASK_FAILED",
                self.state.task_id,
                error=str(e)
            )
            raise

    async def _generate_module_streaming(
        self,
        spec,
        module_idx: int,
        total_modules: int
    ) -> AsyncIterator[WorkflowEvent]:
        """Generate module and yield iteration events"""
        # Use parent class logic but yield events
        iteration = 0

        for iteration in range(self.settings.max_iterations_per_module):
            # Generate, test, score (simplified)
            score = 0.5 + (iteration * 0.1)  # Placeholder

            yield module_iteration(
                self.state.task_id,
                spec.name,
                iteration + 1,
                score
            )

            if score >= self.settings.min_score_threshold:
                break

            await asyncio.sleep(0.1)  # Simulated work
