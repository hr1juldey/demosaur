# FastAPI Integration Plan

**Status**: Research Complete - Planning Phase
**Source**: https://fastapi.tiangolo.com
**Purpose**: Plan transformation of Code Intern from stdio MCP to FastAPI + WebSocket backend

---

## Executive Summary

**Goal**: Replace stdio-based MCP server with FastAPI backend for:
- Network access over WiFi from laptop
- Real-time progress streaming via WebSockets
- Better background task management for long-running code generation
- Production-ready HTTP API

**Architecture**: FastAPI (REST + WebSocket) → Code Intern Workflow → Ollama

---

## FastAPI Core Concepts (Research Summary)

### 1. Background Tasks

**Source**: [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)

#### What We Learned:
- `BackgroundTasks` is for **lightweight, fire-and-forget** operations
- Executes **after response** is returned
- **NOT suitable** for our use case (multi-minute code generation)
- Quote: "If you need to perform heavy background computation...you might benefit from using other bigger tools like Celery"

#### For Our Use Case:
- ❌ **Don't use**: `BackgroundTasks` (too simple)
- ❌ **Don't use**: Celery (overkill, requires Redis/RabbitMQ)
- ✅ **Use**: `asyncio.create_task()` with proper task tracking

**Why asyncio.create_task()?**
- Handles long-running I/O-bound operations (subprocess calls, DSPy)
- Lightweight (no external dependencies)
- Can track tasks with dict: `active_tasks[task_id] = asyncio.create_task(...)`
- Proper cleanup with task cancellation

---

### 2. WebSockets

**Source**: [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)

#### What We Learned:
```python
@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Response: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

#### Key Features:
- **Connection Manager**: Track multiple clients
- **Broadcasting**: Send progress to all connected clients for a task
- **Error Handling**: `WebSocketDisconnect` exception
- **Dependency Injection**: Supports `Depends()`, `Query()`, `Header()`

#### For Our Use Case:
- ✅ **Perfect** for real-time progress streaming
- ✅ Replaces polling `GET /tasks/{id}/status`
- ✅ Each task has its own WebSocket channel: `/ws/{task_id}`
- ✅ Send events: `PLANNING_COMPLETE`, `MODULE_STARTED`, `TEST_PASSED`, etc.

---

### 3. Streaming Responses

**Source**: [FastAPI Custom Response](https://fastapi.tiangolo.com/advanced/custom-response/)

#### What We Learned:
```python
from fastapi.responses import StreamingResponse

async def log_streamer(task_id: str):
    while task_running(task_id):
        log_lines = await get_new_logs(task_id)
        for line in log_lines:
            yield f"{line}\n"
        await asyncio.sleep(0.1)

@app.get("/tasks/{task_id}/logs/stream")
async def stream_logs(task_id: str):
    return StreamingResponse(
        log_streamer(task_id),
        media_type="text/plain"
    )
```

#### For Our Use Case:
- ✅ **Use** for streaming logs (alternative to WebSocket)
- ✅ HTTP-based (easier for `curl`, browser)
- ⚠️ **Note**: WebSocket is better for bi-directional communication

---

### 4. Startup and Shutdown Events

**Source**: [FastAPI Events](https://fastapi.tiangolo.com/advanced/events/)

#### Modern Approach: Lifespan
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DSPy, Ollama connection
    print("Configuring DSPy...")
    configure_dspy()
    yield
    # Shutdown: Cleanup tasks, connections
    print("Shutting down...")
    await cleanup_tasks()

app = FastAPI(lifespan=lifespan)
```

#### For Our Use Case:
- ✅ **Use** lifespan for DSPy configuration
- ✅ Initialize Ollama connection at startup
- ✅ Cleanup running tasks on shutdown

---

### 5. Async vs Def

