# Iterative Development Workflow

## Phase 1: Requirement Gathering

**Goal**: Understand what Claude wants to build

**Questions Asked** (in order):
1. **Goal**: What do you want to achieve? (free text)
2. **Algorithmic Approach**: What's your approach? (e.g., "recursive search", "event-driven", etc)
3. **Technologies**: Which tech stack? (e.g., "FastAPI, PostgreSQL, Redis")
4. **Libraries**: Specific libraries and their features? (e.g., "FastAPI: dependency injection, async routes")
5. **Documentation** (optional): Any specific docs/links to reference?

**Output**: `Requirements` object with structured data

```python
@dataclass
class Requirements:
    goal: str
    approach: str
    technologies: List[str]
    libraries: Dict[str, List[str]]  # lib -> features
    docs: Optional[List[str]]
    context: Dict[str, Any]  # Additional context
```

## Phase 2: Planning

**Goal**: Decide architecture before coding

**Steps**:
1. **Module Decomposition**: Break goal into modules (max 100 lines each)
2. **Dependency Graph**: Determine module dependencies
3. **Test Planning**: Define unit/integration tests for each module
4. **Performance Criteria**: Set target metrics (time/space complexity)

**DSPy Signature**:
```python
class CodePlanner(dspy.Signature):
    requirements: str = dspy.InputField()

    modules: List[ModuleSpec] = dspy.OutputField()
    dependencies: Dict[str, List[str]] = dspy.OutputField()
    test_plan: List[TestSpec] = dspy.OutputField()
    performance_targets: Dict[str, str] = dspy.OutputField()
```

## Phase 3: Iterative Generation

**Goal**: Generate code that passes all tests

**The Loop**:
```
FOR each module:
    iteration = 0
    WHILE iteration < MAX_ITERATIONS:
        1. Generate code (DSPy ProgramOfThought)
        2. Generate tests (DSPy)
        3. Execute tests (Sandbox)
        4. Measure performance (Metrics)
        5. Calculate score (Scorer)

        IF score >= THRESHOLD:
            BREAK  # Success!
        ELSE:
            6. Analyze failures (Feedback)
            7. Refine code (DSPy Refine)
            iteration++

    IF score < THRESHOLD:
        MARK as partial_success
        LOG all attempts
```

**Scoring Function**:
```python
def calculate_score(results: TestResults, metrics: PerformanceMetrics) -> float:
    test_score = results.passed / results.total  # 0-1
    perf_score = evaluate_complexity(metrics)     # 0-1
    return 0.7 * test_score + 0.3 * perf_score
```

## Phase 4: Code Generation (DSPy POT)

**Using ProgramOfThought**:
```python
class CodeGenerator(dspy.Module):
    def __init__(self):
        self.generate = dspy.ProgramOfThought(
            signature="requirements, spec -> code: str, reasoning: str"
        )

    def forward(self, requirements, spec):
        # POT will generate code AND execute it to verify
        result = self.generate(
            requirements=requirements,
            spec=spec
        )
        return result.code
```

## Phase 5: Test Generation

**Automatic pytest Generation**:
```python
class TestGenerator(dspy.Signature):
    code: str = dspy.InputField()
    module_spec: str = dspy.InputField()

    test_code: str = dspy.OutputField(desc="Complete pytest test suite")
    test_cases: List[str] = dspy.OutputField(desc="List of test scenarios")
    fixtures: str = dspy.OutputField(desc="Pytest fixtures if needed")
```

**Test Types**:
- **Unit Tests**: Test individual functions
- **Integration Tests**: Test module interactions
- **Performance Tests**: Measure time/space complexity

## Phase 6: Execution & Measurement

**Sandbox Execution**:
1. Create isolated environment
2. Install dependencies
3. Run tests with timeout
4. Capture stdout/stderr
5. Measure execution time, memory usage

**Performance Metrics**:
```python
@dataclass
class PerformanceMetrics:
    execution_time: float
    memory_peak: float
    cpu_usage: float
    time_complexity: str  # O(n), O(log n), etc
    space_complexity: str
```

## Phase 7: Refinement (DSPy Refine)

**When tests fail or performance poor**:
```python
class CodeRefiner(dspy.Module):
    def __init__(self):
        self.refine = dspy.Refine(
            signature="code, errors, metrics -> improved_code: str",
            max_iters=5
        )

    def forward(self, code, errors, metrics):
        return self.refine(
            code=code,
            errors=format_errors(errors),
            metrics=format_metrics(metrics)
        )
```

**Refinement Strategies**:
- Fix syntax/runtime errors
- Optimize algorithms (reduce complexity)
- Add error handling
- Improve code clarity
- Add type hints

## Phase 8: Reporting

**Generate Comprehensive Report**:
```python
@dataclass
class DevelopmentReport:
    module_name: str
    iterations: int
    final_score: float

    # The code
    code: str
    tests: str

    # Performance
    metrics: PerformanceMetrics

    # Audit trail
    error_trail: List[ErrorRecord]
    attempt_history: List[Attempt]

    # Success status
    status: Literal["success", "partial", "failed"]
    notes: str
```

## Async Monitoring

**Claude can monitor progress**:
```python
# In orchestrator
async def generate_with_monitoring():
    async for event in generation_loop():
        await logger.log(event)

        # Claude can read logs
        if event.type == "iteration_complete":
            # Check if Claude sent interrupt signal
            if should_interrupt():
                await logger.log("Interrupted by Claude")
                break
```

**Log Levels**:
- `DEBUG`: Every code attempt
- `INFO`: Iteration summaries
- `WARN`: Test failures, performance issues
- `ERROR`: Critical failures
- `PROGRESS`: % completion updates

## Example Full Workflow

```
Claude: "Build a FastAPI endpoint that validates emails"

1. Requirements:
   Goal: Email validation API endpoint
   Approach: Regex-based validation with RFC 5322 compliance
   Tech: FastAPI, Pydantic
   Libraries: {FastAPI: [routes, dependency_injection], Pydantic: [EmailStr]}

2. Planning:
   Modules: [validator.py, routes.py, models.py]
   Tests: [test_validator.py, test_routes.py, test_integration.py]

3. Generation (validator.py):
   Iteration 1: Generated code, 2/5 tests pass
   Iteration 2: Fixed edge cases, 5/5 tests pass
   Score: 0.92 ✓

4. Generation (routes.py):
   Iteration 1: Generated code, 3/3 tests pass
   Score: 0.88 ✓

5. Integration:
   All modules pass integration tests
   Performance: 0.001s per validation

6. Report:
   Status: SUCCESS
   3 modules, 8 tests, all passing
   Performance: O(n) time, O(1) space

Return to Claude: Working MVP + full audit trail
```
