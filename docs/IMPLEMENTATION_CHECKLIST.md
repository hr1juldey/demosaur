# Hybrid FastAPI + FastMCP + Event Sourcing - Implementation Checklist

**Implementation Strategy**: Sequential Build-Test-Build-Test
**Test Gate Policy**: ⛔ **STOP** if any test fails. Fix before proceeding.
**Code Constraints**: ≤100 lines per file, SRP, SOLID principles, absolute imports only

---

## Phase 0: Foundation Setup ✅ (Already Complete)

- ✅ DSPy configured with Ollama
- ✅ FastMCP server (`src/mcp/fastmcp_server.py`)
- ✅ Server runner with stdio/HTTP modes (`src/mcp/server_runner.py`)
- ✅ Dead code detection system (`src/deadcode/`)
- ✅ Port 9876 configured

**Dependencies**: Already in `requirements.txt`

```bash
fastmcp>=2.13.1
dspy-ai>=2.5.0
pydantic>=2.12.4
httpx>=0.28.1
```

---

## Phase 1: Event Store Foundation 🏗️

**Goal**: Implement event sourcing as single source of truth
**Rationale**: Event store must exist before all async orchestration

### 1.1 Core Event Types

**File**: `src/events/__init__.py` (≤20 lines)

- [ ] Create module structure
- [ ] Export all public types

**File**: `src/events/event_types.py` (≤100 lines)

- [ ] Define `EventType` enum
  - TASK_STARTED, PLANNING_COMPLETE, CODE_GENERATED
  - TEST_STARTED, TEST_PASSED, TEST_FAILED
  - CORRECTION_STARTED, CORRECTION_COMPLETED
  - BUG_REPORT_RECEIVED, USER_INTERVENTION
  - MODULE_STARTED, MODULE_ITERATION, MODULE_COMPLETE
  - TASK_COMPLETE, TASK_FAILED

**File**: `src/events/event.py` (≤100 lines)

- [ ] Define `Event` dataclass (frozen=True)
  - event_id: str (UUID)
  - task_id: str
  - event_type: EventType
  - timestamp: datetime
  - sequence_number: int (Lamport clock)
  - vector_clock: Dict[str, int]
  - causation_id: Optional[str]
  - correlation_id: str
  - data: dict
  - code_version: int
- [ ] Add `__post_init__` validation
- [ ] Add `to_dict()` method for serialization

### 1.2 Vector Clock Implementation

**File**: `src/events/vector_clock.py` (≤100 lines)

- [ ] Implement `VectorClock` class
  - `tick(process_id: str)` - increment clock
  - `merge(other: Dict[str, int])` - merge clocks (max of each)
  - `happens_before(clock1, clock2)` - causality check
  - `concurrent(clock1, clock2)` - concurrency check
- [ ] Add clock comparison utilities

### 1.3 Event Store

**File**: `src/events/event_store.py` (≤100 lines)

- [ ] Implement `EventStore` class
  - `__init__()` - initialize with lock, sequence counter
  - `async append(event: Event)` - append-only, thread-safe
  - `async get_events(task_id, after_sequence=0)` - query events
  - `async get_latest_version(task_id)` - get current code version
  - `async _persist(event)` - save to disk (JSON file for now)
- [ ] Use `asyncio.Lock()` for thread safety

### 1.4 State Projections

**File**: `src/events/projections.py` (≤100 lines)

- [ ] Implement `StateProjection` class
  - `async rebuild_state(task_id)` - replay events to build state
  - `_apply_event(state, event)` - state transition logic
  - Support all EventType transitions
- [ ] Add state validation

### 1.5 Event Ordering Utilities

**File**: `src/events/ordering.py` (≤100 lines)

- [ ] Implement `EventOrdering` class
  - `is_report_valid_for_current_code(bug_report, correction)` - 3-layer validation
  - `filter_stale_events(events, current_version)` - remove obsolete events
- [ ] Add version monotonicity checks

### 🧪 TEST GATE 1: Event Store Tests

**File**: `tests/test_event_store.py` (≤100 lines)

