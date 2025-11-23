# Hybrid FastAPI + FastMCP + Event Sourcing - DETAILED Implementation Checklist

**CRITICAL FINDINGS from Codebase Analysis**:
- ⚠️ Existing event system in `src/orchestrator/events.py` (simple, no vector clocks)
- ⚠️ Streaming already exists in `src/orchestrator/streaming.py` (AsyncIterator pattern)
- ⚠️ Global state dictionaries NOT thread-safe (StateManager, InterventionManager)
- ⚠️ AsyncLogger file writes NOT atomic (race conditions)
- ⚠️ TestRunner uses subprocess.run (blocks event loop, not truly async)

---

## Phase 1: Event Store Foundation 🏗️

### 1.1 Core Event Types

**File**: `src/events/__init__.py` (≤20 lines)
- [ ] Create module structure
- [ ] Export: Event, EventType, EventStore, VectorClock, StateProjection, EventOrdering

**File**: `src/events/event_types.py` (≤100 lines)
- [ ] Define `EventType` enum with 18 types

**INTEGRATION NOTE**: Must merge with existing `src/orchestrator/events.py`:
- Existing: TASK_STARTED, PLANNING_COMPLETE, MODULE_STARTED, MODULE_ITERATION, TASK_COMPLETE
- New additions: CODE_GENERATED, CORRECTION_STARTED, CORRECTION_COMPLETED, BUG_REPORT_RECEIVED, TEST_STARTED, TEST_PASSED, TEST_FAILED

**File**: `src/events/event.py` (≤100 lines)
- [ ] Define `Event` dataclass (frozen=True)
- [ ] Add `__post_init__` validation
- [ ] Add `to_dict()` method

**PASSING CRITERIA**:
- ✅ Event is immutable (frozen=True enforced)
- ✅ event_id is valid UUID format
- ✅ task_id is non-empty string
- ✅ timestamp is valid ISO 8601
- ✅ sequence_number is positive integer
- ✅ code_version ≥ 0

**FAILING CRITERIA**:
- ❌ Event modified after creation (raises FrozenInstanceError)
- ❌ event_id is None or empty
- ❌ task_id is None, empty, or non-string
- ❌ vector_clock is not Dict[str, int]
- ❌ data contains non-serializable objects

**EDGE CASES**:
1. Empty vector_clock {} - should be valid
2. causation_id = None - valid for root events
3. data = {} - valid empty metadata
4. Large data dict (>1MB) - should handle
5. Unicode in task_id - should sanitize
6. Negative code_version - should reject
7. Future timestamp - should reject
8. sequence_number = 0 - should allow (initial event)

---

### 1.2 Vector Clock Implementation

**File**: `src/events/vector_clock.py` (≤100 lines)
- [ ] Implement `VectorClock` class

**PASSING CRITERIA**:
- ✅ tick() increments process_id counter by exactly 1
- ✅ merge() takes max of each process value
- ✅ happens_before() correctly identifies causal precedence
- ✅ concurrent() returns True when no causal relationship exists
- ✅ Empty clocks handled (return False for happens_before)

**FAILING CRITERIA**:
- ❌ tick() increments by ≠1
- ❌ merge() doesn't take max (takes min, sum, etc.)
- ❌ happens_before() false positive (clock1 || clock2 returns True)
- ❌ happens_before() false negative (clock1 < clock2 returns False)
- ❌ concurrent() returns True for causal events

**EDGE CASES**:
1. **Empty clocks**: {} vs {} - should be concurrent
2. **Single process**: {"p1": 5} vs {"p1": 3} - should be happens_before
3. **Disjoint processes**: {"p1": 1} vs {"p2": 1} - should be concurrent
4. **Subset relation**: {"p1": 1} vs {"p1": 1, "p2": 1} - happens_before
5. **Equal clocks**: {"p1": 5, "p2": 3} vs {"p1": 5, "p2": 3} - concurrent (not <)
6. **Negative values**: {"p1": -1} - should reject or sanitize
7. **Process ID collision**: Same process_id from different sources
8. **Very large values**: {"p1": 2^63} - integer overflow check

---

### 1.3 Event Store

**File**: `src/events/event_store.py` (≤100 lines)
- [ ] Implement `EventStore` class

**PASSING CRITERIA**:
- ✅ append() is thread-safe (asyncio.Lock)
- ✅ Sequence numbers increment by exactly 1 with no gaps
- ✅ Persistence succeeds and file is readable
- ✅ get_events() filters by task_id correctly
- ✅ get_events(after_sequence=N) returns only events > N
- ✅ Concurrent appends don't corrupt sequence

**FAILING CRITERIA**:
- ❌ Sequence number gaps exist (e.g., 1, 2, 4...)
- ❌ Sequence numbers repeat (e.g., 1, 2, 2, 3)
- ❌ Concurrent appends cause race condition
- ❌ Persistence fails silently
- ❌ get_events() returns events from wrong task
- ❌ File corruption on interrupted write

