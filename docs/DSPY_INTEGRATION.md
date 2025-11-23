# DSPy Integration Guide

## Required DSPy Components

### 1. ProgramOfThought (POT)

**Purpose**: Generate code AND execute it to verify correctness

**Key Features**:
- Executes Python code in sandbox
- Returns both code and execution results
- Can use custom interpreters (Deno, Python)

**Usage**:
```python
from dspy import ProgramOfThought
from dspy.experimental import PythonInterpreter

# Configure interpreter
interpreter = PythonInterpreter(
    timeout=30,
    max_memory_mb=1024
)

# Create POT module
class CodeGenerator(dspy.Module):
    def __init__(self):
        self.pot = ProgramOfThought(
            signature="spec -> code: str",
            interpreter=interpreter
        )

    def forward(self, spec):
        result = self.pot(spec=spec)
        return result.code, result.execution_result
```

### 2. CodeAct

**Purpose**: Iterative code generation with action-based refinement

**Key Features**:
- Generates code in steps
- Can execute and observe results
- Refines based on execution feedback

**Usage**:
```python
from dspy import CodeAct

class IterativeCodeGenerator(dspy.Module):
    def __init__(self):
        self.codeact = CodeAct(
            signature="requirements -> code: str",
            max_actions=10
        )

    def forward(self, requirements):
        return self.codeact(requirements=requirements)
```

### 3. ReAct

**Purpose**: Reasoning + Acting pattern for complex tasks

**Key Features**:
- Alternates between reasoning and acting
- Can use tools
- Self-correcting

**Usage**:
```python
from dspy import ReAct

class PlanningAgent(dspy.Module):
    def __init__(self, tools):
        self.react = ReAct(
            signature="goal -> plan: str",
            tools=tools,
            max_iters=5
        )

    def forward(self, goal):
        return self.react(goal=goal)
```

### 4. Refine

**Purpose**: Iteratively improve outputs based on feedback

**Key Features**:
- Takes initial output + feedback
- Progressively refines
- Configurable stopping criteria

**Usage**:
```python
from dspy import Refine

class CodeRefiner(dspy.Module):
    def __init__(self):
        self.refine = Refine(
            signature="code, test_results -> improved_code: str",
            max_iters=5
        )

    def forward(self, code, test_results):
        return self.refine(
            code=code,
            test_results=format_results(test_results)
        )
```

### 5. ChainOfThought

**Purpose**: Add reasoning steps to improve quality

**Usage**:
```python
from dspy import ChainOfThought

class TestGenerator(dspy.Module):
    def __init__(self):
        self.generate = ChainOfThought(
            "code, spec -> tests: str, reasoning: str"
        )

    def forward(self, code, spec):
        result = self.generate(code=code, spec=spec)
        return result.tests
```

## DSPy Signatures

**Custom signatures for our use case**:

```python
# Planning signature
class ModulePlanner(dspy.Signature):
    """Plan the module structure for a coding task"""
    requirements: str = dspy.InputField()

    modules: List[Dict[str, str]] = dspy.OutputField(
        desc="List of modules with name, purpose, dependencies"
    )
    test_strategy: str = dspy.OutputField(
        desc="Overall testing strategy"
    )

# Code generation signature
class PythonCodeGenerator(dspy.Signature):
    """Generate production-quality Python code"""
    specification: str = dspy.InputField()
    dependencies: List[str] = dspy.InputField()
    constraints: str = dspy.InputField(
        desc="Max 100 lines, type hints required, etc"
    )

    code: str = dspy.OutputField(desc="Complete Python code")
    imports: List[str] = dspy.OutputField(desc="Required imports")
    complexity: str = dspy.OutputField(desc="Time/space complexity")

# Test generation signature
class TestGeneratorSignature(dspy.Signature):
    """Generate comprehensive pytest test suite"""
    code: str = dspy.InputField()
    module_purpose: str = dspy.InputField()

    test_code: str = dspy.OutputField(desc="Complete pytest code")
    test_cases: List[str] = dspy.OutputField(desc="Test case descriptions")
    fixtures: str = dspy.OutputField(desc="Pytest fixtures if needed")

# Refinement signature
class CodeRefinementSignature(dspy.Signature):
    """Refine code based on test failures and performance"""
    original_code: str = dspy.InputField()
    test_failures: str = dspy.InputField()
    performance_issues: str = dspy.InputField()

    refined_code: str = dspy.OutputField()
    changes_made: List[str] = dspy.OutputField()
    improvement_reasoning: str = dspy.OutputField()
```