- [ ] Test event append (sequence numbers increment)
- [ ] Test event retrieval (filtering by task_id)
- [ ] Test persistence (save/load from disk)
- [ ] Test concurrent append (thread safety)

**File**: `tests/test_vector_clock.py` (≤100 lines)

- [ ] Test happens_before (causality detection)
- [ ] Test concurrent (no causal relationship)
- [ ] Test merge (max of each process)
- [ ] Test edge cases (empty clocks, single process)

**File**: `tests/test_projections.py` (≤100 lines)

- [ ] Test state rebuild from events
- [ ] Test version tracking
- [ ] Test stale event filtering
- [ ] Test all event type transitions

**Run Tests**:

```bash
pytest tests/test_event_store.py tests/test_vector_clock.py tests/test_projections.py -v
```

⛔ **STOP HERE IF ANY TEST FAILS** ⛔

---

## Phase 2: Task Orchestration 🎯

**Goal**: Implement priority queue with backpressure
**Dependencies**: Phase 1 (Event Store)

### 2.1 Priority System

**File**: `src/orchestrator/priority.py` (≤100 lines)

- [ ] Define `TaskPriority` IntEnum
  - CRITICAL = 0 (user intervention, urgent bugs)
  - HIGH = 10 (code generation main path)
  - MEDIUM = 20 (testing, refinement)
  - LOW = 30 (logging, metrics)
  - BACKGROUND = 40 (cleanup, analysis)
- [ ] Implement `TaskPriorityAssigner`
  - `assign_priority(event: Event) -> TaskPriority`
  - `should_preempt(new_event, current_task) -> bool`

**File**: `src/orchestrator/prioritized_task.py` (≤100 lines)

- [ ] Define `PrioritizedTask` dataclass (order=True)
  - priority: int
  - sequence: int (tie-breaker)
  - task_id: str
  - coro: Coroutine
  - timeout: float = 300.0

### 2.2 Task Orchestrator

**File**: `src/orchestrator/task_orchestrator.py` (≤100 lines)

- [ ] Implement `TaskOrchestrator` class
  - `__init__(max_concurrent=5, max_queue_size=100)`
  - `async start_workers(num_workers=3)` - start worker pool
  - `async submit_task(coro, task_id, priority, timeout)` - blocks if full
  - `async _worker(worker_id)` - process queue with semaphore
  - `async get_queue_stats()` - monitoring
  - `async shutdown()` - cleanup all tasks
- [ ] Use `asyncio.PriorityQueue(maxsize=100)` (bounded!)
- [ ] Use `asyncio.Semaphore(max_concurrent)` for limit

### 2.3 Backpressure Monitoring

**File**: `src/orchestrator/backpressure.py` (≤100 lines)

- [ ] Implement `BackpressureMonitor` class
  - `async monitor(orchestrator)` - continuous monitoring
  - `_check_queue_health(stats)` - alert on 80% full
  - `_emit_alert(level, message)` - logging/events

### 🧪 TEST GATE 2: Task Orchestration Tests

**File**: `tests/test_task_orchestrator.py` (≤100 lines)

- [ ] Test priority ordering (CRITICAL before BACKGROUND)
- [ ] Test max concurrent limit (semaphore enforcement)
- [ ] Test backpressure (queue blocks when full)
- [ ] Test worker pool (3 workers process tasks)
- [ ] Test timeout (long-running tasks cancelled)
- [ ] Test graceful shutdown

**File**: `tests/test_priority_assignment.py` (≤100 lines)

- [ ] Test priority assignment for each event type
- [ ] Test preemption logic (2-level difference)

**Run Tests**:

```bash
pytest tests/test_task_orchestrator.py tests/test_priority_assignment.py -v
```

⛔ **STOP HERE IF ANY TEST FAILS** ⛔

---

## Phase 3: Context Management for Small LLMs 🧠

**Goal**: Manage context window for Mistral 7B (8K) and Qwen3 8B (32K)
**Dependencies**: Phase 1 (Event Store)

### 3.1 Context Manager

**File**: `src/context/context_manager.py` (≤100 lines)

