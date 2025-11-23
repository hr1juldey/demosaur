# Implementation Plan: Remaining Features

## Research Summary

### Code Quality Tools Integration

#### Ruff (Linter)
- **Status**: No official Python API yet ([Issue #659](https://github.com/astral-sh/ruff/issues/659))
- **Solution**: Use CLI with `--output-format=json` via subprocess
- **Command**: `ruff check --output-format=json <file>`
- **Package**: `ruff-api` (experimental) exists but unstable

#### Pyright (Type Checker)
- **Pylance**: Proprietary, VSCode-only (since 2020.10.3)
- **Solution**: Use **Pyright** (open-source foundation)
- **Command**: `pyright --outputjson <file>`
- **Package**: `pyright` on PyPI

### References
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Ruff GitHub](https://github.com/astral-sh/ruff)
- [Pyright GitHub](https://github.com/microsoft/pyright)
- [Stack Overflow: Pyright Integration](https://stackoverflow.com/questions/76912452/)

---

## Implementation Tasks

### 1. Log Separation (HIGH Priority)

**Goal**: Separate 3 types of logs with dedicated MCP Resources

#### Architecture
```
logs/
├── server.log              # MCP server operations
├── task-{id}.log          # Workflow logs (planning, gen)
└── task-{id}-exec.log     # Code/test execution output
```

#### Files to Create
1. `src/orchestrator/log_manager.py` (≤100 lines)
   - `LogManager` class with 3 separate loggers
   - `get_server_logger()` singleton

2. `src/orchestrator/server_logger.py` (≤100 lines)
   - Global server logger
   - Tracks MCP operations

3. Update `src/mcp/resources.py`
   - Add `logs://server`
   - Add `logs://task/{id}/workflow`
   - Add `logs://task/{id}/execution`

#### Dependencies
- Modify `WorkflowOrchestrator` to use `LogManager`
- Update `TestRunner` to log to execution logger

---

### 2. Execution Log Capture (HIGH Priority)

**Goal**: Capture pytest stdout/stderr and code execution logs

#### Files to Create
1. `src/execution/log_capture.py` (≤100 lines)
   - `ExecutionLogCapture` class
   - Captures subprocess stdout/stderr
   - Writes to execution logger

2. Update `src/testing/runner.py`
   - Use `ExecutionLogCapture`
   - Log all test output

#### Example Implementation
```python
class ExecutionLogCapture:
    def __init__(self, exec_logger: AsyncLogger):
        self.logger = exec_logger

    async def run_with_capture(self, cmd: list) -> subprocess.CompletedProcess:
        """Run command and log output"""
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await proc.communicate()

        await self.logger.log(
            LogLevel.INFO,
            "Command executed",
            command=" ".join(cmd),
            stdout=stdout.decode(),
            stderr=stderr.decode(),
            returncode=proc.returncode
        )

        return proc
```

---

### 3. Streaming Progress (HIGH Priority)

**Goal**: Real-time progress updates instead of polling

#### Files to Create
1. `src/orchestrator/events.py` (≤100 lines)
   - `WorkflowEvent` dataclass
   - Event types: `STARTED`, `PROGRESS`, `MODULE_START`, etc.

2. `src/orchestrator/streaming.py` (≤100 lines)
   - `StreamingWorkflowOrchestrator` extends `WorkflowOrchestrator`
   - Yields events during execution

3. Update `src/mcp/fastmcp_server.py`
   - Add `stream_task_progress(task_id)` tool

#### Example Event Stream
```python
@dataclass
class WorkflowEvent:
    type: str  # STARTED, PROGRESS, MODULE_START, etc.
    task_id: str
    timestamp: float
    data: Dict[str, Any]

async def stream_workflow():
    yield WorkflowEvent("STARTED", task_id, time(), {})
    yield WorkflowEvent("PLANNING", task_id, time(), {"modules": 3})
    yield WorkflowEvent("MODULE_START", task_id, time(), {"module": "validator.py"})
    yield WorkflowEvent("ITERATION", task_id, time(), {"iter": 1, "score": 0.75})
```

#### MCP Tool
```python
@mcp.tool()
async def stream_task_progress(task_id: str):
    """Stream real-time progress updates"""
    async for event in orchestrator.run_with_streaming():
        yield event.to_dict()
```

---

### 4. Code Quality Tools Integration (MEDIUM Priority)

**Goal**: Add Ruff and Pyright checking to code generation

#### Files to Create
1. `src/codegen/quality_checker.py` (≤100 lines)
   - `QualityChecker` class
   - `check_with_ruff()` - subprocess to ruff
   - `check_with_pyright()` - subprocess to pyright
   - Parse JSON output

2. `src/codegen/quality_fixer.py` (≤100 lines)
   - `QualityFixer` class
   - Auto-fix ruff violations
   - Report pyright errors to refiner

3. Update `src/codegen/generator.py`
   - Run quality checks after generation
   - Auto-fix if possible
   - Add errors to refinement feedback

#### Example Implementation
```python
class QualityChecker:
    async def check_with_ruff(self, code: str, filepath: str) -> List[Dict]:
        """Run ruff and return violations"""
        with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            result = subprocess.run(
                ['ruff', 'check', '--output-format=json', temp_path],
                capture_output=True,
                text=True
            )

            violations = json.loads(result.stdout)
            return violations

        finally:
            os.unlink(temp_path)

    async def check_with_pyright(self, code: str) -> List[Dict]:
        """Run pyright and return type errors"""
        # Similar implementation
```

---

### 5. Intervention Tool (MEDIUM Priority)

**Goal**: Let Claude send corrections/guidance mid-execution

#### Files to Create
1. `src/orchestrator/intervention.py` (≤100 lines)
   - `InterventionManager` class
   - Check for pending interventions
   - Apply to refinement process

2. Update `src/mcp/fastmcp_server.py`
   - Add `intervene_in_task(task_id, intervention)` tool

3. Update `src/orchestrator/workflow.py`
   - Check for interventions in loop
   - Pass to refiner

#### Example Implementation
```python
@mcp.tool()
async def intervene_in_task(task_id: str, guidance: str) -> dict:
    """
    Send guidance to a running task.

    Args:
        task_id: Task identifier
        guidance: Correction or suggestion

    Returns:
        Acknowledgment
    """
    state = state_manager.get_task(task_id)
    if not state:
        return {"error": "Task not found"}

    # Store intervention
    intervention_manager.add_intervention(task_id, guidance)

    return {
        "status": "intervention_queued",
        "message": "Guidance will be applied in next refinement"
    }
```

---

## Implementation Order

### Phase 1: Logging (Week 1)
1. ✅ Create `log_manager.py`
2. ✅ Create `server_logger.py`
3. ✅ Create `log_capture.py`
4. ✅ Update `resources.py` with new log resources
5. ✅ Update `WorkflowOrchestrator` to use `LogManager`
6. ✅ Update `TestRunner` to capture logs

### Phase 2: Streaming (Week 1)
1. ✅ Create `events.py`
2. ✅ Create `streaming.py`
3. ✅ Add `stream_task_progress` tool
4. ✅ Test streaming with demo

### Phase 3: Quality Tools (Week 2)
1. ✅ Add `pyright` to requirements.txt
2. ✅ Create `quality_checker.py`
3. ✅ Create `quality_fixer.py`
4. ✅ Integrate into `CodeGenerator`
5. ✅ Test with sample code

### Phase 4: Intervention (Week 2)
1. ✅ Create `intervention.py`
2. ✅ Add `intervene_in_task` tool
3. ✅ Update workflow to check interventions
4. ✅ Test intervention flow

---

## Testing Strategy

### Unit Tests
- `test_log_manager.py` - Test log separation
- `test_streaming.py` - Test event stream
- `test_quality_checker.py` - Test ruff/pyright
- `test_intervention.py` - Test intervention flow

### Integration Tests
- `test_full_workflow_with_logs.py` - End-to-end with log separation
- `test_streaming_workflow.py` - Streaming integration
- `test_quality_integration.py` - Quality checks in workflow

---

## File Size Compliance

All files must be ≤100 lines. Split if needed:

**Good:**
- `log_manager.py` (80 lines)
- `server_logger.py` (60 lines)

**Bad:**
- `logging_system.py` (200 lines) ❌

---

## Dependencies to Add

```txt
# requirements.txt additions
pyright>=1.1.0  # Type checking
```

Note: `ruff` already in requirements.txt

---

## MCP Resources After Implementation

```python
# Log Resources
logs://server                      # Server operations
logs://task/{id}/workflow         # Planning, generation
logs://task/{id}/execution        # Test/code execution

# Code Resources (existing)
code://task/{id}/module/{name}
tests://task/{id}/module/{name}
report://task/{id}

# New Tools
stream_task_progress(task_id)     # Real-time updates
intervene_in_task(task_id, guidance)  # Send corrections
```

---

## Success Criteria

- ✅ 3 separate log files per task
- ✅ MCP Resources for each log type
- ✅ Streaming events (no polling)
- ✅ Pytest output captured
- ✅ Ruff violations detected and fixed
- ✅ Pyright errors reported
- ✅ Claude can intervene mid-execution
- ✅ All files ≤100 lines
- ✅ Full test coverage