**Source**: [FastAPI Async](https://fastapi.tiangolo.com/async/)

#### When to Use Each:

| Use Case | Function Type | Why |
|----------|--------------|-----|
| Database queries | `async def` | I/O-bound, awaitable |
| Subprocess calls (pytest, Deno) | `async def` | I/O-bound with `asyncio.create_subprocess_exec` |
| DSPy calls | `async def` | Can be long-running I/O |
| Simple responses | `def` | No I/O, just return data |

#### For Our Use Case:
- ✅ All endpoints: `async def` (default)
- ✅ Background tasks: `async def`
- ✅ WebSocket handlers: `async def`

---

### 6. Deployment (Network Access)

**Source**: [FastAPI Manual Deployment](https://fastapi.tiangolo.com/deployment/manually/)

#### Running on Network:
```bash
uvicorn main:app --host 0.0.0.0 --port 9876
```

- `--host 0.0.0.0`: Listen on all network interfaces (WiFi access)
- `--port 9876`: Uncommon port (avoid conflicts)
- No `--reload` in production (high resource usage)

#### For Our Use Case:
- ✅ Port 9876 (user's requirement: uncommon port)
- ✅ `--host 0.0.0.0` (laptop access over WiFi)
- ✅ Single worker initially (can scale later)

---

## Proposed Architecture

### Current (stdio MCP):
```
Claude Desktop
    ↓ stdin/stdout (JSON-RPC)
MCP Server
    ↓
Code Intern Workflow
    ↓
Ollama
```

### New (FastAPI + WebSocket):
```
Laptop Browser/Client (WiFi 192.168.1.x)
    ↓ HTTP/WebSocket
FastAPI Server (port 9876)
    ├── REST API (/tasks, /status)
    ├── WebSocket (/ws/{task_id})
    └── asyncio Background Tasks
         ↓
    Code Intern Workflow (DSPy)
         ↓
    Ollama (localhost:11434)
```

---

## File Structure Changes (Planned)

### New Files to Create:

```
src/api/
├── __init__.py
├── fastapi_server.py       # Main FastAPI app (≤100 lines)
├── websocket_manager.py    # WebSocket connection manager (≤100 lines)
├── task_manager.py         # asyncio task tracking (≤100 lines)
├── endpoints/
│   ├── __init__.py
│   ├── tasks.py            # POST /tasks, GET /tasks/{id} (≤100 lines)
│   ├── logs.py             # GET /tasks/{id}/logs (≤100 lines)
│   └── websocket.py        # WebSocket endpoints (≤100 lines)
└── models/
    ├── __init__.py
    ├── requests.py         # Pydantic request models (≤100 lines)
    └── responses.py        # Pydantic response models (≤100 lines)
```

### Files to Modify:

1. **src/orchestrator/workflow.py**
   - Add event emission to WebSocket
   - Hook into WebSocketManager
   - No major refactor

2. **src/orchestrator/state.py**
   - Add `asyncio.Task` reference
   - Add WebSocket connection tracking

3. **src/common/types.py**
   - Add API request/response types

### Files to Keep (No Changes):
- All existing modules (requirements, planning, codegen, testing, etc.)
- Workflow logic unchanged
- Just add API layer on top

---

## API Design (Detailed)

### 1. REST Endpoints

#### POST /tasks
**Purpose**: Start a new coding task

**Request**:
```json
{
  "prompt": "Build an email validator",
  "answers": [
    "Build validation function using regex",
    "Use regex pattern matching",
    "Python standard library",
    "re: pattern matching",
    ""
  ]
}
```

**Response**:
```json
{
  "task_id": "task-abc123",
  "status": "started",
  "websocket_url": "ws://localhost:9876/ws/task-abc123"
}
```

---

#### GET /tasks/{task_id}
**Purpose**: Get current task status

**Response**:
```json
{
  "task_id": "task-abc123",
  "status": "in_progress",
  "current_module": "validator.py",
  "iteration": 2,
  "modules_complete": 1,
  "total_modules": 3,
  "progress": 0.33
}
```

---

#### GET /tasks/{task_id}/results
**Purpose**: Get final results (code, tests, reports)

**Response**:
```json
{
  "task_id": "task-abc123",
  "status": "completed",
  "modules": [
    {
      "name": "validator.py",
      "code": "...",
      "tests": "...",
      "quality_score": 0.95
    }
  ]
}
```

---

#### GET /tasks/{task_id}/logs/stream
**Purpose**: Stream logs in real-time (SSE alternative)

**Response** (text/event-stream):
```
data: [INFO] Task started
data: [INFO] Planning complete
data: [INFO] Generating validator.py...
```

---

### 2. WebSocket Endpoints

#### WS /ws/{task_id}
**Purpose**: Real-time progress updates

**Events Sent** (Server → Client):
```json
{
  "type": "TASK_STARTED",
  "task_id": "task-abc123",
  "timestamp": "2025-11-23T16:30:00Z",
  "data": {"goal": "Build email validator"}
}

{
  "type": "PLANNING_COMPLETE",
  "task_id": "task-abc123",
  "data": {
    "modules": ["validator.py", "tests.py"],
    "estimated_iterations": 3
  }
}

{
  "type": "MODULE_ITERATION",
  "task_id": "task-abc123",
  "data": {
    "module": "validator.py",
    "iteration": 2,
    "test_pass_rate": 0.8,
    "quality_score": 0.85
  }
}

{
  "type": "TASK_COMPLETE",
  "task_id": "task-abc123",
  "data": {
    "total_time": "3m 45s",
    "modules_generated": 2
  }
}
```

**Events Received** (Client → Server):
```json
{
  "type": "INTERVENTION",
  "guidance": "Use RFC 5322 regex pattern"
}
```

---

## Implementation Details

### WebSocket Manager Pattern

**Source**: [Real-Time Dashboard Tutorial](https://testdriven.io/blog/fastapi-postgres-websockets/)

```python
# src/api/websocket_manager.py

class WebSocketManager:
    """Manages WebSocket connections for task progress streaming"""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, task_id: str, websocket: WebSocket):
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        self.active_connections[task_id].append(websocket)

    def disconnect(self, task_id: str, websocket: WebSocket):
        if task_id in self.active_connections:
            self.active_connections[task_id].remove(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]

    async def broadcast_to_task(self, task_id: str, message: dict):
        """Send event to all clients watching this task"""
        if task_id not in self.active_connections:
            return

        disconnected = []
        for connection in self.active_connections[task_id]:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # Cleanup disconnected
        for conn in disconnected:
            self.disconnect(task_id, conn)
```

---

### Task Manager Pattern

**Source**: [Managing Background Tasks in FastAPI](https://leapcell.io/blog/managing-background-tasks-and-long-running-operations-in-fastapi)

```python
# src/api/task_manager.py

class TaskManager:
    """Manages asyncio background tasks for code generation"""

    def __init__(self):
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.task_states: Dict[str, StateManager] = {}

    async def start_task(
        self,
        task_id: str,
        workflow_coro: Coroutine
    ) -> None:
        """Start background task"""
        task = asyncio.create_task(workflow_coro)
        self.active_tasks[task_id] = task

        # Cleanup when done
        task.add_done_callback(
            lambda t: self._cleanup_task(task_id)
        )

    def _cleanup_task(self, task_id: str):
        """Remove completed task"""
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]

    async def cancel_task(self, task_id: str):
        """Cancel running task"""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def shutdown_all(self):
        """Cancel all tasks on server shutdown"""
        for task_id in list(self.active_tasks.keys()):
            await self.cancel_task(task_id)
```

---

### Integration with Existing Workflow

**Minimal changes to existing code**:

```python
# src/orchestrator/workflow.py (MODIFIED)

class WorkflowOrchestrator:
    def __init__(self, websocket_manager: Optional[WebSocketManager] = None):
        # Existing init
        self.websocket_manager = websocket_manager  # NEW

    async def _emit_event(self, event_type: str, data: dict):
        """Emit event to WebSocket (NEW METHOD)"""
        if self.websocket_manager:
            event = {
                "type": event_type,
                "task_id": self.state.task_id,
                "timestamp": datetime.now().isoformat(),
                "data": data
            }
            await self.websocket_manager.broadcast_to_task(
                self.state.task_id,
                event
            )

    async def run(self):
        # Existing workflow...
        await self._emit_event("TASK_STARTED", {"goal": self.state.requirements.goal})

        # Plan
        plan = await self.planner.plan(...)
        await self._emit_event("PLANNING_COMPLETE", {"modules": len(plan.modules)})

        # Generate modules
        for module in plan.modules:
            await self._emit_event("MODULE_STARTED", {"module": module.name})
            # ... existing code ...
            await self._emit_event("MODULE_ITERATION", {"iteration": i, "score": score})

        await self._emit_event("TASK_COMPLETE", {"total_time": elapsed})
```

---

## Migration Strategy

### Phase 1: Setup FastAPI (Week 1)
- [ ] Create `src/api/` structure
- [ ] Implement `fastapi_server.py` with lifespan
- [ ] Add basic REST endpoints (POST /tasks, GET /tasks/{id})
- [ ] Test with Postman/curl

### Phase 2: WebSocket Integration (Week 1)
- [ ] Implement `WebSocketManager`
- [ ] Add WebSocket endpoint
- [ ] Integrate with `WorkflowOrchestrator`
- [ ] Test real-time events

### Phase 3: Task Management (Week 2)
- [ ] Implement `TaskManager`
- [ ] Replace demo workflow with real API
- [ ] Add cancellation support
- [ ] Test multi-task handling

### Phase 4: Network Testing (Week 2)
- [ ] Deploy on `0.0.0.0:9876`
- [ ] Test from laptop over WiFi
- [ ] Create simple HTML client for testing
- [ ] Performance testing

### Phase 5: MCP Compatibility (Optional - Week 3)
- [ ] Keep `src/mcp/` for backward compatibility
- [ ] Add HTTP-based MCP transport
- [ ] Document both access methods

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Network accessibility | Accessible from laptop over WiFi |
| Real-time latency | Events received <500ms after emission |
| Concurrent tasks | Handle 3-5 simultaneous code generation tasks |
| Task startup time | <2 seconds to start background task |
| WebSocket stability | No disconnections during 5-minute workflow |

---

## Testing Strategy

### Unit Tests
```python
# tests/test_api_endpoints.py
import pytest
from fastapi.testclient import TestClient

def test_start_task():
    client = TestClient(app)
    response = client.post("/tasks", json={"prompt": "Test"})
    assert response.status_code == 200
    assert "task_id" in response.json()
```

### WebSocket Tests
```python
# tests/test_websocket.py
from fastapi.testclient import TestClient

def test_websocket_events():
    client = TestClient(app)
    with client.websocket_connect("/ws/test-task") as websocket:
        data = websocket.receive_json()
        assert data["type"] == "TASK_STARTED"
```

---

## References

- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/)
- [Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)
- [Async Concurrency](https://fastapi.tiangolo.com/async/)
- [Manual Deployment](https://fastapi.tiangolo.com/deployment/manually/)
- [Real-Time Dashboard Tutorial](https://testdriven.io/blog/fastapi-postgres-websockets/)
- [Background Tasks Best Practices](https://leapcell.io/blog/managing-background-tasks-and-long-running-operations-in-fastapi)

---

## Next Steps

1. Review this plan
2. Read `FASTMCP.md` for FastMCP integration options
3. Decide: Pure FastAPI or FastAPI + FastMCP hybrid?
4. Get user approval before modifying `src/`