**EDGE CASES**:
1. **Concurrent append from 10 tasks** - all should get unique sequences
2. **Disk full during persist** - should handle gracefully
3. **File permissions** - should handle permission errors
4. **Large event data** (10MB) - should handle or reject with clear error
5. **Very long task_id** (1000 chars) - should handle or reject
6. **Special chars in task_id** (`/`, `\`, null) - should sanitize
7. **append() interrupted mid-write** - should not corrupt store
8. **get_events() with negative after_sequence** - should handle
9. **Empty store** - get_events() should return []
10. **Million events** - performance should be acceptable (<1s)

---

### 1.4 State Projections

**File**: `src/events/projections.py` (≤100 lines)
- [ ] Implement `StateProjection` class

**PASSING CRITERIA**:
- ✅ rebuild_state() replays all events in order
- ✅ State matches last code_version from events
- ✅ Stale events (old version) are ignored
- ✅ All EventType transitions handled
- ✅ No events = empty state (not error)

**FAILING CRITERIA**:
- ❌ rebuild_state() misses events
- ❌ rebuild_state() replays in wrong order
- ❌ State includes data from stale events
- ❌ Unknown EventType causes crash
- ❌ Empty event list causes error

**EDGE CASES**:
1. **No events for task_id** - should return empty initialized state
2. **Out-of-order events** (by timestamp) - should use sequence_number
3. **Duplicate sequence numbers** - should detect and error
4. **Missing causation chain** - should handle gracefully
5. **BUG_REPORT for old version** - should ignore if code_version doesn't match
6. **CORRECTION_COMPLETED without CORRECTION_STARTED** - should handle
7. **Multiple CODE_GENERATED** - should keep latest version
8. **Event with invalid data structure** - should handle or validate
9. **Very long event chain** (10k events) - performance check (<5s)
10. **CODE_GENERATED with version < current** - should reject as stale

---

### 1.5 Event Ordering Utilities

**File**: `src/events/ordering.py` (≤100 lines)
- [ ] Implement `EventOrdering` class

**PASSING CRITERIA**:
- ✅ is_report_valid_for_current_code() uses all 3 methods (version, clock, hash)
- ✅ Version mismatch → False
- ✅ Clock causality (report before correction) → False
- ✅ Hash mismatch → False
- ✅ All checks pass → True

**FAILING CRITERIA**:
- ❌ Only checks 1 or 2 of the 3 methods
- ❌ Version match + clock mismatch → returns True (should be False)
- ❌ Hash missing in event → crashes (should handle gracefully)

**EDGE CASES**:
1. **Report and correction same version, concurrent clocks** - should use hash
2. **Hash missing in both events** - should fall back to version+clock
3. **code_hash is None** - should handle gracefully
4. **Report version > correction version** - invalid state, should detect
5. **Correction without hash** - should handle
6. **Empty causation chain** - should handle
7. **Report with future timestamp** - should not affect ordering (use sequence)

### 🧪 TEST GATE 1: Event Store Tests

**File**: `tests/test_event_store.py` (≤100 lines)

```python
# Test 1: Sequential append
✅ PASS: Events [1,2,3,4,5] have sequence_numbers [1,2,3,4,5]
❌ FAIL: Any gap, duplicate, or out-of-order sequence

# Test 2: Concurrent append
✅ PASS: 100 concurrent appends produce 100 unique sequences [1..100]
❌ FAIL: Any collision, gap, or duplicate

# Test 3: Persistence
✅ PASS: After append, file exists and is valid JSON
✅ PASS: Load from file reproduces exact events
❌ FAIL: File corrupt, missing, or events lost

# Test 4: Filtering
✅ PASS: get_events("task-A") returns only task-A events
✅ PASS: get_events("task-B", after_sequence=5) returns only seq > 5
❌ FAIL: Wrong events returned, or missing events

# Test 5: Thread safety
✅ PASS: 10 async tasks appending 10 events each = 100 total, all unique
❌ FAIL: Race condition, lost events, or duplicate sequences
```

**File**: `tests/test_vector_clock.py` (≤100 lines)

```python
# Test 1: Causality detection
✅ PASS: {"p1":1} happens_before {"p1":2} → True
✅ PASS: {"p1":1} happens_before {"p1":1,"p2":1} → True
❌ FAIL: Returns False for clear causal relationship

# Test 2: Concurrency detection
✅ PASS: {"p1":1} concurrent {"p2":1} → True
✅ PASS: {"p1":2,"p2":1} concurrent {"p1":1,"p2":2} → True
❌ FAIL: Returns False for clearly concurrent events

# Test 3: Merge correctness
✅ PASS: merge({"p1":5},{"p1":3,"p2":1}) → {"p1":5,"p2":1}
❌ FAIL: Doesn't take max, or loses processes

# Test 4: Edge cases
✅ PASS: {} concurrent {} → True
✅ PASS: {"p1":0} handled correctly
❌ FAIL: Crash on empty clocks or zero values
```

**File**: `tests/test_projections.py` (≤100 lines)

```python
# Test 1: State rebuild
✅ PASS: Events [CODE_GEN(v1), CORRECTION(v2)] → state.code_version=2
❌ FAIL: Wrong version, or missing updates

# Test 2: Stale event filtering
✅ PASS: BUG_REPORT(v1) after CORRECTION(v2) → ignored in state
❌ FAIL: Stale data included in state

# Test 3: All event type handling
✅ PASS: Each of 18 EventTypes processes without error
❌ FAIL: Unknown EventType causes crash

# Test 4: Empty events
✅ PASS: rebuild_state([]) → empty initialized state, no error
❌ FAIL: Crashes or returns None
```

**Run Tests**:
```bash
pytest tests/test_event_store.py tests/test_vector_clock.py tests/test_projections.py -v --tb=short
```

⛔ **STOP HERE IF ANY TEST FAILS** ⛔

**Debug checklist if tests fail**:
- [ ] Check asyncio.Lock is acquired before all dict/list modifications
- [ ] Check sequence_number assignment happens inside lock
- [ ] Check file writes are atomic (write to temp, then rename)
- [ ] Check vector clock merge uses `max()` not `min()`
- [ ] Check happens_before uses `all()` and `any()` correctly

---

## Phase 2: Task Orchestration 🎯

### 2.1 Priority System

**File**: `src/orchestrator/priority.py` (≤100 lines)
- [ ] Define `TaskPriority` IntEnum
- [ ] Implement `TaskPriorityAssigner`

**PASSING CRITERIA**:
- ✅ Priority values are integers (0, 10, 20, 30, 40)
- ✅ CRITICAL < HIGH < MEDIUM < LOW < BACKGROUND
- ✅ assign_priority() maps event types correctly
- ✅ should_preempt() returns True only if ≥20 priority difference

**FAILING CRITERIA**:
- ❌ Priority comparison broken (HIGH > CRITICAL)
- ❌ assign_priority() returns wrong priority for event
- ❌ should_preempt() allows 10-point difference (should be 20)

**EDGE CASES**:
1. **Unknown EventType** - should default to BACKGROUND
2. **None event** - should handle gracefully
3. **Event without event_type field** - should handle
4. **Negative priority** - should reject
5. **Priority > 100** - should handle or reject

---

### 2.2 Task Orchestrator

**File**: `src/orchestrator/task_orchestrator.py` (≤100 lines)
- [ ] Implement `TaskOrchestrator` class

**PASSING CRITERIA**:
- ✅ Queue accepts tasks until maxsize (100) reached
- ✅ 101st task blocks until queue has space
- ✅ Semaphore limits to max_concurrent (5) simultaneous tasks
- ✅ Priority ordering: CRITICAL tasks execute before BACKGROUND
- ✅ Workers process tasks from queue continuously
- ✅ Timeout cancels long-running tasks
- ✅ shutdown() cancels all pending and active tasks

**FAILING CRITERIA**:
- ❌ Queue accepts 101+ tasks without blocking
- ❌ More than max_concurrent tasks run simultaneously
- ❌ Lower priority task executes before higher priority
- ❌ Workers stop processing queue
- ❌ Timeout doesn't cancel task
- ❌ shutdown() leaves tasks running

**EDGE CASES**:
1. **submit_task() with queue full** - should block until space available
2. **Worker crash** - should restart worker or handle gracefully
3. **Task raises exception** - should log and continue, not crash worker
4. **Task with timeout=0** - should cancel immediately
5. **submit_task() during shutdown** - should reject new tasks
6. **Circular task dependencies** - should detect or handle
7. **Task that never yields** - should timeout
8. **1000 tasks submitted rapidly** - should handle (100 queued, rest block)
9. **get_queue_stats() during high load** - should not block
10. **Duplicate task_id** - should handle or reject

**CRITICAL INTEGRATION**: Must handle existing global StateManager without race conditions!

---

### 2.3 Backpressure Monitoring

**File**: `src/orchestrator/backpressure.py` (≤100 lines)
- [ ] Implement `BackpressureMonitor` class

**PASSING CRITERIA**:
- ✅ Alerts when queue is 80% full
- ✅ CRITICAL alert when queue is 100% full
- ✅ No false positives (alerting when queue <80%)

**FAILING CRITERIA**:
- ❌ No alert when queue 90% full
- ❌ Alert spam (multiple alerts per second)
- ❌ Crash when queue stats unavailable

**EDGE CASES**:
1. **Queue oscillating at 79-81%** - should debounce alerts
2. **Rapid queue drain** - should clear alert quickly
3. **Multiple orchestrators** - each should monitor independently

### 🧪 TEST GATE 2: Task Orchestration Tests

**File**: `tests/test_task_orchestrator.py` (≤100 lines)

```python
# Test 1: Priority ordering
✅ PASS: Submit [LOW, CRITICAL, HIGH] → executes in order [CRITICAL, HIGH, LOW]
❌ FAIL: Wrong execution order

# Test 2: Max concurrent limit
✅ PASS: Start 10 long tasks → max 5 run simultaneously
❌ FAIL: 6+ tasks run simultaneously

# Test 3: Backpressure (bounded queue)
✅ PASS: Submit 105 tasks → first 100 queue, last 5 block
✅ PASS: After 1 completes, blocked task enters queue
❌ FAIL: All 105 tasks enter queue immediately

# Test 4: Worker pool
✅ PASS: 3 workers continuously process queue
✅ PASS: 1 worker crash → other 2 continue
❌ FAIL: Workers stop processing

# Test 5: Timeout enforcement
✅ PASS: Task with timeout=1s running 2s → cancelled at 1s
❌ FAIL: Task runs beyond timeout

# Test 6: Graceful shutdown
✅ PASS: shutdown() cancels 20 queued + 5 active tasks
✅ PASS: All tasks receive CancelledError
❌ FAIL: Tasks left running after shutdown
```

**File**: `tests/test_priority_assignment.py` (≤100 lines)

```python
# Test 1: Priority mapping
✅ PASS: USER_INTERVENTION → CRITICAL (0)
✅ PASS: CODE_GENERATION → HIGH (10)
✅ PASS: DEAD_CODE_ANALYSIS → LOW (30)
❌ FAIL: Wrong priority assigned

# Test 2: Preemption logic
✅ PASS: CRITICAL (0) should_preempt MEDIUM (20) → True
✅ PASS: HIGH (10) should_preempt MEDIUM (20) → False (only 10 diff)
❌ FAIL: Preemption logic incorrect
```

**Run Tests**:
```bash
pytest tests/test_task_orchestrator.py tests/test_priority_assignment.py -v -s
```

⛔ **STOP HERE IF ANY TEST FAILS** ⛔

**Debug checklist**:
- [ ] Check PriorityQueue correctly orders by priority (lower = higher)
- [ ] Check Semaphore(5) enforces max concurrent
- [ ] Check asyncio.Queue(maxsize=100) blocks on 101st put()
- [ ] Check workers use `while True` loop
- [ ] Check timeout uses asyncio.wait_for()

---

## Phase 3: Context Management for Small LLMs 🧠

### 3.1 Context Manager

**File**: `src/context/context_manager.py` (≤100 lines)
- [ ] Implement `ContextManager` class

**PASSING CRITERIA**:
- ✅ Token estimate within 20% of actual (chars/4 ± 20%)
- ✅ Routes to larger model when >80% of context limit
- ✅ 4-layer context structure maintained
- ✅ Cached prompts reused (not regenerated)

**FAILING CRITERIA**:
- ❌ Token estimate off by >30%
- ❌ Context exceeds model limit (causes LLM error)
- ❌ Routing to larger model fails
- ❌ Cache misses when it should hit

**EDGE CASES**:
1. **Event with 50K chars** - should trigger model routing
2. **mistral:7b at 7.5K tokens** - should route to qwen3:8b
3. **qwen3:8b at 30K tokens** - should route to claude (or reject)
4. **Unicode/emoji heavy text** - token estimate should handle
5. **Empty event history** - should still build valid context
6. **Very long system prompt** (5K tokens) - should include in estimate
7. **Cache warm, then clear** - should regenerate correctly

---

### 3.2 Event Summarizer

**File**: `src/context/event_summarizer.py` (≤100 lines)
- [ ] Implement `EventSummarizer` class

**PASSING CRITERIA**:
- ✅ Compression achieves ≥5x token reduction
- ✅ Summary includes key statistics (module count, iteration count)
- ✅ Recent events (last 5) kept in full detail
- ✅ Older events compressed to 1-line summaries

**FAILING CRITERIA**:
- ❌ Compression <3x (not effective enough)
- ❌ Summary missing critical info (current version, status)
- ❌ Recent events lost or corrupted

**EDGE CASES**:
1. **keep_recent=5 but only 3 events** - should keep all 3
2. **1000 old events** - compression should still be fast (<100ms)
3. **Events with large data fields** - should truncate data in compression
4. **No events** - should return minimal summary, not error

---

### 3.3 System Prompt Cache

**File**: `src/context/prompt_cache.py` (≤100 lines)
- [ ] Implement `SystemPromptCache` class

**PASSING CRITERIA**:
- ✅ First call generates prompt (cache miss)
- ✅ Second call reuses prompt (cache hit)
- ✅ clear_cache() invalidates all entries
- ✅ Different event_types have different prompts

**FAILING CRITERIA**:
- ❌ Cache always misses (regenerates every time)
- ❌ Cache returns wrong prompt for event_type
- ❌ clear_cache() doesn't actually clear

**EDGE CASES**:
1. **Unknown event_type** - should generate generic prompt
2. **Cache with 100 entries** - should handle (no size limit)
3. **Prompt generation fails** - should retry or use fallback

---

### 3.4 Relevance Filter

**File**: `src/context/relevance_filter.py` (≤100 lines)
- [ ] Implement `RelevanceFilter` class

**PASSING CRITERIA**:
- ✅ Returns ≤limit events
- ✅ Events in chronological order
- ✅ Filters by: same module, same version, causal chain
- ✅ Empty result if no relevant events

**FAILING CRITERIA**:
- ❌ Returns >limit events
- ❌ Events out of chronological order
- ❌ Includes irrelevant events (wrong module/version)

**EDGE CASES**:
1. **limit=10 but only 3 relevant events** - return 3
2. **All events irrelevant** - return []
3. **Causation chain broken** - should still return what's available
4. **Events from multiple tasks mixed** - should filter correctly

### 🧪 TEST GATE 3: Context Management Tests

**File**: `tests/test_context_manager.py` (≤100 lines)

```python
# Test 1: 4-layer context
✅ PASS: Context has [system_prompt, state_summary, compressed_events, current_event]
❌ FAIL: Missing layer or wrong order

# Test 2: Token estimation
✅ PASS: 10K chars → ~2500 tokens estimate (±20%)
❌ FAIL: Estimate off by >30%

# Test 3: Model routing
✅ PASS: mistral:7b at 7K tokens → routes to qwen3:8b
✅ PASS: qwen3:8b at 28K tokens → routes to larger model
❌ FAIL: Doesn't route, or routes at wrong threshold

# Test 4: Cache effectiveness
✅ PASS: Same event_type called twice → prompt identical, not regenerated
❌ FAIL: Cache miss on second call
```

**File**: `tests/test_event_summarizer.py` (≤100 lines)

```python
# Test 1: Compression ratio
✅ PASS: 50 events (10K tokens) → summary (1.5K tokens) = 6.6x compression
❌ FAIL: Compression <3x

# Test 2: keep_recent
✅ PASS: 20 events, keep_recent=5 → 5 full + 15 compressed
❌ FAIL: Wrong number kept full, or order wrong

# Test 3: Summary content
✅ PASS: Summary includes module count, iteration count, current version
❌ FAIL: Missing critical statistics
```

**File**: `tests/test_relevance_filter.py` (≤100 lines)

```python
# Test 1: Limit enforcement
✅ PASS: 100 events, limit=10 → returns exactly 10
❌ FAIL: Returns ≠10

# Test 2: Relevance filtering
✅ PASS: 50 events, same module → returns only same-module events
❌ FAIL: Returns events from other modules

# Test 3: Chronological order
✅ PASS: Events returned in sequence_number order
❌ FAIL: Out of order
```

**Run Tests**:
```bash
pytest tests/test_context_manager.py tests/test_event_summarizer.py tests/test_relevance_filter.py -v
```

⛔ **STOP HERE IF ANY TEST FAILS** ⛔

---

## Phase 4: FastAPI + WebSocket Layer 🌐

### 4.1 Pydantic Models

**File**: `src/api/models/requests.py` (≤100 lines)
- [ ] Define `TaskRequest`, `InterventionRequest` models

**PASSING CRITERIA**:
- ✅ TaskRequest.prompt is non-empty string
- ✅ TaskRequest.answers is list (can be empty)
- ✅ Pydantic validation rejects invalid data

**FAILING CRITERIA**:
- ❌ Accepts empty prompt ""
- ❌ Accepts answers as non-list
- ❌ Validation doesn't catch malformed data

**EDGE CASES**:
1. **prompt with 100K chars** - should handle or reject with clear error
2. **answers with 1000 items** - should handle
3. **Unicode/emoji in prompt** - should handle
4. **priority="CRITICAL"** (string) - should convert to TaskPriority enum
5. **priority="INVALID"** - should reject with error

**File**: `src/api/models/responses.py` (≤100 lines)
- [ ] Define response models

**PASSING CRITERIA**:
- ✅ All required fields present
- ✅ Serialization to JSON works
- ✅ websocket_url format is valid (ws://host:port/ws/task_id)

**FAILING CRITERIA**:
- ❌ Missing required fields
- ❌ Non-serializable fields
- ❌ Invalid URL format

**EDGE CASES**:
1. **task_id with special chars** - URL encoding should handle
2. **Very long task_id** (1000 chars) - should handle or reject
3. **None values** - should serialize as null

---

### 4.2 WebSocket Manager

**File**: `src/api/websocket_manager.py` (≤100 lines)
- [ ] Implement `WebSocketManager` class

**PASSING CRITERIA**:
- ✅ connect() accepts WebSocket and stores in dict
- ✅ Multiple clients can connect to same task_id
- ✅ broadcast_to_task() sends to all connected clients
- ✅ disconnect() removes client and cleans up empty lists
- ✅ Failed sends don't crash other broadcasts

**FAILING CRITERIA**:
- ❌ Only 1 client per task_id allowed
- ❌ broadcast fails if one client disconnected
- ❌ Memory leak (disconnected clients not removed)

**EDGE CASES**:
1. **Client connects, then immediately disconnects** - should handle
2. **broadcast to task_id with no clients** - should be no-op, not error
3. **Client connection fails during accept** - should handle gracefully
4. **100 clients for same task_id** - should broadcast to all efficiently
5. **Client receives message, then disconnects** - no error
6. **WebSocket send raises exception** - should catch and remove client
7. **Concurrent connect/disconnect** - should be thread-safe

**CRITICAL**: Must integrate with existing `StreamingWorkflowOrchestrator`!

---

### 4.3 Task Manager (FastAPI Integration)

**File**: `src/api/task_manager.py` (≤100 lines)
- [ ] Implement `TaskManager` class

**PASSING CRITERIA**:
- ✅ start_task() creates asyncio.Task and stores in dict
- ✅ Callback cleanup when task completes
- ✅ cancel_task() cancels and awaits task
- ✅ get_task_status() queries event store (not in-memory state)
- ✅ shutdown_all() cancels all tasks

**FAILING CRITERIA**:
- ❌ start_task() blocks until task completes
- ❌ Completed tasks not removed (memory leak)
- ❌ cancel_task() doesn't await (leaves zombie tasks)
- ❌ shutdown_all() misses some tasks

**EDGE CASES**:
1. **Task raises exception** - callback should still fire
2. **cancel_task() on completed task** - should handle gracefully
3. **Double cancel** - should be idempotent
4. **get_task_status() for unknown task_id** - should return error, not crash
5. **start_task() with duplicate task_id** - should reject or overwrite

**CRITICAL INTEGRATION**: Must work with existing `StateManager` global dict!

---

### 4.4-4.6 Endpoints

**Files**: `src/api/endpoints/*.py` (≤100 lines each)
- [ ] health.py, tasks.py, websocket.py

**PASSING CRITERIA**:
- ✅ POST /tasks returns 200 with task_id
- ✅ GET /tasks/{task_id} returns current status
- ✅ WebSocket /ws/{task_id} accepts connection
- ✅ WebSocket receives versioned messages
- ✅ GET /health returns 200 when healthy

**FAILING CRITERIA**:
- ❌ POST /tasks with invalid data returns 200 (should be 400)
- ❌ GET /tasks/nonexistent returns 200 (should be 404)
- ❌ WebSocket doesn't send version in messages
- ❌ Health check returns 200 when Ollama down (should be 503)

**EDGE CASES**:
1. **POST /tasks during high load** - should queue or reject gracefully
2. **GET /tasks/{id} for task that hasn't started** - should return status "created"
3. **WebSocket connect before task starts** - should wait or error clearly
4. **WebSocket receives out-of-order messages** - client should sort by sequence
5. **Health check during DSPy reconfiguration** - should handle

---

### 4.7 Versioned State Manager

**File**: `src/api/versioned_state.py` (≤100 lines)
- [ ] Implement `VersionedState` class

**PASSING CRITERIA**:
- ✅ update() rejects version ≤ current_version
- ✅ update() is thread-safe (asyncio.Lock)
- ✅ get_current_version() returns latest version
- ✅ States indexed by version number

**FAILING CRITERIA**:
- ❌ Accepts stale update (v2 after v3)
- ❌ Race condition on concurrent updates
- ❌ Version collision (two states with same version)

**EDGE CASES**:
1. **Update v1, v3 (skip v2)** - should accept (versions can have gaps)
2. **Concurrent update of v2 from two sources** - only one should succeed
3. **Update with v=0** - should accept as initial
4. **get_current_version() with no updates** - should return 0
5. **Very large version number** (2^31) - should handle

### 🧪 TEST GATE 4: FastAPI Tests

**File**: `tests/test_api_models.py` (≤100 lines)

```python
# Test 1: Pydantic validation
✅ PASS: TaskRequest(prompt="test") → valid
❌ FAIL: TaskRequest(prompt="") → ValidationError not raised

# Test 2: Serialization
✅ PASS: TaskResponse(...).dict() → valid JSON dict
❌ FAIL: Non-serializable fields cause error
```

**File**: `tests/test_websocket_manager.py` (≤100 lines)

```python
# Test 1: Multiple clients
✅ PASS: 3 clients connect to task-A → all 3 receive broadcast
❌ FAIL: Only 1 receives, or broadcast fails

# Test 2: Cleanup
✅ PASS: Client disconnects → removed from active_connections
❌ FAIL: Client lingers (memory leak)

# Test 3: Failed send
✅ PASS: 1 of 3 clients fails → other 2 still receive message
❌ FAIL: All broadcasts fail due to 1 bad client
```

**File**: `tests/test_task_manager.py` (≤100 lines)

```python
# Test 1: Task creation
✅ PASS: start_task() creates asyncio.Task
✅ PASS: Task ID in active_tasks dict
❌ FAIL: Task not tracked

# Test 2: Cancellation
✅ PASS: cancel_task() cancels and removes from dict
❌ FAIL: Task still running, or not removed

# Test 3: Callback cleanup
✅ PASS: Task completes → callback fires → removed from dict
❌ FAIL: Callback doesn't fire, task lingers
```

**File**: `tests/test_endpoints.py` (≤100 lines)

```python
# Test 1: POST /tasks
✅ PASS: Valid request → 200, returns task_id
❌ FAIL: Invalid request → 200 (should be 400)

# Test 2: GET /tasks/{id}
✅ PASS: Existing task → 200, returns status
✅ PASS: Nonexistent task → 404
❌ FAIL: 404 returns 200, or 200 returns 500

# Test 3: GET /health
✅ PASS: DSPy configured, Ollama reachable → 200
❌ FAIL: Returns 200 when Ollama down
```

**File**: `tests/test_websocket_endpoint.py` (≤100 lines)

```python
# Test 1: Connection
✅ PASS: WS /ws/task-A connects successfully
❌ FAIL: Connection refused or timeout

# Test 2: Message versioning
✅ PASS: All messages include version and sequence fields
❌ FAIL: Missing version or sequence

# Test 3: Stale update rejection
✅ PASS: Client at v3 receives v2 message → ignores
❌ FAIL: Client processes stale message
```

**Run Tests**:
```bash
pytest tests/test_api_models.py tests/test_websocket_manager.py tests/test_task_manager.py tests/test_endpoints.py tests/test_websocket_endpoint.py -v
```

⛔ **STOP HERE IF ANY TEST FAILS** ⛔

---

## Phase 5: Hybrid FastAPI + FastMCP Main App 🔗

### 5.1 Main FastAPI App

**File**: `src/api/main.py` (≤100 lines)

**PASSING CRITERIA**:
- ✅ Lifespan startup configures DSPy successfully
- ✅ Orchestrator workers start (3 workers running)
- ✅ All routers mounted (/health, /tasks, /ws)
- ✅ FastMCP mounted at /mcp/
- ✅ app.state contains all managers
- ✅ Lifespan shutdown cancels all tasks

**FAILING CRITERIA**:
- ❌ DSPy configuration fails, app still starts
- ❌ Workers don't start
- ❌ FastMCP not accessible at /mcp/
- ❌ Shutdown doesn't clean up tasks

**EDGE CASES**:
1. **Ollama not running at startup** - should error clearly, not start
2. **Port 9876 already in use** - should error clearly
3. **Shutdown during active task** - should wait for cancellation
4. **Restart after crash** - should reinitialize cleanly

---

### 5.2 Modify Existing MCP Server

**File**: `src/mcp/fastmcp_server.py` (MODIFY)

**CHANGES**:
```python
# Add at end (line 151+):
def get_asgi_app():
    """Export FastMCP as ASGI app for mounting"""
    return mcp.get_asgi_app()
```

**PASSING CRITERIA**:
- ✅ get_asgi_app() returns valid ASGI app
- ✅ All existing tools still work via stdio
- ✅ Mounted app works via HTTP at /mcp/

**FAILING CRITERIA**:
- ❌ get_asgi_app() returns None or errors
- ❌ stdio mode broken
- ❌ HTTP mode broken

**EDGE CASES**:
1. **stdio and HTTP used simultaneously** - should work independently
2. **global state shared** - should be thread-safe

---

### 5.3 Update Server Runner

**File**: `src/mcp/server_runner.py` (MODIFY)

**CHANGES**:
- Add --fastapi flag
- If --fastapi: `subprocess.run(["uvicorn", "src.api.main:app", ...])`

**PASSING CRITERIA**:
- ✅ --fastapi starts hybrid server on port 9876
- ✅ --http still works (FastMCP HTTP only)
- ✅ Default (no flags) still works (stdio)

**FAILING CRITERIA**:
- ❌ --fastapi doesn't start server
- ❌ Breaking existing modes

### 🧪 TEST GATE 5: Integration Tests

**File**: `tests/test_hybrid_integration.py` (≤100 lines)

```python
# Test 1: FastAPI endpoints work
✅ PASS: POST /tasks returns 200
❌ FAIL: 404 or 500

# Test 2: FastMCP tools work
✅ PASS: POST /mcp/tools/call → start_coding_task works
❌ FAIL: 404 or tool doesn't execute

# Test 3: Shared state
✅ PASS: Task created via REST visible via MCP get_task_status
❌ FAIL: State not shared

# Test 4: Lifespan
✅ PASS: Startup configures DSPy, logs confirm
✅ PASS: Shutdown cancels tasks, logs confirm
❌ FAIL: Startup/shutdown errors
```

**File**: `tests/test_network_access.py` (≤100 lines)

```python
# Test 1: 0.0.0.0 binding
✅ PASS: Server binds to 0.0.0.0:9876
✅ PASS: Accessible from 127.0.0.1
❌ FAIL: Only localhost, or port conflict

# Test 2: WebSocket from network
✅ PASS: WS connection from external IP works
❌ FAIL: Connection refused

# Test 3: MCP endpoint
✅ PASS: http://localhost:9876/mcp/ returns MCP info
❌ FAIL: 404 or error
```

**Run Tests**:
```bash
pytest tests/test_hybrid_integration.py tests/test_network_access.py -v
```

⛔ **STOP HERE IF ANY TEST FAILS** ⛔

---

## Phase 6: Workflow Integration 🔄

### 6.1 Modify Workflow Orchestrator

**File**: `src/orchestrator/workflow.py` (MODIFY)

**CRITICAL INTEGRATION NOTES**:
- Existing WorkflowOrchestrator (line 30-166)
- Existing StreamingWorkflowOrchestrator (in streaming.py)
- Must add event emission WITHOUT breaking existing functionality

**PASSING CRITERIA**:
- ✅ Existing workflow still works without WebSocket manager
- ✅ With WebSocket manager, events emitted at each stage
- ✅ Events stored in EventStore
- ✅ Backward compatible (Optional parameters)

**FAILING CRITERIA**:
- ❌ Workflow breaks if event_store=None
- ❌ Events not emitted
- ❌ EventStore not populated

**EDGE CASES**:
1. **websocket_manager=None** - should work (for backward compat)
2. **event_store=None** - should work (for backward compat)
3. **Both provided** - should emit events to both
4. **WebSocket broadcast fails** - should continue workflow
5. **EventStore append fails** - should log error, continue workflow

**INTEGRATION WITH EXISTING EVENT SYSTEM**:
- Existing `WorkflowEvent` in orchestrator/events.py
- New `Event` in events/event.py
- Must coexist! Perhaps emit both temporarily.

---

### 6.2 Modify State Manager

**File**: `src/orchestrator/state.py` (MODIFY)

**CHANGES**:
```python
# Line 23+ in TaskState.__init__:
self.asyncio_task: Optional[asyncio.Task] = None
self.websocket_connections: List[WebSocket] = []
self.code_version: int = 0
```

**PASSING CRITERIA**:
- ✅ New fields added
- ✅ Existing fields unchanged
- ✅ Backward compatible (old code still works)

**FAILING CRITERIA**:
- ❌ Breaking changes to existing fields
- ❌ Import errors

**CRITICAL**: StateManager uses dict, NOT thread-safe! Must add locks or use async-safe structure.

### 🧪 TEST GATE 6: Workflow Integration Tests

**File**: `tests/test_workflow_events.py` (≤100 lines)

```python
# Test 1: Event emission
✅ PASS: Workflow emits TASK_STARTED, PLANNING_COMPLETE, MODULE_STARTED, etc.
❌ FAIL: Events missing or out of order

# Test 2: Version increment
✅ PASS: CODE_GENERATED events have version [1,2,3...]
❌ FAIL: Version doesn't increment, or skips numbers

# Test 3: WebSocket broadcast
✅ PASS: Connected client receives all events
❌ FAIL: Client misses events

# Test 4: EventStore population
✅ PASS: EventStore contains all workflow events after completion
❌ FAIL: Events missing or corrupted
```

**File**: `tests/test_end_to_end.py` (≤100 lines)

```python
# Test 1: Full workflow
✅ PASS: POST /tasks → workflow completes → GET /tasks/{id} shows "completed"
❌ FAIL: Workflow hangs, errors, or status wrong

# Test 2: WebSocket receives all events
✅ PASS: Client receives [TASK_STARTED ... TASK_COMPLETE] in order
❌ FAIL: Events out of order, or missing

# Test 3: Version monotonicity
✅ PASS: All events have increasing version numbers
❌ FAIL: Version decreases or repeats

# Test 4: Event history
✅ PASS: EventStore.get_events(task_id) returns complete history
❌ FAIL: History incomplete

# Test 5: Context manager used
✅ PASS: DSPy calls use context from ContextManager
❌ FAIL: Context not used, or exceeds model limits
```

**Run Tests**:
```bash
pytest tests/test_workflow_events.py tests/test_end_to_end.py -v --tb=long
```

⛔ **STOP HERE IF ANY TEST FAILS** ⛔

---

## Summary: Critical Edge Cases Across All Phases

### Thread Safety Issues (HIGH PRIORITY):
1. StateManager.tasks - concurrent access
2. InterventionManager.interventions - concurrent access
3. EventStore.sequence_counter - must use lock
4. AsyncLogger.logs - list append not atomic
5. WebSocketManager.active_connections - dict modification

### Data Validation Issues:
6. task_id - never validated (could be empty, None, malicious)
7. prompt - could be empty string ""
8. code_version - could be negative
9. event.data - could contain non-serializable objects
10. module_spec.dependencies - could be malformed

### Integration Gotchas:
11. Two event systems (WorkflowEvent vs Event) - must coexist
12. StreamingWorkflowOrchestrator already exists - must integrate
13. Global state managers - must be made async-safe
14. TestRunner subprocess.run - blocks event loop, not truly async
15. AsyncLogger file writes - not atomic, race condition

### Performance Edge Cases:
16. 1M events in EventStore - projection should be <5s
17. 100 concurrent WebSocket clients - broadcast should be <100ms
18. Queue with 100 tasks - submit should block, not error
19. Very long context (50K tokens) - should route to larger model
20. 1000 task_ids in StateManager - lookup should be O(1)

### Error Handling:
21. Ollama not running - should fail fast with clear error
22. Disk full during event persist - should handle gracefully
23. WebSocket client disconnects mid-broadcast - should continue
24. DSPy returns malformed result - should validate and retry
25. Test timeout during high load - should cancel gracefully

---

## Final Pre-Implementation Checklist

Before starting Phase 1:
- [ ] Read this entire document
- [ ] Understand all edge cases
- [ ] Understand integration with existing code (events.py, streaming.py, state.py)
- [ ] Have pytest installed and working
- [ ] Have uvicorn installed (pip install uvicorn[standard])
- [ ] Ollama running (http://localhost:11434)
- [ ] Test existing workflow works (python -m src.mcp.server_runner)

**Current Status**: ⏸️ Awaiting user approval and write access to `src/`
