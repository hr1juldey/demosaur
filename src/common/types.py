"""
Shared type definitions for Code Intern MCP Server.

All dataclasses and type aliases used across modules.
Follows SRP: Single source of truth for data structures.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal, Any
from enum import Enum


class TaskStatus(Enum):
    """Task lifecycle states"""
    CREATED = "created"
    GATHERING_REQUIREMENTS = "gathering_requirements"
    PLANNING = "planning"
    GENERATING = "generating"
    TESTING = "testing"
    REFINING = "refining"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class Requirements:
    """User requirements gathered interactively"""
    goal: str
    approach: str
    technologies: List[str]
    libraries: Dict[str, List[str]]  # lib_name -> [features]
    docs: Optional[List[str]] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModuleSpec:
    """Specification for a single code module"""
    name: str
    purpose: str
    dependencies: List[str]
    max_lines: int = 100
    complexity_target: Optional[str] = None  # e.g., "O(n)"


@dataclass
class TestSpec:
    """Specification for tests"""
    module_name: str
    test_type: Literal["unit", "integration", "performance"]
    test_cases: List[str]
    fixtures: Optional[str] = None


@dataclass
class CodePlan:
    """Complete plan for code generation"""
    modules: List[ModuleSpec]
    dependencies: Dict[str, List[str]]  # module -> [dependencies]
    test_plan: List[TestSpec]
    performance_targets: Dict[str, str]


@dataclass
class PerformanceMetrics:
    """Measured performance of code"""
    execution_time: float  # seconds
    memory_peak: float  # MB
    cpu_usage: float  # percentage
    time_complexity: Optional[str] = None
    space_complexity: Optional[str] = None


@dataclass
class TestResults:
    """Results from test execution"""
    total: int
    passed: int
    failed: int
    errors: List[str]
    duration: float


@dataclass
class GeneratedCode:
    """Generated code with metadata"""
    code: str
    imports: List[str]
    complexity: Optional[str] = None
    execution_result: Optional[Dict[str, Any]] = None


@dataclass
class ModuleResult:
    """Result of generating a single module"""
    module_name: str
    code: str
    tests: str
    iterations: int
    final_score: float
    metrics: PerformanceMetrics
    test_results: TestResults
    status: Literal["success", "partial", "failed"]
    notes: str = ""


@dataclass
class DevelopmentReport:
    """Complete report of development process"""
    task_id: str
    modules: List[ModuleResult]
    total_iterations: int
    success_rate: float
    error_trail: List[Dict[str, Any]]
    timestamp: str
