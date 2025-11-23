"""
Code generation orchestrator.

Coordinates code generation using DSPy modules.
Follows SRP: Code generation workflow only.
"""

import dspy
from typing import Dict, Any

from src.common.types import ModuleSpec, GeneratedCode
from src.common.config import settings
from src.common.utils import count_lines, extract_imports
from src.codegen.signatures import (
    PythonCodeGenSignature,
    CodeReviewSignature,
    ErrorFixSignature
)
from src.codegen.pot_module import create_pot_module


class CodeGenerator:
    """Generates code using DSPy ProgramOfThought"""

    def __init__(self):
        # Code generation with POT (includes execution)
        self.code_gen_pot = create_pot_module(PythonCodeGenSignature)

        # Code review for quality check
        self.code_reviewer = dspy.ChainOfThought(CodeReviewSignature)

        # Error fixing
        self.error_fixer = dspy.ChainOfThought(ErrorFixSignature)

    def generate(
        self,
        spec: ModuleSpec,
        approach: str
    ) -> GeneratedCode:
        """
        Generate code for a module specification.

        Args:
            spec: Module specification
            approach: Algorithmic approach

        Returns: Generated code with metadata
        """
        # Build constraints
        constraints = self._build_constraints(spec)

        # Generate code using POT
        result = self.code_gen_pot(
            specification=spec.purpose,
            dependencies=", ".join(spec.dependencies),
            constraints=constraints,
            approach=approach
        )

        # Extract imports from generated code
        imports = extract_imports(result.code)

        # Verify line count
        line_count = count_lines(result.code)
        if line_count > spec.max_lines:
            # Code too long, need to refactor
            # TODO: implement auto-splitting
            pass

        return GeneratedCode(
            code=result.code,
            imports=imports or result.imports,
            complexity=result.complexity_analysis,
            execution_result=None  # POT already executed it
        )

    def review_code(
        self,
        code: str,
        specification: str
    ) -> Dict[str, Any]:
        """Review generated code for quality"""
        result = self.code_reviewer(
            code=code,
            specification=specification
        )

        return {
            "issues": result.issues,
            "suggestions": result.suggestions,
            "quality_score": result.quality_score
        }

    def fix_errors(
        self,
        code: str,
        error_messages: str,
        specification: str
    ) -> GeneratedCode:
        """Fix errors in code"""
        result = self.error_fixer(
            code=code,
            error_messages=error_messages,
            specification=specification
        )

        imports = extract_imports(result.fixed_code)

        return GeneratedCode(
            code=result.fixed_code,
            imports=imports,
            complexity=None,  # Reuse original
            execution_result={"changes": result.changes_made}
        )

    def _build_constraints(self, spec: ModuleSpec) -> str:
        """Build constraint string"""
        constraints = [
            f"Maximum {spec.max_lines} lines",
            "Follow SOLID principles",
            "Single Responsibility Principle"
        ]

        if settings.enable_type_hints:
            constraints.append("Include type hints")

        if settings.enable_docstrings:
            constraints.append("Include docstrings")

        return ". ".join(constraints)