- [ ] Implement `ContextManager` class
  - `__init__()` - define model limits (8K, 32K, 200K)
  - `async prepare_context(event, model="mistral:7b")` - build minimal context
  - `_estimate_tokens(text)` - rough estimate (chars/4)
  - `_should_route_to_larger_model(token_count, limit)` - 80% threshold
- [ ] 4-layer context: cached prompt + state summary + compressed events + current event

### 3.2 Event Summarizer

**File**: `src/context/event_summarizer.py` (≤100 lines)

- [ ] Implement `EventSummarizer` class
  - `async summarize_task_history(task_id, keep_recent=5)` - compress old events
  - `_compress_event(event)` - 10x token reduction
  - `_count_by_type(events, event_type)` - statistics
- [ ] Format: Summary (500 tokens) + Recent events (full detail)

### 3.3 System Prompt Cache

**File**: `src/context/prompt_cache.py` (≤100 lines)

- [ ] Implement `SystemPromptCache` class
  - `get_cached_prompt(event_type)` - retrieve or generate
  - `_generate_system_prompt(event_type)` - create new prompt
  - `clear_cache()` - invalidate all
- [ ] Store in-memory dict (10x cost savings)

### 3.4 Relevance Filter

**File**: `src/context/relevance_filter.py` (≤100 lines)

- [ ] Implement `RelevanceFilter` class
  - `async get_relevant_events(task_id, event_type, limit=10)` - filter by relevance
  - `_is_relevant(event, target_type)` - heuristics
    - Same module
    - Same code version
    - Causal chain (follows causation_id)
- [ ] Return last N relevant events in chronological order

### 🧪 TEST GATE 3: Context Management Tests

**File**: `tests/test_context_manager.py` (≤100 lines)

- [ ] Test context preparation (4 layers)
- [ ] Test token estimation
- [ ] Test model routing (mistral → qwen3 if >80%)
- [ ] Test cache hit (reuse system prompt)

**File**: `tests/test_event_summarizer.py` (≤100 lines)

- [ ] Test event compression (10x reduction)
- [ ] Test summary generation
- [ ] Test keep_recent logic

**File**: `tests/test_relevance_filter.py` (≤100 lines)

- [ ] Test relevance heuristics
- [ ] Test limit enforcement
- [ ] Test chronological ordering

**Run Tests**:

```bash
pytest tests/test_context_manager.py tests/test_event_summarizer.py tests/test_relevance_filter.py -v
```

⛔ **STOP HERE IF ANY TEST FAILS** ⛔

---

## Phase 4: FastAPI + WebSocket Layer 🌐

**Goal**: Network-accessible API with real-time updates
**Dependencies**: Phase 1 (Event Store), Phase 2 (Task Orchestrator)

### 4.1 Pydantic Models

**File**: `src/api/__init__.py` (≤20 lines)

- [ ] Create module structure
- [ ] Export main app

**File**: `src/api/models/requests.py` (≤100 lines)

- [ ] Define `TaskRequest` model
  - prompt: str
  - answers: List[str] = []
  - priority: Optional[str] = "MEDIUM"
- [ ] Define `InterventionRequest` model
  - guidance: str

**File**: `src/api/models/responses.py` (≤100 lines)

- [ ] Define `TaskResponse` model
  - task_id: str
  - status: str
  - websocket_url: str
- [ ] Define `TaskStatusResponse` model
  - task_id, status, current_module, iteration, progress
- [ ] Define `WebSocketMessage` model
  - type: str
  - task_id: str
  - version: int (code version)
  - sequence: int (event sequence)
  - timestamp: float
  - data: dict

### 4.2 WebSocket Manager

**File**: `src/api/websocket_manager.py` (≤100 lines)

- [ ] Implement `WebSocketManager` class
  - `async connect(task_id, websocket)` - accept and track connection
  - `disconnect(task_id, websocket)` - remove connection
  - `async broadcast_to_task(task_id, message)` - send to all clients
  - `_cleanup_disconnected(task_id, failed_conns)` - error handling
- [ ] Track: `Dict[str, List[WebSocket]]`

### 4.3 Task Manager (FastAPI Integration)

**File**: `src/api/task_manager.py` (≤100 lines)

