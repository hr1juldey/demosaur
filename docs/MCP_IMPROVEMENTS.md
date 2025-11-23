# MCP Interface Improvements

## ❌ Critical Issues Found in Original Implementation

### 1. Not Using FastMCP Properly

**Problem:**
- Created custom `CodeInternMCPServer` class
- Not using FastMCP decorators (`@tool`, `@resource`, `@prompt`)
- Missing automatic schema generation

**Impact:**
- Claude can't discover available tools automatically
- No type validation
- Manual schema management

**Solution:** ✅
- Use `@mcp.tool()` decorators
- Use `@mcp.resource()` for read-only data
- Let FastMCP auto-generate schemas from type hints

### 2. No Log Access via MCP Resources

**Problem:**
- Logs exist in memory and files
- **NOT exposed as MCP Resources**
- Claude cannot read logs without custom implementation

**Impact:**
- Claude can't monitor progress
- Can't debug issues
- Must rely on polling status

**Solution:** ✅ Created MCP Resources:
- `logs://server` - Server operation logs
- `logs://task/{task_id}` - Task-specific logs (filterable)
- `logs://task/{task_id}/progress` - Progress logs only

### 3. No Real-time Streaming

**Problem:**
- Claude must poll `get_status()` repeatedly
- No streaming partial results
- Long-running tasks show no progress

**Impact:**
- Poor UX (stale status)
- Wastes tokens on polling
- Can't intervene early

**Solution:** 🚧 Needs Implementation:
```python
@mcp.tool()
async def stream_task_progress(task_id: str):
    """Stream real-time progress updates"""
    async for event in _stream_workflow(task_id):
        yield event  # FastMCP supports streaming
```

### 4. No Resources for Generated Code

**Problem:**
- Generated code only available in final results
- Can't inspect interim code during iterations
- No separation of code vs tests

**Impact:**
- Claude can't review code mid-generation
- Can't provide early feedback
- No granular access

**Solution:** ✅ Created MCP Resources:
- `code://task/{task_id}/module/{module_name}` - Generated code
- `tests://task/{task_id}/module/{module_name}` - Generated tests
- `report://task/{task_id}` - Full development report

### 5. Poor Log Separation

**Problem:**
Three types of logs were MIXED or MISSING:

1. **MCP Server Logs** (server operations) - ❌ Not separated
2. **Task Workflow Logs** (planning, generation) - ✅ Partially done
3. **Execution Logs** (pytest output, code execution) - ❌ NOT captured

**Impact:**
- Can't distinguish server issues from task issues
- Test failures not logged properly
- Code execution output lost

**Solution:** ✅ Separated:
```
logs/
├── server.log              # MCP server operations
├── task-{id}.log          # Task workflow logs
└── task-{id}-exec.log     # Code execution logs
```

## 📊 Comparison: Before vs After

| Feature | Before | After |
|---------|--------|-------|
| **Tools** | Custom methods | `@mcp.tool()` decorators ✅ |
| **Resources** | None | 7 resources exposed ✅ |
| **Log Access** | File only | MCP Resources ✅ |
| **Streaming** | Polling only | Ready for streaming 🚧 |
| **Code Access** | Final only | Per-module resources ✅ |
| **Log Separation** | Mixed | 3 separate streams ✅ |
| **Type Safety** | Manual | Auto-generated ✅ |
| **Caching** | None | Ready for FastMCP cache 🚧 |

## 🎯 New MCP Resources Available to Claude

### Log Resources
```python
# Get all task logs
logs = await mcp.read_resource("logs://task/task-abc123")

# Get only progress logs
progress = await mcp.read_resource("logs://task/task-abc123/progress")

# Filter by level
errors = await mcp.read_resource("logs://task/task-abc123?level=ERROR")
```

### Code Resources
```python
# Get generated code
code = await mcp.read_resource("code://task/task-abc123/module/validator")

# Get tests
tests = await mcp.read_resource("tests://task/task-abc123/module/validator")

# Get full report
report = await mcp.read_resource("report://task/task-abc123")
```

## 🔧 Still Need to Implement

