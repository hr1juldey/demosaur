# FastMCP Integration Plan

**Status**: Research Complete - Planning Phase
**Source**: https://gofastmcp.com
**Purpose**: Evaluate FastMCP for Code Intern server and plan integration strategy

---

## Executive Summary

**Question**: Should we use FastMCP, pure FastAPI, or a hybrid approach?

**Answer**: **Hybrid Approach** - FastAPI for core API + FastMCP for MCP protocol compatibility

**Rationale**:
- FastAPI gives us full control over REST/WebSocket API for network access
- FastMCP provides standardized MCP protocol for Claude Desktop integration
- Best of both worlds: HTTP API + MCP compatibility

---

## FastMCP Core Concepts (Research Summary)

### 1. What is FastMCP?

**Source**: [FastMCP Overview](https://gofastmcp.com/)

FastMCP is a Python framework for building Model Context Protocol (MCP) servers and clients. It's the **actively maintained** successor to the official MCP SDK, with enterprise features and production-ready patterns.

#### Key Differences from Raw MCP:
- **Simpler**: Decorator-based API (like FastAPI)
- **Production-ready**: Auth (Google, GitHub, Azure), deployment tools, testing
- **Comprehensive**: Server composition, proxying, client libraries
- **FastMCP 2.0**: Current version with HTTP transport support

#### What It Does:
- **Resources**: Expose data for LLM context (read-only)
- **Tools**: Execute code, produce side effects (actions)
- **Prompts**: Reusable LLM interaction templates

---

### 2. Tools (MCP Actions)

**Source**: [FastMCP Tools](https://gofastmcp.com/servers/tools)

#### Decorator Pattern:
```python
from fastmcp import FastMCP

mcp = FastMCP(name="CodeIntern")

@mcp.tool
def start_coding_task(prompt: str) -> dict:
    """Start a new coding task"""
    return {"task_id": "task-123", "status": "started"}
```

#### Key Features:
- **Type annotations**: Auto-generate schemas
- **Docstrings**: Used as tool descriptions
- **Async support**: `async def` for I/O-bound operations
- **Return types**: String, dict, bytes, Pydantic models, ToolResult
- **Error handling**: Raise `ToolError` for failures
- **Metadata**: Tags, annotations (`readOnlyHint`, `destructiveHint`)

#### Advanced: ToolResult
```python
from fastmcp.tools.tool import ToolResult

@mcp.tool
def generate_code() -> ToolResult:
    return ToolResult(
        content="Summary text",
        structured_content={"code": "...", "tests": "..."},
        meta={"execution_time_ms": 3450}
    )
```

#### For Our Use Case:
- ✅ Perfect match for existing MCP tools
- ✅ Already have tools defined in `src/mcp/fastmcp_server.py`
- ✅ Can keep existing tool signatures

---

### 3. Resources (MCP Data Exposure)

**Source**: [FastMCP Resources](https://gofastmcp.com/servers/resources)

#### Basic Resources:
```python
@mcp.resource("logs://server")
def get_server_logs() -> str:
    """Server operation logs"""
    return read_logs("server.log")
```

#### Dynamic Resources (URI Templates):
```python
@mcp.resource("logs://task/{task_id}/workflow")
def get_task_workflow_logs(task_id: str) -> str:
    """Workflow logs for specific task"""
    return read_logs(f"task-{task_id}-workflow.log")
```

#### Advanced: Query Parameters (v2.13.0+):
```python
@mcp.resource("code://task/{task_id}/module/{module_name}{?format}")
def get_generated_code(
    task_id: str,
    module_name: str,
    format: str = "python"
) -> str:
    """Get generated code in specified format"""
    return get_code(task_id, module_name, format)
```

#### For Our Use Case:
- ✅ Already have resources defined
- ✅ URI templates match our design
- ✅ Can add query parameters for filtering

---

### 4. HTTP Transport (Remote Access)

**Source**: [FastMCP HTTP Deployment](https://gofastmcp.com/deployment/http)

#### Two Deployment Methods:

**Method 1: Direct HTTP Server (Built-in)**
```python
if __name__ == "__main__":
    mcp.run(transport="sse", port=9876, host="0.0.0.0")
```

**Method 2: ASGI with Uvicorn (Production)**
```python
# Export as ASGI app
app = mcp.get_asgi_app()

# Run with uvicorn
# uvicorn server:app --host 0.0.0.0 --port 9876
```

#### Transport Types:
- **stdio**: Local MCP clients (Claude Desktop)
- **sse**: HTTP Server-Sent Events (remote, web browsers)
- **Streamable HTTP**: Ecosystem standard for remote MCP (2025)

#### Network Configuration:
- **Default endpoint**: `/mcp/` (customizable)
- **Authentication**: Bearer tokens, JWT, OAuth (recommended for remote)
- **Health checks**: Can add custom routes
- **Middleware**: Starlette middleware support (CORS, logging)

#### For Our Use Case:
- ✅ ASGI method gives us Uvicorn control
- ✅ SSE transport for network access
- ⚠️ **Limitation**: SSE is one-way (server → client), not bi-directional like WebSocket

---

### 5. Hybrid Architecture (FastAPI + FastMCP)

**Source**: [FastMCP HTTP Deployment](https://gofastmcp.com/deployment/http)

FastMCP can be **mounted** under FastAPI using Starlette's `Mount()`:

```python
from fastapi import FastAPI
from starlette.routing import Mount
from src.mcp.fastmcp_server import mcp

app = FastAPI()

# Custom REST endpoints
@app.post("/tasks")
async def create_task(request: TaskRequest):
    """Custom FastAPI endpoint"""
    return {"task_id": "..."}

# Mount FastMCP under /mcp/
app.mount("/mcp", mcp.get_asgi_app())
```

#### Benefits:
- ✅ **Best of both worlds**: REST API + MCP protocol
- ✅ **Single port**: Both on 9876
- ✅ **Shared state**: Same app instance
- ✅ **Flexible routing**: `/mcp/*` for MCP, rest for FastAPI

---

## FastMCP vs FastAPI Comparison

| Feature | FastMCP | FastAPI | Hybrid |
|---------|---------|---------|--------|
| **REST API** | ❌ No | ✅ Yes | ✅ Yes |
| **WebSocket** | ❌ No (SSE only) | ✅ Yes | ✅ Yes |
| **MCP Protocol** | ✅ Yes | ❌ No | ✅ Yes |
| **Claude Desktop** | ✅ stdio | ❌ No | ✅ stdio |
| **Network Access** | ✅ SSE/HTTP | ✅ HTTP/WS | ✅ Both |
| **Bi-directional** | ❌ SSE one-way | ✅ WebSocket | ✅ WebSocket |
| **Background Tasks** | ❌ Limited | ✅ asyncio | ✅ asyncio |
| **Streaming** | ✅ SSE | ✅ SSE/WS | ✅ Both |

**Conclusion**: Hybrid approach wins for our requirements.

---

## Proposed Hybrid Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Laptop/Client (WiFi)                       │
│  ┌──────────────┐           ┌──────────────┐           │
│  │   Browser    │           │ Claude CLI   │           │
│  │ (WebSocket)  │           │   (stdio)    │           │
│  └──────┬───────┘           └──────┬───────┘           │
└─────────┼──────────────────────────┼───────────────────┘
          │                          │
          │ HTTP/WebSocket           │ stdio (JSON-RPC)
          │                          │
┌─────────▼──────────────────────────▼───────────────────┐
│            FastAPI Server (Port 9876)                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Custom REST Endpoints               │  │
│  │  POST /tasks      - Start task (REST)            │  │
│  │  GET /tasks/{id}  - Get status (REST)            │  │
│  │  WS /ws/{id}      - Progress stream (WebSocket)  │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │          FastMCP (Mounted at /mcp/)              │  │
│  │  Tools:    start_coding_task                     │  │
│  │            answer_requirement                     │  │
│  │            get_task_status                        │  │
│  │  Resources: logs://, code://, tests://           │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │           Shared Components                       │  │
│  │  - WebSocketManager                               │  │
│  │  - TaskManager (asyncio)                          │  │
│  │  - StateManager                                   │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│           Code Intern Workflow (Unchanged)              │
│  Requirements → Planning → Codegen → Testing → Refine   │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│              Ollama (localhost:11434)                   │
└─────────────────────────────────────────────────────────┘
```

---

## File Structure (Hybrid Approach)

### New Files:
```
src/api/
├── __init__.py
├── main.py                    # FastAPI app with /mcp mount (≤100 lines)
├── websocket_manager.py       # WebSocket connections (≤100 lines)
├── task_manager.py            # asyncio task tracking (≤100 lines)
├── endpoints/
│   ├── __init__.py
│   ├── tasks.py               # POST /tasks, GET /tasks/{id} (≤100 lines)
│   ├── websocket.py           # WS /ws/{task_id} (≤100 lines)
│   └── health.py              # GET /health (≤50 lines)
└── models/
    ├── __init__.py
    ├── requests.py            # Pydantic models (≤100 lines)
    └── responses.py           # Pydantic models (≤100 lines)
```

### Modified Files:
```
src/mcp/
├── fastmcp_server.py          # MODIFY: Export as ASGI app
└── server_runner.py           # MODIFY: Support both stdio and HTTP
```

### Keep Unchanged:
- All existing workflow modules
- All existing MCP tool definitions
- All existing resources

---

## Implementation Plan

### src/api/main.py (Hybrid Entry Point)

```python
"""
FastAPI + FastMCP Hybrid Server.

Provides:
- REST API for custom endpoints
- WebSocket for real-time updates
- MCP protocol at /mcp/ for Claude Desktop
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.routing import Mount
import dspy

from src.common.config import settings
from src.mcp.fastmcp_server import mcp
from src.api.websocket_manager import WebSocketManager
from src.api.task_manager import TaskManager
from src.api.endpoints import tasks, websocket, health


# Global managers
ws_manager = WebSocketManager()
task_manager = TaskManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown"""
    # Startup: Configure DSPy
    print("[Server] Configuring DSPy...")
    lm = dspy.LM(
        model=f"ollama_chat/{settings.model_name}",
        api_base=settings.ollama_base_url,
        api_key="",
        temperature=settings.temperature,
        max_tokens=settings.max_tokens
    )
    dspy.configure(lm=lm)
    print("[Server] DSPy configured")

    yield

    # Shutdown: Cleanup tasks
    print("[Server] Shutting down tasks...")
    await task_manager.shutdown_all()


# Create FastAPI app
app = FastAPI(
    title="Code Intern API",
    version="2.0.0",
    lifespan=lifespan
)

# Include custom endpoints
app.include_router(health.router, prefix="/health")
app.include_router(tasks.router, prefix="/tasks")
app.include_router(websocket.router)

# Mount FastMCP under /mcp
app.mount("/mcp", mcp.get_asgi_app())


# Make managers available to endpoints
app.state.ws_manager = ws_manager
app.state.task_manager = task_manager


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=9876,
        log_level="info"
    )
```

---

### API Endpoints Design

#### 1. POST /tasks (Custom FastAPI)
```python
# src/api/endpoints/tasks.py

from fastapi import APIRouter, Request
from src.api.models.requests import TaskRequest
from src.api.models.responses import TaskResponse

router = APIRouter()

@router.post("/", response_model=TaskResponse)
async def create_task(request: TaskRequest, app_request: Request):
    """Start a new coding task (REST)"""
    task_manager = app_request.app.state.task_manager
    ws_manager = app_request.app.state.ws_manager

    # Generate task ID
    task_id = generate_task_id()

    # Start background workflow
    workflow_coro = run_workflow(
        task_id=task_id,
        prompt=request.prompt,
        answers=request.answers,
        ws_manager=ws_manager
    )

    await task_manager.start_task(task_id, workflow_coro)

    return TaskResponse(
        task_id=task_id,
        status="started",
        websocket_url=f"ws://localhost:9876/ws/{task_id}"
    )
```

#### 2. GET /tasks/{task_id} (Custom FastAPI)
```python
@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str, app_request: Request):
    """Get current task status (REST)"""
    state = state_manager.get_task(task_id)
    if not state:
        raise HTTPException(404, "Task not found")

    return TaskStatusResponse(
        task_id=task_id,
        status=state.status.value,
        current_module=state.current_module,
        progress=calculate_progress(state)
    )
```

#### 3. WS /ws/{task_id} (Custom FastAPI - WebSocket)
```python
# src/api/endpoints/websocket.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

@router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """Real-time progress updates via WebSocket"""
    ws_manager = websocket.app.state.ws_manager

    await ws_manager.connect(task_id, websocket)

    try:
        while True:
            # Client can send interventions
            data = await websocket.receive_json()
            if data.get("type") == "INTERVENTION":
                await handle_intervention(task_id, data["guidance"])

    except WebSocketDisconnect:
        ws_manager.disconnect(task_id, websocket)
```

#### 4. MCP Tools (FastMCP at /mcp/)
```python
# src/mcp/fastmcp_server.py (EXISTING, MINIMAL CHANGES)

# These tools are accessible at:
# - stdio: for Claude Desktop
# - HTTP: POST /mcp/tools/call

@mcp.tool()
async def start_coding_task(prompt: str) -> dict:
    """Start coding task via MCP protocol"""
    # Use same task_manager as FastAPI
    task_id = generate_task_id()
    # ... existing implementation
    return {"task_id": task_id, "status": "started"}
```

---

## Access Patterns

### Pattern 1: Browser/Laptop (REST + WebSocket)
```bash
# Start task (REST)
curl -X POST http://192.168.1.4:9876/tasks \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Build validator", "answers": [...]}'

# Get status (REST)
curl http://192.168.1.4:9876/tasks/task-abc123

# Stream progress (WebSocket)
wscat -c ws://192.168.1.4:9876/ws/task-abc123
```

### Pattern 2: Claude Desktop (MCP stdio)
```bash
# stdio transport (configured in Claude Desktop)
python -m src.mcp.server_runner
```

### Pattern 3: Claude CLI (MCP HTTP)
```bash
# HTTP transport (for remote Claude Code)
# Connect to http://192.168.1.4:9876/mcp/
```

---

## Migration from Current Setup

### Step 1: Keep MCP Server Intact
- ✅ `src/mcp/fastmcp_server.py` stays mostly same
- ✅ Just export ASGI app: `app = mcp.get_asgi_app()`
- ✅ All tools and resources work unchanged

### Step 2: Add FastAPI Layer
- ✅ Create `src/api/main.py`
- ✅ Mount MCP at `/mcp`
- ✅ Add custom endpoints

### Step 3: Add WebSocket Support
- ✅ Create `WebSocketManager`
- ✅ Integrate with workflow
- ✅ Test real-time events

### Step 4: Shared State
- ✅ Use FastAPI `app.state` for managers
- ✅ Both MCP and REST use same `TaskManager`
- ✅ Single source of truth

---

## Advantages of Hybrid Approach

### ✅ Pros:

1. **MCP Compatibility**: Keep working with Claude Desktop (stdio)
2. **Network Access**: REST + WebSocket for laptop over WiFi
3. **Real-time Updates**: WebSocket bi-directional (better than SSE)
4. **Standardization**: MCP protocol for tool/resource definitions
5. **Flexibility**: Can use either interface
6. **Single Port**: Both on 9876, clean architecture
7. **Minimal Changes**: Existing MCP code mostly unchanged

### ⚠️ Considerations:

1. **Two interfaces**: Need to maintain both (but similar)
2. **State sharing**: Must ensure both use same managers
3. **Documentation**: Explain two access methods to users

---

## FastMCP-Specific Features We Can Use

### 1. Tool Annotations
```python
@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": True
    }
)
async def clean_dead_code(task_id: str) -> dict:
    """Remove dead code (DESTRUCTIVE)"""
    # Claude knows this modifies code
```

### 2. Resource Metadata
```python
@mcp.resource(
    "code://task/{task_id}/module/{module_name}",
    mime_type="text/x-python",
    tags={"generated", "code"}
)
def get_generated_code(task_id: str, module_name: str) -> str:
    """Get generated Python code"""
    return read_code(task_id, module_name)
```

### 3. Context Access
```python
from fastmcp import Context

@mcp.tool
async def tool_with_context(ctx: Context, param: str) -> dict:
    """Access MCP context info"""
    client_info = ctx.client_info
    # Can access request metadata
```

---

## Testing Strategy

### Test Both Interfaces:

```python
# tests/test_rest_api.py
from fastapi.testclient import TestClient
from src.api.main import app

def test_rest_create_task():
    client = TestClient(app)
    response = client.post("/tasks", json={"prompt": "test"})
    assert response.status_code == 200

# tests/test_mcp_tools.py
from src.mcp.fastmcp_server import mcp

async def test_mcp_tool():
    result = await mcp.call_tool("start_coding_task", {"prompt": "test"})
    assert "task_id" in result

# tests/test_websocket.py
def test_websocket_events():
    client = TestClient(app)
    with client.websocket_connect("/ws/test-task") as ws:
        data = ws.receive_json()
        assert data["type"] == "TASK_STARTED"
```

---

## Deployment Configuration

### Development (Local)
```bash
# Single command for both interfaces
uvicorn src.api.main:app --host 0.0.0.0 --port 9876 --reload
```

**Accessible**:
- REST: http://localhost:9876/tasks
- WebSocket: ws://localhost:9876/ws/{task_id}
- MCP: http://localhost:9876/mcp/
- Claude Desktop: stdio via `python -m src.mcp.server_runner`

### Production (WiFi Network)
```bash
# No reload, production mode
uvicorn src.api.main:app --host 0.0.0.0 --port 9876
```

**Accessible from laptop** (192.168.1.x network):
- REST: http://192.168.1.4:9876/tasks
- WebSocket: ws://192.168.1.4:9876/ws/{task_id}
- MCP: http://192.168.1.4:9876/mcp/

---

## Decision Matrix

| Requirement | Pure FastAPI | Pure FastMCP | Hybrid |
|-------------|--------------|--------------|--------|
| Network access (WiFi) | ✅ | ✅ SSE | ✅ |
| Bi-directional (WebSocket) | ✅ | ❌ | ✅ |
| Background tasks | ✅ asyncio | ⚠️ Limited | ✅ |
| MCP protocol | ❌ | ✅ | ✅ |
| Claude Desktop | ❌ | ✅ stdio | ✅ |
| REST API | ✅ | ❌ | ✅ |
| Real-time events | ✅ WS | ⚠️ SSE | ✅ WS |
| **TOTAL** | 5/7 | 4/7 | **7/7** ✅ |

**Winner**: **Hybrid Approach**

---

## Recommended Implementation

### Phase 1: Core Hybrid Setup
1. ✅ Create `src/api/main.py` with FastMCP mount
2. ✅ Add basic REST endpoints
3. ✅ Export MCP as ASGI app
4. ✅ Test both interfaces

### Phase 2: WebSocket Integration
1. ✅ Implement `WebSocketManager`
2. ✅ Add WebSocket endpoint
3. ✅ Integrate with workflow events
4. ✅ Test real-time streaming

### Phase 3: Task Management
1. ✅ Implement `TaskManager` with asyncio
2. ✅ Share state between REST and MCP
3. ✅ Add cancellation support
4. ✅ Test multi-task handling

### Phase 4: Network Deployment
1. ✅ Deploy on 0.0.0.0:9876
2. ✅ Test from laptop over WiFi
3. ✅ Test both REST and MCP access
4. ✅ Performance testing

---

## References

- [FastMCP Overview](https://gofastmcp.com/)
- [FastMCP Tools](https://gofastmcp.com/servers/tools)
- [FastMCP Resources](https://gofastmcp.com/servers/resources)
- [FastMCP HTTP Deployment](https://gofastmcp.com/deployment/http)
- [FastMCP Quickstart](https://gofastmcp.com/getting-started/quickstart)

---

## Conclusion

**Recommendation**: Implement **Hybrid FastAPI + FastMCP** architecture

**Benefits**:
- ✅ All requirements met (7/7)
- ✅ Minimal changes to existing code
- ✅ Best practices from both frameworks
- ✅ Network access + MCP compatibility
- ✅ Real-time WebSocket + MCP tools/resources

**Next Step**: Get user approval, then implement Phase 1
