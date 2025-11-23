"""
Code planning orchestrator using DSPy.

Plans module structure, dependencies, and tests.
Follows SRP: Planning orchestration only.
"""

import dspy
from typing import List, Dict

from src.common.types import Requirements, CodePlan, ModuleSpec, TestSpec
from src.common.config import settings
from src.planning.signatures import (
    ModulePlannerSignature,
    TestPlannerSignature,
    DependencyAnalyzerSignature,
    ComplexityEstimatorSignature
)


class CodePlanner:
    """Plans code architecture using DSPy"""

    def __init__(self):
        # Initialize DSPy modules with Chain of Thought
        self.module_planner = dspy.ChainOfThought(ModulePlannerSignature)
        self.test_planner = dspy.ChainOfThought(TestPlannerSignature)
        self.dependency_analyzer = dspy.ChainOfThought(
            DependencyAnalyzerSignature
        )
        self.complexity_estimator = dspy.ChainOfThought(
            ComplexityEstimatorSignature
        )

    def create_plan(self, requirements: Requirements) -> CodePlan:
        """
        Create comprehensive code plan from requirements.

        Args:
            requirements: User requirements

        Returns: Complete code plan
        """
        # Step 1: Plan module structure
        module_plan = self._plan_modules(requirements)

        # Step 2: Analyze dependencies
        dependencies = self._analyze_dependencies(module_plan["modules"])

        # Step 3: Plan tests
        test_plan = self._plan_tests(module_plan["modules"])

        # Step 4: Assemble final plan
        return CodePlan(
            modules=self._convert_to_module_specs(module_plan["modules"]),
            dependencies=dependencies,
            test_plan=test_plan,
            performance_targets=module_plan["performance_targets"]
        )

    def _plan_modules(
        self,
        requirements: Requirements
    ) -> Dict:
        """Plan module structure"""
        constraints = (
            f"Max {settings.max_lines_per_file} lines per file. "
            f"Follow SOLID principles. "
            f"Use type hints: {settings.enable_type_hints}. "
            f"Include docstrings: {settings.enable_docstrings}."
        )

        tech_str = ", ".join(requirements.technologies)

        result = self.module_planner(
            goal=requirements.goal,
            approach=requirements.approach,
            technologies=tech_str,
            constraints=constraints
        )

        return {
            "modules": result.modules,
            "performance_targets": result.performance_targets,
            "test_strategy": result.test_strategy
        }

    def _analyze_dependencies(
        self,
        modules: List[Dict[str, str]]
    ) -> Dict[str, List[str]]:
        """Analyze module dependencies"""
        modules_str = "\n".join([
            f"{m['name']}: {m['purpose']}" for m in modules
        ])

        result = self.dependency_analyzer(modules=modules_str)
        return result.dependency_graph

    def _plan_tests(
        self,
        modules: List[Dict[str, str]]
    ) -> List[TestSpec]:
        """Plan tests for all modules"""
        test_specs = []

        for module in modules:
            # Plan unit tests
            unit_plan = self.test_planner(
                module_name=module['name'],
                module_purpose=module['purpose'],
                code_spec=module.get('purpose', '')
            )

            test_specs.append(TestSpec(
                module_name=module['name'],
                test_type="unit",
                test_cases=unit_plan.unit_tests,
                fixtures=unit_plan.fixtures_needed
            ))

        return test_specs

    def _convert_to_module_specs(
        self,
        modules: List[Dict[str, str]]
    ) -> List[ModuleSpec]:
        """Convert dspy output to ModuleSpec objects"""
        return [
            ModuleSpec(
                name=m['name'],
                purpose=m['purpose'],
                dependencies=m.get('dependencies', '').split(','),
                max_lines=settings.max_lines_per_file
            )
            for m in modules
        ]
