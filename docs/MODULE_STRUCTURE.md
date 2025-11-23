# Module Structure & File Organization

## Directory Layout

```
demo/
├── docs/                          # Documentation
│   ├── PROJECT_OVERVIEW.md
│   ├── ARCHITECTURE.md
│   ├── WORKFLOW.md
│   ├── API_DESIGN.md
│   └── MODULE_STRUCTURE.md
│
├── src/                           # Source code
│   ├── __init__.py
│   │
│   ├── mcp/                       # MCP Server Layer
│   │   ├── __init__.py
│   │   ├── server.py              # Main MCP server
│   │   ├── handlers.py            # Tool handlers
│   │   └── session.py             # Session management
│   │
│   ├── orchestrator/              # Orchestration Layer
│   │   ├── __init__.py
│   │   ├── workflow.py            # Main workflow orchestrator
│   │   ├── state.py               # State management
│   │   └── logger.py              # Async logging
│   │
│   ├── requirements/              # Requirement Gathering
│   │   ├── __init__.py
│   │   ├── gatherer.py            # Interactive Q&A
│   │   ├── validator.py           # Validation logic
│   │   └── schema.py              # Data models
│   │
│   ├── planning/                  # Code Planning
│   │   ├── __init__.py
│   │   ├── planner.py             # Module/test planner
│   │   ├── signatures.py          # DSPy signatures
│   │   └── models.py              # Plan data models
│   │
│   ├── codegen/                   # Code Generation
│   │   ├── __init__.py
│   │   ├── generator.py           # DSPy code generator
│   │   ├── pot_module.py          # ProgramOfThought wrapper
│   │   └── signatures.py          # DSPy signatures
│   │
│   ├── testing/                   # Test Generation & Execution
│   │   ├── __init__.py
│   │   ├── generator.py           # Test generator
│   │   ├── runner.py              # Test executor
│   │   └── reporter.py            # Result reporter
│   │
│   ├── execution/                 # Code Execution
│   │   ├── __init__.py
│   │   ├── sandbox.py             # Sandbox manager
│   │   ├── interpreter.py         # Python interpreter
│   │   └── metrics.py             # Performance metrics
│   │
│   ├── refinement/                # Code Refinement
│   │   ├── __init__.py
│   │   ├── refiner.py             # Iterative refiner
│   │   ├── scorer.py              # Quality scorer
│   │   └── feedback.py            # Error analyzer
│   │
│   └── common/                    # Shared Utilities
│       ├── __init__.py
│       ├── types.py               # Type definitions
│       ├── config.py              # Configuration
│       └── utils.py               # Utility functions
│
├── tests/                         # Test suite
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── pyproject.toml                 # Project config
├── requirements.txt               # Dependencies
└── main.py                        # Entry point
```

## Import Strategy

**Always use absolute imports from project root**:

```python
# ✅ CORRECT
from src.common.types import Requirements
from src.codegen.generator import CodeGenerator
from src.execution.sandbox import Sandbox

# ❌ WRONG
from ..common.types import Requirements
from .generator import CodeGenerator
```

## File Size Constraint

**Maximum 100 lines per file** including:
- Imports
- Class/function definitions
- Docstrings
- Comments

**Splitting strategies**:
1. **By responsibility**: One class per file
2. **By feature**: Group related functions
3. **By abstraction**: Interfaces separate from implementations

## Dependency Graph

```
mcp.server
    ↓
orchestrator.workflow
    ↓
    ├─→ requirements.gatherer
    ├─→ planning.planner
    ├─→ codegen.generator
    │       ↓
    │   codegen.pot_module
    │       ↓
    │   execution.interpreter
    ├─→ testing.generator
    │       ↓
    │   testing.runner
    │       ↓
    │   execution.sandbox
    └─→ refinement.refiner
            ↓
        refinement.scorer
            ↓
        execution.metrics

All modules can use:
    - common.types
    - common.config
    - common.utils
```

## Module Responsibilities (SRP)

### MCP Layer
- `server.py`: MCP protocol handling ONLY
- `handlers.py`: Route requests to orchestrator ONLY
- `session.py`: Manage task sessions ONLY

### Orchestrator
- `workflow.py`: Coordinate phases ONLY
- `state.py`: Persist/retrieve state ONLY
- `logger.py`: Handle logging ONLY

### Requirements
- `gatherer.py`: Ask questions ONLY
- `validator.py`: Validate answers ONLY
- `schema.py`: Define data structures ONLY

### Planning
- `planner.py`: Generate plans ONLY
- `signatures.py`: DSPy signatures ONLY
- `models.py`: Plan data models ONLY

### Codegen
- `generator.py`: Orchestrate generation ONLY
- `pot_module.py`: Wrap DSPy POT ONLY
- `signatures.py`: DSPy signatures ONLY

### Testing
- `generator.py`: Generate tests ONLY
- `runner.py`: Execute tests ONLY
- `reporter.py`: Format results ONLY

### Execution
- `sandbox.py`: Manage sandbox ONLY
- `interpreter.py`: Execute code ONLY
- `metrics.py`: Measure performance ONLY

### Refinement
- `refiner.py`: Coordinate refinement ONLY
- `scorer.py`: Calculate scores ONLY
- `feedback.py`: Analyze errors ONLY

## Type Definitions

**All shared types in `common/types.py`**:
```python
from dataclasses import dataclass
from typing import List, Dict, Optional, Literal

@dataclass
class Requirements:
    goal: str
    approach: str
    technologies: List[str]
    libraries: Dict[str, List[str]]
    docs: Optional[List[str]] = None

@dataclass
class ModuleSpec:
    name: str
    purpose: str
    dependencies: List[str]
    max_lines: int = 100

# ... etc
```

## Configuration Management

**All config in `common/config.py`**:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # DSPy/LLM
    ollama_base_url: str = "http://localhost:11434"
    model_name: str = "mistral:7b"

    # Execution
    max_iterations: int = 10
    test_timeout: int = 30
    sandbox_memory_limit: int = 1024  # MB

    # MCP
    max_concurrent_tasks: int = 3
    task_timeout: int = 1800  # 30 min

    # Thresholds
    min_score_threshold: float = 0.8
    min_test_pass_rate: float = 0.9

settings = Settings()
```

## Async Patterns

**All I/O operations are async**:
```python
# File I/O
async def read_file(path: str) -> str:
    async with aiofiles.open(path) as f:
        return await f.read()

# Subprocess
async def run_tests(code: str) -> TestResults:
    proc = await asyncio.create_subprocess_exec(...)
    stdout, stderr = await proc.communicate()
    return parse_results(stdout)

# Concurrent operations
async def generate_all_modules(specs: List[ModuleSpec]):
    tasks = [generate_module(spec) for spec in specs]
    return await asyncio.gather(*tasks)
```

## Testing Strategy

- **Unit tests**: Test each module in isolation
- **Integration tests**: Test module interactions
- **No E2E tests**: Leave to Claude

**Example**:
```
tests/
├── unit/
│   ├── test_gatherer.py
│   ├── test_generator.py
│   └── test_scorer.py
├── integration/
│   ├── test_workflow.py
│   └── test_full_cycle.py
└── fixtures/
    ├── sample_requirements.json
    └── sample_code.py
```
