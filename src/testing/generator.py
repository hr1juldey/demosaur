"""
Test generation using DSPy.

Generates pytest test suites for generated code.
Follows SRP: Test generation only.
"""

import dspy
from typing import List

from src.common.types import ModuleSpec, TestSpec


class TestGenSignature(dspy.Signature):
    """Generate comprehensive pytest test suite"""

    # Inputs
    code: str = dspy.InputField(desc="Code to test")
    module_purpose: str = dspy.InputField(desc="What the module does")
    spec: str = dspy.InputField(desc="Module specification")

    # Outputs
    test_code: str = dspy.OutputField(
        desc="Complete pytest test code"
    )
    test_cases: List[str] = dspy.OutputField(
        desc="List of test case descriptions"
    )
    fixtures: str = dspy.OutputField(
        desc="Pytest fixtures if needed"
    )


class TestGenerator:
    """Generates pytest tests using DSPy"""

    def __init__(self):
        self.test_gen = dspy.ChainOfThought(TestGenSignature)

    def generate_tests(
        self,
        code: str,
        spec: ModuleSpec
    ) -> str:
        """
        Generate pytest tests for code.

        Args:
            code: Source code to test
            spec: Module specification

        Returns: Pytest test code
        """
        result = self.test_gen(
            code=code,
            module_purpose=spec.purpose,
            spec=self._format_spec(spec)
        )

        # Combine test code with fixtures
        full_test_code = self._combine_test_parts(
            result.test_code,
            result.fixtures
        )

        return full_test_code

    def _format_spec(self, spec: ModuleSpec) -> str:
        """Format spec for DSPy"""
        return (
            f"Module: {spec.name}\n"
            f"Purpose: {spec.purpose}\n"
            f"Dependencies: {', '.join(spec.dependencies)}\n"
            f"Max lines: {spec.max_lines}"
        )

    def _combine_test_parts(
        self,
        test_code: str,
        fixtures: str
    ) -> str:
        """Combine test code and fixtures"""
        parts = []

        # Standard imports
        parts.append("import pytest")
        parts.append("from typing import Any")
        parts.append("")

        # Fixtures
        if fixtures and fixtures.strip():
            parts.append(fixtures)
            parts.append("")

        # Test code
        parts.append(test_code)

        return "\n".join(parts)
