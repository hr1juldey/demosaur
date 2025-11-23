# MCP Server API Design

## MCP Protocol Overview

The server exposes tools that Claude can call via the Model Context Protocol.

## Core Tools

### 1. `code_intern_start_task`

**Description**: Start a new coding task with the intern

**Input**:
```json
{
  "task_id": "unique-task-id",
  "initial_prompt": "Build a REST API for user management"
}
```

**Output**:
```json
{
  "status": "started",
  "task_id": "unique-task-id",
  "next_step": "requirements_gathering",
  "question": "What do you want to achieve with this API?"
}
```

### 2. `code_intern_answer`

**Description**: Answer the intern's questions

**Input**:
```json
{
  "task_id": "unique-task-id",
  "answer": "Create CRUD endpoints for users with authentication"
}
```

**Output**:
```json
{
  "status": "in_progress",
  "next_question": "What's your algorithmic approach?",
  "progress": 20
}
```

### 3. `code_intern_get_status`

**Description**: Check progress of ongoing task

**Input**:
```json
{
  "task_id": "unique-task-id"
}
```

**Output**:
```json
{
  "status": "generating",
  "current_phase": "code_generation",
  "current_module": "auth.py",
  "iteration": 2,
  "score": 0.75,
  "progress": 60,
  "logs": ["...", "..."]
}
```

### 4. `code_intern_get_logs`

**Description**: Get recent logs from the intern

**Input**:
```json
{
  "task_id": "unique-task-id",
  "level": "INFO",
  "last_n": 50
}
```

**Output**:
```json
{
  "logs": [
    {"time": "...", "level": "INFO", "message": "..."},
    {"time": "...", "level": "WARN", "message": "Test failed: ..."}
  ]
}
```

### 5. `code_intern_intervene`

**Description**: Send correction/guidance to intern

**Input**:
```json
{
  "task_id": "unique-task-id",
  "intervention": "You're using recursion incorrectly, try iteration instead"
}
```

**Output**:
```json
{
  "status": "acknowledged",
  "action": "refining_with_guidance"
}
```

### 6. `code_intern_stop_task`

**Description**: Stop/cancel a running task

**Input**:
```json
{
  "task_id": "unique-task-id",
  "reason": "Taking too long"
}
```

**Output**:
```json
{
  "status": "stopped",
  "partial_results": {...}
}
```

### 7. `code_intern_get_results`

**Description**: Get final results when complete

**Input**:
```json
{
  "task_id": "unique-task-id"
}
```

**Output**:
```json
{
  "status": "completed",
  "modules": [
    {
      "name": "auth.py",
      "code": "...",
      "tests": "...",
      "score": 0.92,
      "metrics": {...}
    }
  ],
  "error_trail": [...],
  "performance_report": {...},
  "total_iterations": 12,
  "success_rate": 0.85
}
```

## Workflow Example

```python
# Claude starts task
response = await mcp.call_tool("code_intern_start_task", {
    "task_id": "task-123",
    "initial_prompt": "Build email validator"
})

# Interactive Q&A
while response["status"] == "in_progress":
    answer = get_answer_from_context()
    response = await mcp.call_tool("code_intern_answer", {
        "task_id": "task-123",
        "answer": answer
    })

# Monitor progress
async def monitor():
    while True:
        status = await mcp.call_tool("code_intern_get_status", {
            "task_id": "task-123"
        })

        if status["status"] == "completed":
            break

        # Check logs
        if status["score"] < 0.5:
            logs = await mcp.call_tool("code_intern_get_logs", {
                "task_id": "task-123",
                "level": "ERROR"
            })
            # Maybe intervene
            await mcp.call_tool("code_intern_intervene", {
                "task_id": "task-123",
                "intervention": "Fix the import error"
            })

        await asyncio.sleep(10)

# Get results
results = await mcp.call_tool("code_intern_get_results", {
    "task_id": "task-123"
})
```

## State Machine

```
START
  ↓
GATHERING_REQUIREMENTS
  ↓ (all questions answered)
PLANNING
  ↓
GENERATING (per module)
  ↓ (tests pass)
COMPLETED
  ↓
RESULTS_AVAILABLE

[Any state] → STOPPED (on cancel)
[Any state] → FAILED (on critical error)
```

## Error Responses

```json
{
  "error": {
    "code": "TASK_NOT_FOUND",
    "message": "Task task-123 not found",
    "details": {...}
  }
}
```

**Error Codes**:
- `TASK_NOT_FOUND`
- `INVALID_STATE` (e.g., answering when not in Q&A phase)
- `EXECUTION_FAILED`
- `TIMEOUT`
- `RESOURCE_LIMIT`

## Resource Limits

- **Max concurrent tasks**: 3
- **Max task duration**: 30 minutes
- **Max iterations per module**: 10
- **Max memory per sandbox**: 1GB
- **Max execution time per test**: 30s