- [ ] Implement `TaskManager` class
  - `async start_task(task_id, workflow_coro)` - create_task + callback
  - `async cancel_task(task_id)` - cancel running task
  - `async get_task_status(task_id)` - query from event store
  - `async shutdown_all()` - cleanup on server shutdown
  - `_cleanup_task(task_id)` - callback when done
- [ ] Track: `Dict[str, asyncio.Task]`

### 4.4 Health Endpoint

**File**: `src/api/endpoints/__init__.py` (≤20 lines)

- [ ] Export all routers

**File**: `src/api/endpoints/health.py` (≤50 lines)

- [ ] Define `router = APIRouter()`
- [ ] `GET /health` - return server status
  - DSPy configured
  - Ollama reachable
  - Event store status
  - Queue stats (if orchestrator available)

### 4.5 Task Endpoints

**File**: `src/api/endpoints/tasks.py` (≤100 lines)

- [ ] Define `router = APIRouter()`
- [ ] `POST /tasks` - start new task
  - Generate task_id (UUID)
  - Submit to orchestrator with priority
  - Return TaskResponse with WebSocket URL
- [ ] `GET /tasks/{task_id}` - get status
  - Query event store
  - Calculate progress from events
  - Return TaskStatusResponse
- [ ] `DELETE /tasks/{task_id}` - cancel task
  - Call task_manager.cancel_task()

### 4.6 WebSocket Endpoint

**File**: `src/api/endpoints/websocket.py` (≤100 lines)

- [ ] Define `router = APIRouter()`
- [ ] `WS /ws/{task_id}` - real-time updates
  - Connect via ws_manager
  - Listen for client interventions
  - Handle WebSocketDisconnect
  - Send versioned messages (WebSocketMessage model)

### 4.7 Versioned State Manager

**File**: `src/api/versioned_state.py` (≤100 lines)

- [ ] Implement `VersionedState` class
  - `async update(new_state, event)` - version monotonicity check
  - `async get_current_version(task_id)` - retrieve latest
  - `_reject_stale_update(new_version, current)` - validation
- [ ] Use asyncio.Lock for thread safety

### 🧪 TEST GATE 4: FastAPI Tests

**File**: `tests/test_api_models.py` (≤100 lines)

- [ ] Test Pydantic model validation
- [ ] Test serialization/deserialization

**File**: `tests/test_websocket_manager.py` (≤100 lines)

- [ ] Test connect/disconnect
- [ ] Test broadcast to multiple clients
- [ ] Test cleanup of disconnected clients

**File**: `tests/test_task_manager.py` (≤100 lines)

- [ ] Test start_task (asyncio.create_task)
- [ ] Test cancel_task
- [ ] Test cleanup callback

**File**: `tests/test_endpoints.py` (≤100 lines)

- [ ] Test POST /tasks (create task)
- [ ] Test GET /tasks/{task_id} (status)
- [ ] Test GET /health
- [ ] Use FastAPI TestClient

**File**: `tests/test_websocket_endpoint.py` (≤100 lines)

- [ ] Test WebSocket connection
- [ ] Test message versioning
- [ ] Test stale update rejection (version < current)
- [ ] Use TestClient WebSocket support

**Run Tests**:

```bash
pytest tests/test_api_models.py tests/test_websocket_manager.py tests/test_task_manager.py tests/test_endpoints.py tests/test_websocket_endpoint.py -v
```

⛔ **STOP HERE IF ANY TEST FAILS** ⛔

---

## Phase 5: Hybrid FastAPI + FastMCP Main App 🔗

**Goal**: Mount FastMCP under /mcp/, integrate all components
**Dependencies**: All previous phases

### 5.1 Main FastAPI App

**File**: `src/api/main.py` (≤100 lines)

- [ ] Import FastAPI, lifespan
- [ ] Create global managers (ws_manager, task_manager, orchestrator)
- [ ] Define `lifespan(app)` context manager
  - Startup: Configure DSPy, start orchestrator workers
  - Shutdown: task_manager.shutdown_all(), orchestrator.shutdown()
