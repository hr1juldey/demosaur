"""
Quality scoring for generated code.

Calculates quality scores based on tests and performance.
Follows SRP: Scoring only.
"""

from src.common.types import TestResults, PerformanceMetrics
from src.common.config import settings


class QualityScorer:
    """Calculates quality scores for code"""

    @staticmethod
    def calculate_score(
        test_results: TestResults,
        metrics: PerformanceMetrics
    ) -> float:
        """
        Calculate overall quality score.

        Args:
            test_results: Test execution results
            metrics: Performance metrics

        Returns: Score between 0 and 1
        """
        # Test score (70% weight)
        test_score = QualityScorer._calculate_test_score(test_results)

        # Performance score (30% weight)
        perf_score = QualityScorer._calculate_performance_score(metrics)

        # Weighted combination
        return 0.7 * test_score + 0.3 * perf_score

    @staticmethod
    def _calculate_test_score(results: TestResults) -> float:
        """Calculate score from test results"""
        if results.total == 0:
            return 0.0

        pass_rate = results.passed / results.total

        # Penalty for errors
        error_penalty = len(results.errors) * 0.05
        pass_rate = max(0.0, pass_rate - error_penalty)

        return pass_rate

    @staticmethod
    def _calculate_performance_score(metrics: PerformanceMetrics) -> float:
        """Calculate score from performance metrics"""
        # Time score (faster is better)
        time_score = 1.0 if metrics.execution_time < 0.1 else \
                     0.8 if metrics.execution_time < 1.0 else \
                     0.5 if metrics.execution_time < 5.0 else 0.2

        # Memory score (less is better)
        memory_score = 1.0 if metrics.memory_peak < 10 else \
                       0.8 if metrics.memory_peak < 50 else \
                       0.5 if metrics.memory_peak < 100 else 0.2

        # Complexity score
        complexity_score = QualityScorer._score_complexity(
            metrics.time_complexity
        )

        # Average
        return (time_score + memory_score + complexity_score) / 3

    @staticmethod
    def _score_complexity(complexity: str | None) -> float:
        """Score based on time complexity"""
        if not complexity:
            return 0.5

        # Better complexities get higher scores
        complexity_scores = {
            "O(1)": 1.0,
            "O(log n)": 0.9,
            "O(n)": 0.8,
            "O(n log n)": 0.7,
            "O(n^2)": 0.5,
            "O(n^3)": 0.3,
            "O(2^n)": 0.1
        }

        return complexity_scores.get(complexity, 0.5)

    @staticmethod
    def should_refine(score: float) -> bool:
        """Determine if code should be refined"""
        return score < settings.min_score_threshold

    @staticmethod
    def format_score(score: float) -> str:
        """Format score for display"""
        percentage = score * 100
        status = "✓ EXCELLENT" if score >= 0.9 else \
                 "✓ GOOD" if score >= settings.min_score_threshold else \
                 "⚠ NEEDS IMPROVEMENT" if score >= 0.6 else \
                 "✗ POOR"

        return f"{status} ({percentage:.1f}%)"