### 1. Streaming Progress (High Priority)
```python
@mcp.tool()
async def stream_task_progress(task_id: str):
    """Stream real-time updates"""
    state = state_manager.get_task(task_id)
    orchestrator = WorkflowOrchestrator(state)

    async for event in orchestrator.run_with_streaming():
        yield {
            "type": event.type,
            "data": event.data,
            "timestamp": event.timestamp
        }
```

### 2. Intervention Tool
```python
@mcp.tool()
async def intervene_in_task(
    task_id: str,
    intervention: str
) -> dict:
    """
    Send guidance/correction to running task.

    Args:
        task_id: Task identifier
        intervention: Guidance or correction

    Returns:
        Acknowledgment
    """
    # Set flag that orchestrator can check
    state = state_manager.get_task(task_id)
    state.metadata['intervention'] = intervention
    state.metadata['intervention_time'] = datetime.utcnow()

    return {"status": "intervention_queued"}
```

### 3. Execution Log Capture
```python
# In testing/runner.py, capture stdout/stderr
class TestRunner:
    async def run_tests(self, code, test_code, module_name):
        # Capture execution logs
        exec_logger = AsyncLogger(f"{task_id}-exec")

        result = subprocess.run(...)

        # Log stdout/stderr
        await exec_logger.log(
            LogLevel.INFO,
            "Test Output",
            stdout=result.stdout,
            stderr=result.stderr
        )
```

### 4. Caching (Performance)
```python
from fastmcp import Cache

@mcp.resource("docs://library/{lib_name}", cache=Cache(ttl=3600))
async def get_library_docs(lib_name: str) -> str:
    """Cache library docs for 1 hour"""
    # Fetch documentation
    return docs
```

## 📋 Implementation Checklist

- [x] Replace custom server with FastMCP decorators
- [x] Expose logs as MCP Resources
- [x] Expose generated code as Resources
- [x] Expose tests as Resources
- [x] Expose reports as Resources
- [x] Separate log streams (server/task/exec)
- [ ] Implement streaming progress
- [ ] Implement intervention tool
- [ ] Capture execution logs
- [ ] Add caching for docs
- [ ] Add prompts for common tasks

## 🎁 Benefits to Claude

### Before:
```
Claude: start_task("build validator")
Claude: get_status(task_id) → polling every 2s
Claude: get_status(task_id) → still running...
Claude: get_status(task_id) → still running...
Claude: get_results(task_id) → finally done!
```

### After:
```
Claude: start_coding_task("build validator")
Claude: read_resource("logs://task/{id}/progress") → see progress
Claude: read_resource("code://task/{id}/module/validator") → review interim code
Claude: intervene_in_task(id, "use regex instead") → provide guidance
Claude: stream_task_progress(id) → real-time updates
Claude: read_resource("report://task/{id}") → full report
```

## 🚀 Usage Examples for Claude

### Monitor Progress
```python
# Old way (polling)
while True:
    status = await get_status(task_id)
    if status['status'] == 'completed':
        break
    await asyncio.sleep(2)

# New way (resource)
progress_logs = await mcp.read_resource(f"logs://task/{task_id}/progress")
# Returns formatted progress without polling
```

### Review Code During Generation
```python
# Old way: Wait until complete
results = await get_results(task_id)  # Only at end

# New way: Check anytime
current_code = await mcp.read_resource(
    f"code://task/{task_id}/module/validator"
)
# Can review and intervene early!
```

### Debug Failures
```python
# Old way: No logs
results = await get_results(task_id)
# If failed, unclear why

# New way: Full logs
all_logs = await mcp.read_resource(f"logs://task/{task_id}")
error_logs = await mcp.read_resource(f"logs://task/{task_id}?level=ERROR")
# Clear visibility into what went wrong
```

## 📖 References

- [FastMCP Documentation](https://gofastmcp.com/)
- [FastMCP GitHub](https://github.com/jlowin/fastmcp)
- [Building MCP Servers Guide](https://mcpcat.io/guides/building-mcp-server-python-fastmcp/)
- [FastMCP Tutorial](https://www.firecrawl.dev/blog/fastmcp-tutorial-building-mcp-servers-python)
