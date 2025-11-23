# Analysis: MCP Interface Improvements & Log Separation

## Your Questions Answered

### Q1: Places where we can improve the MCP interface to help Claude better?

**Answer:** We found **5 CRITICAL gaps**:

---

## 1. ❌ NOT Using FastMCP Properly

### What We Did Wrong:
```python
# OLD (src/mcp/server.py) - Custom class, no decorators
class CodeInternMCPServer:
    async def start_task(self, initial_prompt: str):
        # Manual implementation
```

### What We Should Do:
```python
# NEW (src/mcp/fastmcp_server.py) - FastMCP decorators
from fastmcp import FastMCP

mcp = FastMCP("code-intern")

@mcp.tool()
async def start_coding_task(initial_prompt: str) -> dict:
    """Start a new coding task"""  # Auto-generates schema!
```

**Benefits:**
- ✅ Automatic schema generation from docstrings + type hints
- ✅ Automatic validation
- ✅ Claude can discover tools automatically
- ✅ Less boilerplate code

---

## 2. ❌ NO Log Access via MCP Resources

### What Was Missing:
- Logs existed in files and memory
- **NOT exposed as MCP Resources**
- Claude couldn't read logs without file access

### What We Added: ✅

```python
@mcp.resource("logs://task/{task_id}")
async def get_task_logs(task_id: str, level: Optional[str] = None) -> str:
    """Get logs for a specific coding task"""
    # Returns formatted logs Claude can read!

@mcp.resource("logs://task/{task_id}/progress")
async def get_task_progress_logs(task_id: str) -> str:
    """Get only PROGRESS level logs"""
```

**Now Claude Can:**
```python
# Read all task logs
logs = await mcp.read_resource("logs://task/task-abc123")

# Filter by level
errors = await mcp.read_resource("logs://task/task-abc123?level=ERROR")

# Just progress
progress = await mcp.read_resource("logs://task/task-abc123/progress")
```

---

## 3. ❌ NO Streaming (Only Polling)

### What Was Missing:
```python
# OLD: Claude must poll repeatedly (wasteful)
while True:
    status = await get_status(task_id)
    if status['status'] == 'completed':
        break
    await asyncio.sleep(2)  # Waste tokens polling!
```

### What We Need: 🚧 (Not yet implemented)

```python
# NEW: Stream real-time updates
@mcp.tool()
async def stream_task_progress(task_id: str):
    """Stream real-time progress updates"""
    async for event in _stream_workflow(task_id):
        yield event  # FastMCP supports streaming!
```

**Benefits:**
- ✅ Real-time updates without polling
- ✅ Saves tokens (no repeated status calls)
- ✅ Claude can see progress live
- ✅ Can intervene mid-execution

---

## 4. ❌ NO Resources for Generated Code

### What Was Missing:
- Generated code only in final `get_results()`
- No way to inspect interim code
- No separation of code vs tests

### What We Added: ✅

```python
@mcp.resource("code://task/{task_id}/module/{module_name}")
async def get_generated_code(task_id: str, module_name: str) -> str:
    """Get generated code for a specific module"""

@mcp.resource("tests://task/{task_id}/module/{module_name}")
async def get_generated_tests(task_id: str, module_name: str) -> str:
    """Get generated tests for a specific module"""

@mcp.resource("report://task/{task_id}")
async def get_task_report(task_id: str) -> str:
    """Get comprehensive development report"""
```

**Now Claude Can:**
```python
# Review code during generation (iteration 3 of 10)
code = await mcp.read_resource("code://task/abc/module/validator")

# Check tests separately
tests = await mcp.read_resource("tests://task/abc/module/validator")

# Get full report
report = await mcp.read_resource("report://task/abc")
```

---

## 5. ❌ NO Proper Log Separation

### The Problem:
We mixed or lost **three types of logs**:

1. **MCP Server Logs** (server operations like starting/stopping)
2. **Task Workflow Logs** (planning, code gen, testing, refining)
3. **Execution Logs** (pytest output, code execution stdout/stderr)

---

### Q2: Did we create avenues to read MCP server logs and generated code's logs separately?

**Answer:** ❌ NO, we did NOT separate them properly. Here's what we're missing:

---

## Missing Log Separation Implementation

### What We Have Now:
```python
# src/orchestrator/logger.py
class AsyncLogger:
    def __init__(self, task_id: str):
        self.log_file = log_dir / f"{task_id}.log"  # ONE file per task
```

**Problem:** Everything goes into one file:
- MCP server operations
- Workflow logs (planning, generation)
- Test execution output
- Code execution errors

**Result:** Hard to debug! All logs mixed together.

---

### What We SHOULD Have:

```
logs/
├── server.log                  # MCP server operations
├── task-abc123.log            # Workflow logs (planning, gen)
└── task-abc123-execution.log  # Code/test execution output
```

