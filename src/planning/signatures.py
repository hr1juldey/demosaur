"""
DSPy signatures for code planning.

Defines input/output specifications for planning modules.
Follows SRP: Signature definitions only.
"""

import dspy
from typing import List, Dict


class ModulePlannerSignature(dspy.Signature):
    """Plan the module structure for a coding task"""

    # Inputs
    goal: str = dspy.InputField(
        desc="The main goal or feature to build"
    )
    approach: str = dspy.InputField(
        desc="Algorithmic or architectural approach"
    )
    technologies: str = dspy.InputField(
        desc="Technologies and frameworks to use"
    )
    constraints: str = dspy.InputField(
        desc="Constraints like max lines per file, SOLID principles"
    )

    # Outputs
    modules: List[Dict[str, str]] = dspy.OutputField(
        desc="List of modules with name, purpose, dependencies"
    )
    test_strategy: str = dspy.OutputField(
        desc="Overall testing strategy (unit, integration)"
    )
    performance_targets: Dict[str, str] = dspy.OutputField(
        desc="Performance targets for each module (complexity)"
    )
    architecture_notes: str = dspy.OutputField(
        desc="Architecture decisions and rationale"
    )


class TestPlannerSignature(dspy.Signature):
    """Plan comprehensive tests for a module"""

    # Inputs
    module_name: str = dspy.InputField(desc="Name of the module")
    module_purpose: str = dspy.InputField(desc="What the module does")
    code_spec: str = dspy.InputField(desc="Specification of the code")

    # Outputs
    unit_tests: List[str] = dspy.OutputField(
        desc="List of unit test scenarios"
    )
    integration_tests: List[str] = dspy.OutputField(
        desc="List of integration test scenarios"
    )
    edge_cases: List[str] = dspy.OutputField(
        desc="Edge cases to test"
    )
    fixtures_needed: str = dspy.OutputField(
        desc="Test fixtures and setup code needed"
    )


class DependencyAnalyzerSignature(dspy.Signature):
    """Analyze dependencies between modules"""

    # Inputs
    modules: str = dspy.InputField(
        desc="List of modules with their purposes"
    )

    # Outputs
    dependency_graph: Dict[str, List[str]] = dspy.OutputField(
        desc="Module -> list of dependencies"
    )
    build_order: List[str] = dspy.OutputField(
        desc="Recommended order to build modules"
    )
    circular_dependencies: List[str] = dspy.OutputField(
        desc="Any circular dependencies detected"
    )


class ComplexityEstimatorSignature(dspy.Signature):
    """Estimate time/space complexity for code spec"""

    # Inputs
    specification: str = dspy.InputField(
        desc="Code specification and algorithm description"
    )
    approach: str = dspy.InputField(
        desc="Algorithmic approach"
    )

    # Outputs
    time_complexity: str = dspy.OutputField(
        desc="Estimated time complexity (O notation)"
    )
    space_complexity: str = dspy.OutputField(
        desc="Estimated space complexity (O notation)"
    )
    reasoning: str = dspy.OutputField(
        desc="Explanation of complexity analysis"
    )
