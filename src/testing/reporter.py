"""
Test result reporting.

Formats test results for display and logging.
Follows SRP: Result formatting only.
"""

from typing import Dict, Any
from src.common.types import TestResults


class TestReporter:
    """Formats test results for reporting"""

    @staticmethod
    def format_results(results: TestResults) -> str:
        """Format test results as human-readable string"""
        lines = []

        lines.append(f"Total tests: {results.total}")
        lines.append(f"Passed: {results.passed} ✓")
        lines.append(f"Failed: {results.failed} ✗")

        pass_rate = (results.passed / results.total * 100) if results.total > 0 else 0
        lines.append(f"Pass rate: {pass_rate:.1f}%")

        if results.errors:
            lines.append("\nErrors:")
            for error in results.errors:
                lines.append(f"  - {error}")

        lines.append(f"\nDuration: {results.duration:.2f}s")

        return "\n".join(lines)

    @staticmethod
    def to_dict(results: TestResults) -> Dict[str, Any]:
        """Convert test results to dictionary"""
        return {
            "total": results.total,
            "passed": results.passed,
            "failed": results.failed,
            "errors": results.errors,
            "duration": results.duration,
            "pass_rate": (results.passed / results.total) if results.total > 0 else 0
        }

    @staticmethod
    def format_summary(results: TestResults) -> str:
        """Format brief summary"""
        if results.total == 0:
            return "No tests run"

        status = "✓ PASSED" if results.failed == 0 else "✗ FAILED"
        return f"{status}: {results.passed}/{results.total} tests passed"