- [ ] Create `app = FastAPI(title="Code Intern API", version="2.0.0", lifespan=lifespan)`
- [ ] Include routers: health, tasks, websocket
- [ ] Mount FastMCP: `app.mount("/mcp", mcp.get_asgi_app())`
- [ ] Store managers in `app.state` (ws_manager, task_manager, orchestrator)
- [ ] Add `if __name__ == "__main__"` with uvicorn.run (0.0.0.0:9876)

### 5.2 Modify Existing MCP Server

**File**: `src/mcp/fastmcp_server.py` (MODIFY)

- [ ] Add at end of file:

  ```python
  def get_asgi_app():
      """Export FastMCP as ASGI app for mounting"""
      return mcp.get_asgi_app()
  ```

- [ ] Ensure all existing tools remain unchanged
- [ ] Keep stdio functionality intact

### 5.3 Update Server Runner

**File**: `src/mcp/server_runner.py` (MODIFY)

- [ ] Add new option: `--fastapi` (runs hybrid server)
- [ ] Keep existing: `--http` (FastMCP HTTP only), default (stdio)
- [ ] If `--fastapi`: run `uvicorn src.api.main:app --host 0.0.0.0 --port 9876`

### 🧪 TEST GATE 5: Integration Tests

**File**: `tests/test_hybrid_integration.py` (≤100 lines)

- [ ] Test FastAPI endpoints (POST /tasks)
- [ ] Test FastMCP tools (at /mcp/)
- [ ] Test shared state (both use same task_manager)
- [ ] Test lifespan (startup/shutdown)

**File**: `tests/test_network_access.py` (≤100 lines)

- [ ] Test access from 0.0.0.0:9876
- [ ] Test WebSocket connection
- [ ] Test MCP endpoint at /mcp/

**Run Tests**:

```bash
pytest tests/test_hybrid_integration.py tests/test_network_access.py -v
```

⛔ **STOP HERE IF ANY TEST FAILS** ⛔

---

## Phase 6: Workflow Integration 🔄

**Goal**: Integrate event sourcing into existing workflow
**Dependencies**: All previous phases

### 6.1 Modify Workflow Orchestrator

**File**: `src/orchestrator/workflow.py` (MODIFY, keep ≤100 lines)

- [ ] Add `__init__` parameters:
  - `websocket_manager: Optional[WebSocketManager] = None`
  - `event_store: Optional[EventStore] = None`
  - `context_manager: Optional[ContextManager] = None`
- [ ] Add method: `async _emit_event(event_type, data)`
  - Create Event with version, vector clock
  - Append to event_store
  - Broadcast to websocket_manager (if present)
- [ ] Insert event emissions:
  - After task start: TASK_STARTED
  - After planning: PLANNING_COMPLETE
  - Before module: MODULE_STARTED
  - After iteration: MODULE_ITERATION
  - After task: TASK_COMPLETE

**Note**: If workflow.py exceeds 100 lines, split into:

- `src/orchestrator/workflow.py` (core logic)
- `src/orchestrator/workflow_events.py` (event emission)

### 6.2 Modify State Manager

**File**: `src/orchestrator/state.py` (MODIFY)

- [ ] Add field: `asyncio_task: Optional[asyncio.Task] = None`
- [ ] Add field: `websocket_connections: List[WebSocket] = field(default_factory=list)`
- [ ] Add field: `code_version: int = 0`
- [ ] Keep all existing fields

### 🧪 TEST GATE 6: Workflow Integration Tests

**File**: `tests/test_workflow_events.py` (≤100 lines)

- [ ] Test event emission during workflow
- [ ] Test version increment on code changes
- [ ] Test WebSocket broadcast
- [ ] Test event store population

**File**: `tests/test_end_to_end.py` (≤100 lines)

- [ ] Test complete workflow from POST /tasks to completion
- [ ] Test WebSocket receives all events
- [ ] Test version monotonicity (no stale updates)
- [ ] Test event store contains full history
- [ ] Test context manager used for small LLM calls

**Run Tests**:

```bash
pytest tests/test_workflow_events.py tests/test_end_to_end.py -v
```

⛔ **STOP HERE IF ANY TEST FAILS** ⛔

---

## Phase 7: Manual Testing & Deployment 🚀

**Goal**: Verify network access and real-world usage