### Implementation Needed:

```python
# src/orchestrator/logger.py - ADD THESE
class LogManager:
    """Manages separate log streams"""

    def __init__(self, task_id: str):
        self.task_id = task_id

        # Three separate loggers
        self.workflow_logger = AsyncLogger(
            f"{task_id}",
            log_file=f"logs/task-{task_id}.log"
        )

        self.execution_logger = AsyncLogger(
            f"{task_id}-exec",
            log_file=f"logs/task-{task_id}-execution.log"
        )

        # Server logger (singleton)
        self.server_logger = get_server_logger()


# Expose via MCP Resources
@mcp.resource("logs://server")
async def get_server_logs() -> str:
    """MCP server operation logs ONLY"""
    # Server start, stop, errors, etc.

@mcp.resource("logs://task/{task_id}/workflow")
async def get_workflow_logs(task_id: str) -> str:
    """Task workflow logs ONLY"""
    # Planning, code generation, test generation

@mcp.resource("logs://task/{task_id}/execution")
async def get_execution_logs(task_id: str) -> str:
    """Code/test execution logs ONLY"""
    # Pytest output, code stdout/stderr, errors
```

---

## Summary: What's Missing vs What We Added

| Feature | Status | Impact on Claude |
|---------|--------|------------------|
| **FastMCP Decorators** | ✅ Added | Auto-schema, better discovery |
| **Log Resources** | ✅ Added | Can read logs via MCP |
| **Code Resources** | ✅ Added | Can inspect code anytime |
| **Test Resources** | ✅ Added | Can review tests separately |
| **Report Resource** | ✅ Added | Full development report |
| **Streaming Progress** | ❌ Missing | Still must poll status |
| **Intervention Tool** | ❌ Missing | Can't guide mid-execution |
| **Separate Log Streams** | ❌ Missing | Logs are mixed |
| **Execution Log Capture** | ❌ Missing | Pytest output not logged |

---

## What Claude Gets Now vs Before

### Before:
```
Claude: start_task("build validator")
Claude: get_status(task_id)  # Poll every 2s
Claude: get_status(task_id)  # Still running...
Claude: get_status(task_id)  # Still running...
Claude: get_results(task_id) # Finally! But what happened?
```

**Problems:**
- ❌ No logs visible
- ❌ No interim code access
- ❌ No progress details
- ❌ Can't intervene
- ❌ Wastes tokens polling

### After (With Our Improvements):
```
Claude: start_coding_task("build validator")
Claude: read_resource("logs://task/abc/progress")  # See progress
Claude: read_resource("code://task/abc/module/validator")  # Review code
Claude: read_resource("logs://task/abc/workflow")  # Debug if needed
Claude: read_resource("report://task/abc")  # Full report
```

**Benefits:**
- ✅ Full log visibility
- ✅ Inspect code anytime
- ✅ Granular resources
- ✅ Better debugging
- ✅ No wasted tokens

---

## Files Created/Modified

### New Files: ✅
1. **src/mcp/fastmcp_server.py** - Proper FastMCP implementation
2. **src/mcp/resources.py** - MCP Resources for logs/code/tests
3. **src/mcp/helpers.py** - Workflow helpers
4. **docs/MCP_IMPROVEMENTS.md** - Detailed improvement guide

### Still Need to Create: 🚧
1. **src/orchestrator/log_manager.py** - Separate log streams
2. **src/execution/capture.py** - Capture execution logs
3. **src/mcp/streaming.py** - Streaming implementation
4. **src/mcp/intervention.py** - Intervention tools

---

## Next Steps (Priority Order)

1. **HIGH: Implement Log Separation** 🔴
   - Create `LogManager` with 3 separate streams
   - Capture execution logs (pytest stdout/stderr)
   - Expose via separate resources

2. **HIGH: Implement Streaming** 🔴
   - Add `stream_task_progress()` tool
   - Modify orchestrator to yield events
   - Real-time updates for Claude

3. **MEDIUM: Add Intervention Tool** 🟡
   - Let Claude send corrections mid-execution
   - Orchestrator checks for interventions
   - Can guide refinement

4. **LOW: Add Caching** 🟢
   - Cache documentation fetches
   - Cache library analysis
   - Performance boost

---

## References

- [FastMCP Documentation](https://gofastmcp.com/)
- [FastMCP GitHub](https://github.com/jlowin/fastmcp)
- [Building MCP Servers](https://mcpcat.io/guides/building-mcp-server-python-fastmcp/)
- [FastMCP Tutorial](https://www.firecrawl.dev/blog/fastmcp-tutorial-building-mcp-servers-python)
- [MCP Best Practices](https://composio.dev/blog/how-to-effectively-use-prompts-resources-and-tools-in-mcp)
