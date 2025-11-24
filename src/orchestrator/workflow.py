"""
Main workflow orchestrator.

Coordinates all phases of code generation workflow.
Follows SRP: Workflow coordination only.
"""

from typing import Dict, Any

from src.common.types import (
    TaskStatus,
    ModuleResult,
    PerformanceMetrics
)
from src.common.config import settings
from src.requirements.gatherer import RequirementGatherer
from src.planning.planner import CodePlanner
from src.codegen.generator import CodeGenerator
from src.testing.generator import TestGenerator
from src.testing.runner import TestRunner
from src.refinement.refiner import CodeRefiner
from src.refinement.scorer import QualityScorer
from src.orchestrator.state import TaskState
from src.orchestrator.logger import AsyncLogger, TaskLogger


class WorkflowOrchestrator:
    """Orchestrates entire code generation workflow"""

    def __init__(self, task_state: TaskState):
        self.state = task_state
        self.logger = TaskLogger(AsyncLogger(task_state.task_id))

        # Initialize components
        self.req_gatherer = RequirementGatherer()
        self.planner = CodePlanner()
        self.code_gen = CodeGenerator()
        self.test_gen = TestGenerator()
        self.test_runner = TestRunner()
        self.refiner = CodeRefiner()
        self.scorer = QualityScorer()

    async def run(self) -> Dict[str, Any]:
        """
        Run complete workflow.

        Returns: Final results
        """
        try:
            # Phase 1: Already done by MCP (requirements gathered)
            await self.logger.progress(
                "Starting planning phase",
                progress=0.2
            )

            # Phase 2: Planning
            self.state.status = TaskStatus.PLANNING
            plan = self.planner.create_plan(self.state.requirements)
            self.state.plan = plan

            await self.logger.info(
                f"Planned {len(plan.modules)} modules",
                modules=[m.name for m in plan.modules]
            )

            # Phase 3: Generate each module
            self.state.status = TaskStatus.GENERATING
            total_modules = len(plan.modules)

            for idx, module_spec in enumerate(plan.modules):
                progress = 0.2 + (0.6 * (idx / total_modules))
                await self.logger.progress(
                    f"Generating module {module_spec.name}",
                    progress=progress
                )

                result = await self._generate_module(module_spec)
                self.state.module_results[module_spec.name] = result

            # Phase 4: Complete
            self.state.status = TaskStatus.COMPLETED
            await self.logger.progress("Workflow complete", progress=1.0)

            return self.state.to_dict()

        except Exception as e:
            self.state.status = TaskStatus.FAILED
            await self.logger.error(f"Workflow failed: {str(e)}")
            raise

    async def _generate_module(self, spec) -> ModuleResult:
        """Generate single module with iterative refinement"""
        self.state.current_module = spec.name
        iteration = 0
        best_score = 0.0
        best_code = None
        best_tests = None

        for iteration in range(settings.max_iterations_per_module):
            self.state.current_iteration = iteration + 1

            await self.logger.info(
                f"Module {spec.name}, iteration {iteration + 1}"
            )

            # Generate code
            code = self.code_gen.generate(
                spec,
                self.state.requirements.approach
            )

            # Generate tests
            tests = self.test_gen.generate_tests(code.code, spec)

            # Run tests
            test_results = await self.test_runner.run_tests(
                code.code,
                tests,
                spec.name
            )

            # Measure performance (placeholder)
            metrics = PerformanceMetrics(
                execution_time=0.1,
                memory_peak=10.0,
                cpu_usage=50.0
            )

            # Calculate score
            score = self.scorer.calculate_score(test_results, metrics)

            await self.logger.info(
                f"Score: {score:.2f}",
                iteration=iteration + 1,
                score=score
            )

            if score > best_score:
                best_score = score
                best_code = code
                best_tests = tests

            # Check if good enough
            if score >= settings.min_score_threshold:
                break

            # Refine if needed
            if self.scorer.should_refine(score):
                code = self.refiner.refine(code, test_results, metrics, spec)

        # Return best result
        status = "success" if best_score >= settings.min_score_threshold else "partial"

        return ModuleResult(
            module_name=spec.name,
            code=best_code.code if best_code else "",
            tests=best_tests or "",
            iterations=iteration + 1,
            final_score=best_score,
            metrics=metrics,
            test_results=test_results,
            status=status
        )
