"""
Iterative code refinement using DSPy Refine.

Refines code based on test failures and performance.
Follows SRP: Refinement orchestration only.
"""

import dspy
from typing import Dict, Any

from src.common.types import (
    GeneratedCode,
    TestResults,
    PerformanceMetrics,
    ModuleSpec
)
from src.refinement.scorer import QualityScorer
from src.codegen.signatures import ErrorFixSignature, CodeOptimizationSignature


class CodeRefiner:
    """Iteratively refines code using DSPy"""

    def __init__(self):
        self.error_fixer = dspy.ChainOfThought(ErrorFixSignature)
        self.optimizer = dspy.ChainOfThought(CodeOptimizationSignature)
        self.scorer = QualityScorer()

        # Refine module for iterative improvement
        self.refine_module = dspy.Refine(
            module=self.error_fixer,
            N=5,  # Max refinement attempts
            reward_fn=self._reward_function,
            threshold=0.9
        )

    def refine(
        self,
        code: GeneratedCode,
        test_results: TestResults,
        metrics: PerformanceMetrics,
        spec: ModuleSpec
    ) -> GeneratedCode:
        """
        Refine code based on test results and performance.

        Args:
            code: Generated code
            test_results: Test results
            metrics: Performance metrics
            spec: Module specification

        Returns: Refined code
        """
        # Calculate current score
        score = self.scorer.calculate_score(test_results, metrics)

        if not self.scorer.should_refine(score):
            # Already good enough
            return code

        # Decide what to refine
        if test_results.failed > 0 or test_results.errors:
            # Fix test failures
            return self._fix_test_failures(
                code,
                test_results,
                spec
            )
        else:
            # Optimize performance
            return self._optimize_performance(
                code,
                metrics,
                spec
            )

    def _fix_test_failures(
        self,
        code: GeneratedCode,
        test_results: TestResults,
        spec: ModuleSpec
    ) -> GeneratedCode:
        """Fix code based on test failures"""
        error_messages = "\n".join(test_results.errors)

        result = self.error_fixer(
            code=code.code,
            error_messages=error_messages,
            specification=spec.purpose
        )

        return GeneratedCode(
            code=result.fixed_code,
            imports=code.imports,
            complexity=code.complexity
        )

    def _optimize_performance(
        self,
        code: GeneratedCode,
        metrics: PerformanceMetrics,
        spec: ModuleSpec
    ) -> GeneratedCode:
        """Optimize code for better performance"""
        metrics_str = (
            f"Execution time: {metrics.execution_time:.3f}s, "
            f"Memory: {metrics.memory_peak:.2f}MB, "
            f"Complexity: {metrics.time_complexity or 'unknown'}"
        )

        target = spec.complexity_target or "O(n)"

        result = self.optimizer(
            code=code.code,
            performance_metrics=metrics_str,
            target_complexity=target
        )

        return GeneratedCode(
            code=result.optimized_code,
            imports=code.imports,
            complexity=result.new_complexity
        )

    def _reward_function(self, prediction) -> float:
        """Reward function for DSPy Refine (placeholder)"""
        # TODO: Implement actual reward based on test results
        return 0.8
