"""
Performance metrics measurement.

Measures code execution time, memory usage, complexity.
Follows SRP: Performance measurement only.
"""

import time
import tracemalloc
from typing import Optional
import re

from src.common.types import PerformanceMetrics


class MetricsCollector:
    """Collects performance metrics for code execution"""

    @staticmethod
    def measure_execution(
        code_callable,
        *args,
        **kwargs
    ) -> PerformanceMetrics:
        """
        Measure execution time and memory for a callable.

        Args:
            code_callable: Function to measure
            *args, **kwargs: Arguments to pass

        Returns: Performance metrics
        """
        # Start memory tracking
        tracemalloc.start()

        # Measure execution time
        start_time = time.perf_counter()

        try:
            code_callable(*args, **kwargs)
        except Exception:
            pass  # Still collect metrics even if code fails

        end_time = time.perf_counter()

        # Get memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        return PerformanceMetrics(
            execution_time=end_time - start_time,
            memory_peak=peak / 1024 / 1024,  # Convert to MB
            cpu_usage=0.0,  # TODO: implement CPU tracking
            time_complexity=None,
            space_complexity=None
        )

    @staticmethod
    def analyze_complexity(code: str) -> tuple[Optional[str], Optional[str]]:
        """
        Analyze time/space complexity from code structure.

        This is a simple heuristic-based analysis.
        Returns: (time_complexity, space_complexity)
        """
        time_complexity = "O(1)"  # Default
        space_complexity = "O(1)"  # Default

        # Check for loops
        if re.search(r'\bfor\b.*\bin\b', code):
            # Single loop -> O(n)
            time_complexity = "O(n)"

            # Nested loops -> O(n^2)
            nested_for = len(re.findall(r'\n\s+for\b.*\bin\b', code))
            if nested_for > 1:
                time_complexity = f"O(n^{nested_for})"

        # Check for recursion
        if re.search(r'def\s+(\w+).*:\n(?:.*\n)*?\s+\1\(', code):
            # Recursive -> at least O(n)
            time_complexity = "O(n)" if time_complexity == "O(1)" else time_complexity

        # Check for data structures
        if re.search(r'\[\]|\{\}|list\(|dict\(|set\(', code):
            # Uses data structures -> O(n) space
            space_complexity = "O(n)"

        return time_complexity, space_complexity

    @staticmethod
    def calculate_performance_score(
        metrics: PerformanceMetrics,
        target_time: float = 1.0,  # 1 second
        target_memory: float = 100.0  # 100 MB
    ) -> float:
        """
        Calculate performance score 0-1.

        Args:
            metrics: Measured metrics
            target_time: Target execution time
            target_memory: Target memory usage

        Returns: Score between 0 and 1
        """
        # Time score (inverse)
        time_score = min(1.0, target_time / max(metrics.execution_time, 0.001))

        # Memory score (inverse)
        memory_score = min(1.0, target_memory / max(metrics.memory_peak, 0.1))

        # Weighted average
        return 0.6 * time_score + 0.4 * memory_score
