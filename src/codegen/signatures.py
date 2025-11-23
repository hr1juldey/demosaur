"""
DSPy signatures for code generation.

Defines input/output for code generation tasks.
Follows SRP: Signature definitions only.
"""

import dspy
from typing import List


class PythonCodeGenSignature(dspy.Signature):
    """Generate production-quality Python code"""

    # Inputs
    specification: str = dspy.InputField(
        desc="Detailed specification of what to build"
    )
    dependencies: str = dspy.InputField(
        desc="Required dependencies and imports"
    )
    constraints: str = dspy.InputField(
        desc="Constraints like max lines, type hints, docstrings"
    )
    approach: str = dspy.InputField(
        desc="Algorithmic approach to use"
    )

    # Outputs
    code: str = dspy.OutputField(
        desc="Complete, working Python code"
    )
    imports: List[str] = dspy.OutputField(
        desc="Required import statements"
    )
    complexity_analysis: str = dspy.OutputField(
        desc="Time and space complexity analysis"
    )
    docstring: str = dspy.OutputField(
        desc="Module-level docstring"
    )


class CodeReviewSignature(dspy.Signature):
    """Review generated code for quality"""

    # Inputs
    code: str = dspy.InputField(desc="Code to review")
    specification: str = dspy.InputField(desc="Original specification")

    # Outputs
    issues: List[str] = dspy.OutputField(
        desc="List of issues found"
    )
    suggestions: List[str] = dspy.OutputField(
        desc="Improvement suggestions"
    )
    quality_score: str = dspy.OutputField(
        desc="Quality score 0-10 with rationale"
    )


class CodeOptimizationSignature(dspy.Signature):
    """Optimize code for performance"""

    # Inputs
    code: str = dspy.InputField(desc="Code to optimize")
    performance_metrics: str = dspy.InputField(
        desc="Current performance metrics"
    )
    target_complexity: str = dspy.InputField(
        desc="Target time/space complexity"
    )

    # Outputs
    optimized_code: str = dspy.OutputField(
        desc="Optimized code"
    )
    improvements: List[str] = dspy.OutputField(
        desc="List of optimizations made"
    )
    new_complexity: str = dspy.OutputField(
        desc="New complexity after optimization"
    )


class ErrorFixSignature(dspy.Signature):
    """Fix errors in code"""

    # Inputs
    code: str = dspy.InputField(desc="Code with errors")
    error_messages: str = dspy.InputField(
        desc="Error messages from execution/tests"
    )
    specification: str = dspy.InputField(desc="What code should do")

    # Outputs
    fixed_code: str = dspy.OutputField(
        desc="Code with errors fixed"
    )
    changes_made: List[str] = dspy.OutputField(
        desc="List of changes made to fix errors"
    )
    explanation: str = dspy.OutputField(
        desc="Explanation of what was wrong and how it was fixed"
    )