## PythonInterpreter Configuration

**Setting up the sandbox**:

```python
from dspy.experimental import PythonInterpreter
import tempfile
import os

def create_interpreter():
    # Create temp workspace
    workspace = tempfile.mkdtemp(prefix="code_intern_")

    interpreter = PythonInterpreter(
        # Security
        timeout=30,
        max_memory_mb=1024,
        restricted_modules=[
            'os', 'sys', 'subprocess',  # System access
            'socket', 'urllib',          # Network access
        ],

        # Workspace
        working_directory=workspace,

        # Output
        capture_stdout=True,
        capture_stderr=True,

        # Cleanup
        cleanup_on_exit=True
    )

    return interpreter, workspace
```

## Tool Integration for ReAct

**Define tools for the agent**:

```python
from dspy import Tool

# Documentation fetcher tool
doc_fetcher = Tool(
    name="fetch_documentation",
    description="Fetch and parse documentation from URL",
    function=async_fetch_docs
)

# Code analyzer tool
code_analyzer = Tool(
    name="analyze_code",
    description="Analyze code for complexity and patterns",
    function=analyze_code_complexity
)

# Test runner tool
test_runner = Tool(
    name="run_tests",
    description="Execute pytest tests and return results",
    function=run_pytest
)

tools = [doc_fetcher, code_analyzer, test_runner]
```

## Ollama Configuration

**Setting up DSPy with Ollama**:

```python
import dspy
from src.common.config import settings

def configure_dspy():
    lm = dspy.LM(
        model=f"ollama_chat/{settings.model_name}",
        api_base=settings.ollama_base_url,
        api_key="",  # Not needed for Ollama
        temperature=0.7,
        max_tokens=2048
    )

    dspy.configure(lm=lm)
    return lm
```

## Complete Example: Code Generation Module

```python
from dspy import Module, ChainOfThought, ProgramOfThought
from dspy.experimental import PythonInterpreter
from src.common.types import ModuleSpec, GeneratedCode

class ProductionCodeGenerator(Module):
    """Generate production-quality code with POT"""

    def __init__(self):
        super().__init__()

        # Interpreter for POT
        self.interpreter, self.workspace = create_interpreter()

        # Planning step
        self.planner = ChainOfThought(
            "spec -> approach: str, key_functions: List[str]"
        )

        # Code generation with execution
        self.generator = ProgramOfThought(
            signature=PythonCodeGenerator,
            interpreter=self.interpreter
        )

    def forward(self, spec: ModuleSpec) -> GeneratedCode:
        # Step 1: Plan approach
        plan = self.planner(spec=spec.to_string())

        # Step 2: Generate code (POT executes it)
        constraints = f"Max {spec.max_lines} lines, type hints, docstrings"

        result = self.generator(
            specification=spec.purpose,
            dependencies=spec.dependencies,
            constraints=constraints
        )

        # POT already executed the code, check for errors
        if result.execution_result.error:
            # Handle execution errors
            pass

        return GeneratedCode(
            code=result.code,
            imports=result.imports,
            complexity=result.complexity,
            execution_result=result.execution_result
        )

    def cleanup(self):
        self.interpreter.cleanup()
```

## Performance Optimization

**Caching compiled programs**:
```python
import dspy
from functools import lru_cache

@lru_cache(maxsize=10)
def get_compiled_generator():
    generator = ProductionCodeGenerator()

    # Compile with optimizer (if trainset available)
    # optimizer = dspy.BootstrapFewShot()
    # compiled = optimizer.compile(generator, trainset=examples)

    return generator

# Reuse compiled version
generator = get_compiled_generator()
```

## Error Handling

```python
try:
    result = pot_module(spec=spec)
except TimeoutError:
    logger.error("POT execution timeout")
    # Retry with simpler spec or different approach
except MemoryError:
    logger.error("POT memory limit exceeded")
    # Reduce problem size
except Exception as e:
    logger.error(f"POT failed: {e}")
    # Fallback to regular code generation without execution
```