### 7.1 Local Testing

- [ ] Start server: `python -m src.api.main` or `uvicorn src.api.main:app --host 0.0.0.0 --port 9876`
- [ ] Test REST API:

  ```bash
  curl -X POST http://localhost:9876/tasks \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Build email validator"}'
  ```

- [ ] Test WebSocket:

  ```bash
  wscat -c ws://localhost:9876/ws/[task-id]
  ```

- [ ] Test MCP endpoint: `http://localhost:9876/mcp/`
- [ ] Test stdio mode: `python -m src.mcp.server_runner`

### 7.2 Network Testing (WiFi)

- [ ] Start server on PC (192.168.1.4)
- [ ] From laptop on same WiFi:

  ```bash
  curl -X POST http://192.168.1.4:9876/tasks \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Test from laptop"}'
  ```

- [ ] Test WebSocket from laptop
- [ ] Verify real-time progress updates

### 7.3 Performance Testing

- [ ] Test concurrent tasks (3-5 simultaneous)
- [ ] Monitor queue stats (`GET /health` includes queue info)
- [ ] Test backpressure (submit 105 tasks, should block)
- [ ] Test context window management (verify <80% for mistral:7b)

### 7.4 Update Documentation

**File**: `docs/QUICKSTART.md` (UPDATE)

- [ ] Add new FastAPI mode instructions
- [ ] Add network access instructions
- [ ] Add WebSocket usage examples

**File**: `docs/API.md` (NEW)

- [ ] Document all REST endpoints
- [ ] Document WebSocket protocol
- [ ] Document MCP endpoints
- [ ] Include curl examples

---

## Summary: File Count by Phase

| Phase | New Files | Modified Files | Test Files | Total Lines |
|-------|-----------|----------------|------------|-------------|
| **Phase 1: Event Store** | 6 | 0 | 3 | ~900 |
| **Phase 2: Orchestration** | 3 | 0 | 2 | ~500 |
| **Phase 3: Context Mgmt** | 4 | 0 | 3 | ~600 |
| **Phase 4: FastAPI/WS** | 8 | 0 | 5 | ~1200 |
| **Phase 5: Hybrid App** | 1 | 2 | 2 | ~300 |
| **Phase 6: Integration** | 0 | 2 | 2 | ~200 |
| **TOTAL** | **22 new** | **4 modified** | **17 tests** | **~3700 lines** |

**All files**: ≤100 lines each
**Total test coverage**: 17 test files

---

## Technologies Used

From `requirements.txt`:

- ✅ `dspy-ai>=2.5.0` - LLM framework
- ✅ `fastmcp>=2.13.1` - MCP protocol
- ✅ `pydantic>=2.12.4` - Data validation
- ✅ `httpx>=0.28.1` - HTTP client
- ✅ `aiofiles>=25.1.0` - Async file I/O
- ✅ `pytest>=9.0.1` - Testing
- ✅ `pytest-asyncio>=1.3.0` - Async tests

**Additional dependencies needed**:

```bash
pip install fastapi uvicorn[standard] websockets
```

---

## Risk Mitigation

### Critical Test Gates

1. **Phase 1 Gate**: Event store must be 100% reliable (source of truth)
2. **Phase 2 Gate**: Task orchestrator must handle backpressure correctly
3. **Phase 4 Gate**: WebSocket versioning must reject stale updates
4. **Phase 6 Gate**: End-to-end workflow must emit all events correctly

### Rollback Plan

If any phase fails unrecoverably:

- Revert to previous working phase
- Fix in isolation
- Re-run all tests from failed phase onward

### Performance Targets

- Event append: <10ms
- State projection: <100ms
- WebSocket broadcast: <50ms
- Task submission: <2s (including orchestrator queue)
- Context preparation: <500ms

---

## Next Steps After Approval

1. ✅ Get user approval on this checklist
2. 📝 User grants write access to `src/`
3. 🏗️ Start Phase 1: Event Store Foundation
4. 🧪 Run Test Gate 1
5. ⏭️ Proceed to Phase 2 only if all tests pass

**Current Status**: ⏸️ Awaiting user approval and write access to `src/`
