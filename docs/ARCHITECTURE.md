# System Architecture

## Design Principles

- **SOLID**: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
- **Modularity**: Max 100 lines per file
- **Absolute Imports**: No relative imports
- **Async-First**: All I/O operations are async
- **Type Safety**: Full type hints throughout

## Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     MCP Server Layer                         │
│  (Handles Claude requests, manages sessions, routing)        │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                  Orchestrator Layer                          │
│  (Coordinates workflow, manages state, logging)              │
└───┬───────────┬───────────┬───────────┬────────────┬────────┘
    │           │           │           │            │
┌───▼────┐ ┌───▼────┐ ┌───▼────┐ ┌───▼─────┐ ┌────▼─────┐
│Require │ │  Code  │ │  Test  │ │ Execute │ │  Refine  │
│Gatherer│ │Generate│ │Generate│ │ Engine  │ │  Engine  │
└───┬────┘ └───┬────┘ └───┬────┘ └───┬─────┘ └────┬─────┘
    │          │          │          │            │
    └──────────┴──────────┴──────────┴────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                     DSPy Layer                               │
│  (Signatures, Modules: POT, CodeAct, ReAct, Refine)         │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                  Execution Layer                             │
│  (Deno sandbox, Python interpreter, Test runners)           │
└─────────────────────────────────────────────────────────────┘
```

## Module Breakdown

### 1. MCP Server Layer (`src/mcp/`)
- `server.py`: Main MCP server entry point
- `handlers.py`: Request/response handlers
- `session.py`: Session management

### 2. Orchestrator Layer (`src/orchestrator/`)
- `workflow.py`: Main workflow orchestrator
- `state.py`: State management
- `logger.py`: Async logging system

### 3. Requirement Gathering (`src/requirements/`)
- `gatherer.py`: Interactive Q&A
- `validator.py`: Requirement validation
- `schema.py`: Requirement data models

### 4. Code Generation (`src/codegen/`)
- `generator.py`: DSPy-based code generator
- `planner.py`: Module/architecture planner
- `signatures.py`: DSPy signatures for code gen

### 5. Test Generation (`src/testing/`)
- `generator.py`: Pytest test generator
- `runner.py`: Test execution engine
- `reporter.py`: Test result reporter

### 6. Execution Engine (`src/execution/`)
- `sandbox.py`: Deno/Python sandbox manager
- `interpreter.py`: Code interpreter wrapper
- `metrics.py`: Performance measurement

### 7. Refinement Engine (`src/refinement/`)
- `refiner.py`: Iterative code improvement
- `scorer.py`: Performance scoring
- `feedback.py`: Error analysis and feedback

### 8. Common Utilities (`src/common/`)
- `types.py`: Shared type definitions
- `config.py`: Configuration management
- `utils.py`: Utility functions

## Data Flow

1. **Claude Request** → MCP Server receives coding task
2. **Requirement Gathering** → Interactive Q&A with Claude
3. **Planning** → Generate module structure and test plan
4. **Generation Loop**:
   - Generate code (DSPy POT/CodeAct)
   - Generate tests (DSPy)
   - Execute tests (Sandbox)
   - Measure performance (Metrics)
   - Score quality (Scorer)
   - If score < threshold: Refine and repeat
5. **Report Generation** → Compile results, errors, metrics
6. **Response** → Return to Claude with working code + reports

## Async Architecture

```python
async def main_workflow():
    # All operations are async
    requirements = await gather_requirements()
    plan = await create_plan(requirements)

    # Parallel code generation for different modules
    tasks = [generate_module(mod) for mod in plan.modules]
    results = await asyncio.gather(*tasks)

    # Iterative refinement
    async for iteration in refine_loop(results):
        await log_progress(iteration)
        if should_interrupt():
            break
```

## Error Handling Strategy

- **Graceful Degradation**: Return partial results if possible
- **Retry Logic**: 3 attempts for transient failures
- **Error Trails**: Complete logs of all failures
- **Circuit Breaker**: Stop if error rate > 50%

## Performance Targets

- Requirement gathering: < 30s
- Code generation: < 2min per module
- Test execution: < 30s per test suite
- Full workflow: < 10min for typical task
- Memory usage: < 2GB
