"""
Dead Code Detection Integration.

Integrates dead code detection into code generation workflow.
Follows SRP: Integration only.
"""

from typing import Optional

from src.common.types import GeneratedCode
from src.deadcode.detector import VultureDetector
from src.deadcode.analyzer import DeadCodeAnalyzer
from src.deadcode.cleaner import DeadCodeCleaner
from src.deadcode.reporter import DeadCodeReporter


class DeadCodeIntegration:
    """Integrates dead code detection into workflow"""

    def __init__(self):
        self.detector = VultureDetector()
        self.analyzer = DeadCodeAnalyzer()
        self.cleaner = DeadCodeCleaner()
        self.reporter = DeadCodeReporter()

    async def detect_and_report(
        self,
        code: str,
        filename: str = "module.py",
        min_confidence: int = 80
    ) -> dict:
        """
        Detect dead code and return report.

        Args:
            code: Python code to analyze
            filename: Filename for context
            min_confidence: Minimum confidence threshold

        Returns:
            Dead code report dict
        """
        # Detect
        vulture_results = await self.detector.detect(
            code,
            filename,
            min_confidence
        )

        # Analyze
        report = self.analyzer.combine_results(vulture_results)
        filtered = self.analyzer.filter_by_confidence(
            report,
            min_confidence
        )

        # Format
        summary = self.reporter.format_summary(filtered)
        full_report = self.reporter.format_report(filtered)

        return {
            "summary": summary,
            "full_report": full_report,
            "total_items": filtered.total_items,
            "high_confidence": filtered.high_confidence_count,
            "token_savings": filtered.potential_token_savings
        }

    async def clean_code(
        self,
        generated: GeneratedCode,
        min_confidence: int = 100
    ) -> Optional[GeneratedCode]:
        """
        Clean dead code from generated code.

        Args:
            generated: Generated code object
            min_confidence: Only remove >= this confidence

        Returns:
            Cleaned code or None if no cleaning needed
        """
        # Detect
        vulture_results = await self.detector.detect(
            generated.code,
            "module.py",
            min_confidence
        )

        # Analyze
        report = self.analyzer.combine_results(vulture_results)

        if report.total_items == 0:
            return None

        # Clean
        result = self.cleaner.clean(
            generated.code,
            report.items,
            min_confidence
        )

        if not result.success or result.lines_removed == 0:
            return None

        # Return cleaned version
        return GeneratedCode(
            code=result.cleaned_code,
            imports=generated.imports,
            complexity=generated.complexity,
            execution_result=generated.execution_result
        )
