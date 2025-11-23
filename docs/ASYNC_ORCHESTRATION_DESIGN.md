# Async Task Orchestration & State Consistency Design

**Critical Problems Identified**:
1. Event ordering (pre-correction vs post-correction reports)
2. Source of truth under async latency
3. Task overflow prevention
4. Context window management for small LLMs
5. Latency-induced truth divergence

---

## Problem 1: Event Ordering & Causality

### The Scenario

```
Timeline:
T0: Code generated (version V1)
T1: Correction process starts
T2: Bug report arrives (about V1)
T3: Correction completes (version V2)
T4: Bug report processed

Question: Is bug report about V1 or V2?
```

### Research-Backed Solution: Event Sourcing + Vector Clocks

**Source**: [Event Sourcing with FastAPI](https://dev.to/markoulis/how-i-learned-to-stop-worrying-and-love-raw-events-event-sourcing-cqrs-with-fastapi-and-celery-477e)

#### Architecture: Event Store as Source of Truth

```python
# Event = immutable fact that happened

@dataclass(frozen=True)
class Event:
    """Immutable event - source of truth"""
    event_id: str              # UUID
    task_id: str
    event_type: EventType
    timestamp: datetime
    sequence_number: int       # Lamport clock
    vector_clock: Dict[str, int]  # Causality tracking
    causation_id: Optional[str]   # Which event caused this
    correlation_id: str           # Transaction ID
    data: dict
    code_version: int             # CRITICAL: version tracking

# Examples:
Event(
    event_id="evt-001",
    task_id="task-abc",
    event_type="CODE_GENERATED",
    sequence_number=1,
    vector_clock={"generator": 1},
    code_version=1,  # V1
    data={"code": "...", "hash": "abc123"}
)

Event(
    event_id="evt-002",
    task_id="task-abc",
    event_type="CORRECTION_STARTED",
    sequence_number=2,
    vector_clock={"generator": 1, "corrector": 1},
    causation_id="evt-001",  # Caused by CODE_GENERATED
    code_version=1,  # Correcting V1
    data={"target_version": 1}
)

Event(
    event_id="evt-003",
    task_id="task-abc",
    event_type="BUG_REPORT_RECEIVED",
    sequence_number=3,
    vector_clock={"generator": 1, "corrector": 1, "tester": 1},
    causation_id="evt-001",  # About V1
    code_version=1,  # Report about V1
    data={"bug": "..."}
)

Event(
    event_id="evt-004",
    task_id="task-abc",
    event_type="CORRECTION_COMPLETED",
    sequence_number=4,
    vector_clock={"generator": 1, "corrector": 2, "tester": 1},
    causation_id="evt-002",  # Completes correction
    code_version=2,  # Now V2
    data={"code": "...", "hash": "xyz789"}
)
```

#### Vector Clocks for Causality

**Source**: [Vector Clocks Explanation](https://medium.com/big-data-processing/vector-clocks-182007060193)

```python
class VectorClock:
    """Track causality between events"""

    def __init__(self):
        self.clock: Dict[str, int] = {}

    def tick(self, process_id: str) -> Dict[str, int]:
        """Increment clock for this process"""
        self.clock[process_id] = self.clock.get(process_id, 0) + 1
        return self.clock.copy()

    def merge(self, other: Dict[str, int]) -> None:
        """Merge with received clock (take max of each)"""
        for process_id, timestamp in other.items():
            self.clock[process_id] = max(
                self.clock.get(process_id, 0),
                timestamp
            )

    def happens_before(
        self,
        clock1: Dict[str, int],
        clock2: Dict[str, int]
    ) -> bool:
        """Check if event1 causally precedes event2"""
        # clock1 < clock2 if all values in clock1 <= clock2
        # and at least one is strictly less
        return (
            all(clock1.get(k, 0) <= clock2.get(k, 0) for k in clock1)
            and any(clock1.get(k, 0) < clock2.get(k, 0) for k in clock2)
        )

    def concurrent(
        self,
        clock1: Dict[str, int],
        clock2: Dict[str, int]
    ) -> bool:
        """Check if events are concurrent (no causal relationship)"""
        return (
            not self.happens_before(clock1, clock2)
            and not self.happens_before(clock2, clock1)
        )
```

#### Determining Report Validity

```python
class EventOrdering:
    """Determine if bug report is pre or post correction"""

    def is_report_valid_for_current_code(
        self,
        bug_report_event: Event,
        correction_event: Event
    ) -> bool:
        """
        Check if bug report is about current code version.

        Returns:
            True if report is about current version (actionable)
            False if report is stale (ignore)
        """
        # Method 1: Version number
        if bug_report_event.code_version != correction_event.code_version:
            return False  # Report about old version

        # Method 2: Vector clock causality
        if self.happens_before(
            bug_report_event.vector_clock,
            correction_event.vector_clock
        ):
            return False  # Report happened before correction

        # Method 3: Code hash verification
        if bug_report_event.data.get("code_hash") != \
           correction_event.data.get("code_hash"):
            return False  # Different code

        return True  # Report is current
```

---

## Problem 2: Source of Truth

### Research Findings

**Source**: [Event Sourcing as Source of Truth](https://beyondplm.com/2025/03/18/plm-evolution-single-source-of-truth-and-eventual-consistency/)

**Key Insight**: "In event-driven architectures, the **event becomes the single source of truth**."

### Architecture: Event Store Pattern

```python
class EventStore:
    """
    Append-only event log - THE source of truth.

    All state is derived from events by replaying them.
    """

    def __init__(self):
        self.events: List[Event] = []  # In production: database
        self.sequence_counter = 0
        self.lock = asyncio.Lock()

    async def append(self, event: Event) -> None:
        """Append event (only way to change state)"""
        async with self.lock:
            self.sequence_counter += 1
            event.sequence_number = self.sequence_counter
            self.events.append(event)

            # Persist to disk/database
            await self._persist(event)

    async def get_events(
        self,
        task_id: str,
        after_sequence: int = 0
    ) -> List[Event]:
        """Get events for task after sequence number"""
        return [
            e for e in self.events
            if e.task_id == task_id
            and e.sequence_number > after_sequence
        ]

    async def rebuild_state(self, task_id: str) -> TaskState:
        """Rebuild current state from events (projection)"""
        events = await self.get_events(task_id)

        state = TaskState(task_id=task_id)
        for event in events:
            state = self._apply_event(state, event)

        return state

    def _apply_event(self, state: TaskState, event: Event) -> TaskState:
        """State transition based on event"""
        match event.event_type:
            case "CODE_GENERATED":
                state.code = event.data["code"]
                state.code_version = event.code_version
                state.code_hash = event.data["hash"]

            case "BUG_REPORT_RECEIVED":
                # Only apply if for current version
                if event.code_version == state.code_version:
                    state.pending_bugs.append(event.data["bug"])

            case "CORRECTION_COMPLETED":
                state.code = event.data["code"]
                state.code_version = event.code_version
                state.code_hash = event.data["hash"]
                state.pending_bugs.clear()  # Fixed

        return state
```

### Why This Works

**Source**: [Eventual Consistency - Wikipedia](https://en.wikipedia.org/wiki/Eventual_consistency)

1. **Events are facts** - immutable, timestamped, versioned
2. **State is derived** - current state = projection from events
3. **Time-travel debugging** - replay events to any point
4. **Conflict resolution** - vector clocks determine causality

---

## Problem 3: Async Task Orchestration

### Research Findings

**Source**: [CQRS with FastAPI](https://www.pysquad.com/blogs/cqrs-and-event-sourcing-with-fastapi-building-even)

**Key Pattern**: Command-Query Responsibility Segregation

```
Commands (Write)           Queries (Read)
    ↓                          ↑
Event Store            Materialized Views
(Source of Truth)      (Eventually consistent)
```

### Architecture: Task Hierarchy with Priority Queue

**Source**: [Backpressure Management](https://tech-champion.com/programming/python-programming/manage-async-i-o-backpressure-using-bounded-queues-and-timeouts/)

```python
from enum import IntEnum
from asyncio import PriorityQueue, Semaphore

class TaskPriority(IntEnum):
    """Priority levels (lower number = higher priority)"""
    CRITICAL = 0      # User intervention, bug fixes
    HIGH = 10         # Code generation main path
    MEDIUM = 20       # Testing, refinement
    LOW = 30          # Logging, metrics
    BACKGROUND = 40   # Cleanup, analysis

@dataclass(order=True)
class PrioritizedTask:
    """Task with priority for queue"""
    priority: int
    sequence: int              # Tie-breaker (FIFO within priority)
    task_id: str = field(compare=False)
    coro: Coroutine = field(compare=False)
    timeout: float = field(compare=False, default=300.0)

class TaskOrchestrator:
    """Manages async task execution with priority and backpressure"""

    def __init__(
        self,
        max_concurrent: int = 5,   # Prevent overflow
        max_queue_size: int = 100  # Bounded queue
    ):
        self.task_queue = PriorityQueue(maxsize=max_queue_size)
        self.semaphore = Semaphore(max_concurrent)
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.sequence_counter = 0
        self.workers: List[asyncio.Task] = []

    async def start_workers(self, num_workers: int = 3):
        """Start worker pool"""
        for i in range(num_workers):
            worker = asyncio.create_task(self._worker(i))
            self.workers.append(worker)

    async def submit_task(
        self,
        coro: Coroutine,
        task_id: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        timeout: float = 300.0
    ) -> None:
        """
        Submit task with priority.

        Blocks if queue is full (backpressure).
        """
        self.sequence_counter += 1

        prioritized = PrioritizedTask(
            priority=priority,
            sequence=self.sequence_counter,
            task_id=task_id,
            coro=coro,
            timeout=timeout
        )

        # Blocks if queue full (backpressure!)
        await self.task_queue.put(prioritized)

    async def _worker(self, worker_id: int):
        """Worker that processes tasks from queue"""
        while True:
            # Get highest priority task
            prioritized: PrioritizedTask = await self.task_queue.get()

            # Acquire semaphore (max concurrent limit)
            async with self.semaphore:
                try:
                    # Execute with timeout
                    task = asyncio.create_task(prioritized.coro)
                    self.active_tasks[prioritized.task_id] = task

                    await asyncio.wait_for(task, timeout=prioritized.timeout)

                except asyncio.TimeoutError:
                    print(f"[Worker {worker_id}] Task {prioritized.task_id} timeout")
                    task.cancel()

                except Exception as e:
                    print(f"[Worker {worker_id}] Task {prioritized.task_id} failed: {e}")

                finally:
                    self.active_tasks.pop(prioritized.task_id, None)
                    self.task_queue.task_done()

    async def get_queue_stats(self) -> dict:
        """Monitor queue health"""
        return {
            "queue_size": self.task_queue.qsize(),
            "active_tasks": len(self.active_tasks),
            "max_queue_size": self.task_queue.maxsize,
            "queue_full": self.task_queue.full(),
            "backpressure_active": self.task_queue.full()
        }
```

### Backpressure Indicators

**Source**: [Backpressure Handling](https://softwarepatternslexicon.com/patterns-python/9/4/)

**Monitoring**:
```python
async def monitor_backpressure(orchestrator: TaskOrchestrator):
    """Alert on backpressure"""
    stats = await orchestrator.get_queue_stats()

    if stats["queue_size"] > stats["max_queue_size"] * 0.8:
        # Queue 80% full - WARNING
        print("⚠️  Backpressure building! Queue 80% full")

    if stats["backpressure_active"]:
        # Queue full - CRITICAL
        print("🚨 BACKPRESSURE ACTIVE! Queue full, blocking producers")
```

---

## Problem 4: Task Hierarchy Heuristics

### Priority Assignment Rules

```python
class TaskPriorityAssigner:
    """Assign priority based on task characteristics"""

    def assign_priority(self, event: Event) -> TaskPriority:
        """Determine priority from event"""

        # CRITICAL: User interventions, error recovery
        if event.event_type in [
            "USER_INTERVENTION",
            "CORRECTION_REQUESTED",
            "BUG_FIX_URGENT"
        ]:
            return TaskPriority.CRITICAL

        # HIGH: Main workflow path
        if event.event_type in [
            "CODE_GENERATION",
            "REQUIREMENT_GATHERING"
        ]:
            return TaskPriority.HIGH

        # MEDIUM: Testing, refinement
        if event.event_type in [
            "TEST_GENERATION",
            "CODE_REFINEMENT"
        ]:
            return TaskPriority.MEDIUM

        # LOW: Analysis, reporting
        if event.event_type in [
            "DEAD_CODE_ANALYSIS",
            "QUALITY_CHECK"
        ]:
            return TaskPriority.LOW

        # BACKGROUND: Cleanup, logging
        return TaskPriority.BACKGROUND

    def should_preempt(
        self,
        new_event: Event,
        current_task: PrioritizedTask
    ) -> bool:
        """Check if new event should interrupt current task"""
        new_priority = self.assign_priority(new_event)

        # Preempt if ≥2 levels higher priority
        return new_priority <= (current_task.priority - 20)
```

---

## Problem 5: Context Window Management for Small LLMs

### Research Findings

**Source**: [LLM Context Management](https://eval.16x.engineer/blog/llm-context-management-guide)

**Key Techniques**:
1. **Context Caching** - Cache tokens at 10x lower cost
2. **Hierarchical Caching** - Cache frequent prefixes
3. **Route to Appropriate Model** - Small tasks → small models

### Architecture: Smart Context Router

```python
class ContextManager:
    """Manage context for small LLMs (mistral:7b, qwen3:8b)"""

    def __init__(self):
        self.cache: Dict[str, str] = {}  # Token cache
        self.model_limits = {
            "mistral:7b": 8192,    # 8K context
            "qwen3:8b": 32768,     # 32K context
            "claude-sonnet": 200000  # 200K context (fallback)
        }

    async def prepare_context(
        self,
        event: Event,
        model: str = "mistral:7b"
    ) -> str:
        """
        Prepare minimal context for small LLM.

        Strategies:
        1. Event sourcing - only send necessary events
        2. Summarization - compress old events
        3. Caching - reuse common patterns
        """
        task_id = event.task_id

        # Get relevant events (not all!)
        relevant_events = await self._get_relevant_events(
            task_id,
            event.event_type,
            limit=10  # Last 10 relevant events
        )

        # Build minimal context
        context_parts = []

        # 1. Cached system prompt (reused, low cost)
        system_prompt = self._get_cached_system_prompt(event.event_type)
        context_parts.append(system_prompt)

        # 2. Current task state (from event projection)
        current_state = await self._get_current_state(task_id)
        context_parts.append(self._summarize_state(current_state))

        # 3. Recent events (compressed)
        for evt in relevant_events:
            context_parts.append(self._compress_event(evt))

        # 4. Current event (full detail)
        context_parts.append(self._format_event(event))

        full_context = "\n\n".join(context_parts)

        # Check size
        token_count = self._estimate_tokens(full_context)
        limit = self.model_limits[model]

        if token_count > limit * 0.8:
            # Context too large, fallback to larger model
            print(f"⚠️  Context ({token_count} tokens) near limit ({limit})")
            print("→ Routing to larger model (qwen3:8b or Claude)")
            return await self.prepare_context(event, model="qwen3:8b")

        return full_context

    async def _get_relevant_events(
        self,
        task_id: str,
        event_type: str,
        limit: int
    ) -> List[Event]:
        """
        Get only relevant events (not all events).

        Relevance heuristics:
        - Same module
        - Same code version
        - Recent (last N)
        - Causal chain (follows causation_id)
        """
        all_events = await event_store.get_events(task_id)

        # Filter by relevance
        relevant = []
        for event in reversed(all_events):  # Most recent first
            if self._is_relevant(event, event_type):
                relevant.append(event)

            if len(relevant) >= limit:
                break

        return list(reversed(relevant))  # Chronological order

    def _compress_event(self, event: Event) -> str:
        """
        Compress event to minimal tokens.

        Full event: 500 tokens
        Compressed: 50 tokens (10x reduction)
        """
        return (
            f"[{event.event_type} v{event.code_version}] "
            f"{event.data.get('summary', '')}"
        )

    def _get_cached_system_prompt(self, event_type: str) -> str:
        """
        Use cached system prompts.

        Cost: $0.02/1M cached tokens (10x cheaper)
        """
        cache_key = f"system_prompt_{event_type}"

        if cache_key not in self.cache:
            # First time: full cost
            self.cache[cache_key] = self._generate_system_prompt(event_type)

        # Subsequent calls: cached (10x cheaper)
        return self.cache[cache_key]
```

### Source of Truth for Small LLMs: Event Summary

```python
class EventSummarizer:
    """
    Compress event history for small LLMs.

    Instead of sending 50 events (10K tokens),
    send summary (500 tokens) + recent 5 events (2K tokens).
    """

    async def summarize_task_history(
        self,
        task_id: str,
        keep_recent: int = 5
    ) -> str:
        """Generate summary of task history"""
        events = await event_store.get_events(task_id)

        # Recent events: keep full detail
        recent = events[-keep_recent:]

        # Older events: summarize
        older = events[:-keep_recent]

        summary_parts = []

        # Summarize older events by phase
        summary_parts.append("Previous phases:")
        summary_parts.append(
            f"- Requirements: {self._count_by_type(older, 'REQUIREMENT')}"
        )
        summary_parts.append(
            f"- Planning: {self._count_by_type(older, 'PLANNING')}"
        )
        summary_parts.append(
            f"- Code generated: {self._count_by_type(older, 'CODE_GENERATED')} versions"
        )

        # Recent events: full detail
        summary_parts.append("\nRecent activity:")
        for event in recent:
            summary_parts.append(
                f"- [{event.event_type}] {event.data.get('summary', '')}"
            )

        return "\n".join(summary_parts)
```

---

## Problem 6: Latency & Truth Divergence

### The Problem

```
SSE/HTTP Latency: 100-500ms
LLM Inference: 2-10 seconds

Timeline:
T0: Code V1 generated
T1: (100ms later) WebSocket sends "V1 ready"
T2: (200ms later) Correction starts on V1
T3: (5s later) Correction completes → V2
T4: (100ms later) WebSocket sends "V2 ready"
T5: (100ms later) Client receives "V1 ready" (stale!)

Client thinks current version is V1, but it's actually V2!
```

### Solution: Version Monotonicity + Client Reconciliation

```python
class VersionedState:
    """State with version for consistency checking"""

    def __init__(self):
        self.current_version = 0
        self.states: Dict[int, TaskState] = {}
        self.lock = asyncio.Lock()

    async def update(self, new_state: TaskState, event: Event) -> int:
        """Update state, return new version"""
        async with self.lock:
            # Version must increase monotonically
            new_version = event.code_version

            if new_version <= self.current_version:
                # Stale update, reject
                print(f"⚠️  Rejecting stale update (v{new_version} ≤ v{self.current_version})")
                return self.current_version

            # Accept update
            self.current_version = new_version
            self.states[new_version] = new_state

            return new_version

class WebSocketMessage:
    """WebSocket message with version and timestamp"""
    type: str
    task_id: str
    version: int              # Code version
    sequence: int             # Event sequence number
    timestamp: float          # Server timestamp
    data: dict

async def send_websocket_update(
    ws: WebSocket,
    event: Event,
    state: TaskState
):
    """Send update with version info"""
    message = WebSocketMessage(
        type=event.event_type,
        task_id=event.task_id,
        version=event.code_version,      # CLIENT MUST CHECK THIS
        sequence=event.sequence_number,   # For ordering
        timestamp=time.time(),
        data=event.data
    )

    await ws.send_json(asdict(message))

# Client-side reconciliation
class ClientState:
    """Client maintains version, rejects stale updates"""

    def __init__(self):
        self.current_version = 0

    def handle_update(self, message: WebSocketMessage) -> bool:
        """
        Handle update from server.

        Returns:
            True if update applied
            False if update rejected (stale)
        """
        if message.version < self.current_version:
            print(f"⚠️  Rejecting stale update: v{message.version} < v{self.current_version}")
            return False

        if message.version == self.current_version:
            # Same version, check sequence number
            if message.sequence <= self.last_sequence:
                print(f"⚠️  Rejecting duplicate: seq {message.sequence}")
                return False

        # Accept update
        self.current_version = message.version
        self.last_sequence = message.sequence
        self.apply_update(message.data)

        return True
```

---

## Complete System Design

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Client (Browser)                     │
│  ┌──────────────────────────────────────────────────┐  │
│  │  ClientState (version tracking)                   │  │
│  │  - Rejects stale updates                          │  │
│  │  - Reconciles with server version                 │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │ WebSocket (versioned messages)
                     │
┌────────────────────▼────────────────────────────────────┐
│                 FastAPI Server                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Task Orchestrator (Priority Queue)        │  │
│  │  - Max concurrent: 5                              │  │
│  │  - Max queue: 100 (bounded)                       │  │
│  │  - Priority: CRITICAL > HIGH > MEDIUM > LOW       │  │
│  │  - Backpressure: blocks when full                 │  │
│  └─────────────────┬────────────────────────────────┘  │
│                    │                                    │
│  ┌─────────────────▼────────────────────────────────┐  │
│  │         Event Store (Source of Truth)             │  │
│  │  - Append-only log                                │  │
│  │  - Vector clocks for causality                    │  │
│  │  - Version monotonicity                           │  │
│  │  - Sequence numbers                               │  │
│  └─────────────────┬────────────────────────────────┘  │
│                    │                                    │
│  ┌─────────────────▼────────────────────────────────┐  │
│  │      State Projections (Eventually Consistent)    │  │
│  │  - Rebuild from events                            │  │
│  │  - Versioned snapshots                            │  │
│  │  - Client reconciliation                          │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│           Context Manager (for small LLMs)              │
│  - Event summarization                                  │
│  - Cached system prompts (10x cheaper)                  │
│  - Relevance filtering                                  │
│  - Model routing (small → large if needed)              │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Checklist

### Phase 1: Event Store
- [ ] Implement `Event` dataclass with version, vector clock
- [ ] Implement `EventStore` with append-only log
- [ ] Add vector clock implementation
- [ ] Test event ordering and causality

### Phase 2: Task Orchestration
- [ ] Implement `TaskOrchestrator` with priority queue
- [ ] Add bounded queue (max 100) for backpressure
- [ ] Implement worker pool
- [ ] Add priority assignment rules
- [ ] Test overflow prevention

### Phase 3: Versioned State
- [ ] Implement `VersionedState` with monotonic versions
- [ ] Add state projection from events
- [ ] Implement WebSocket versioned messages
- [ ] Test version reconciliation

### Phase 4: Context Management
- [ ] Implement `ContextManager` for small LLMs
- [ ] Add event summarization
- [ ] Implement caching (system prompts)
- [ ] Add model routing logic
- [ ] Test token limits

### Phase 5: Client Reconciliation
- [ ] Implement client version tracking
- [ ] Add stale update rejection
- [ ] Test latency scenarios

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Event ordering accuracy** | 100% | No causality violations |
| **Stale update rejection** | >95% | % of stale updates caught |
| **Backpressure activation** | <10% of time | Queue full % |
| **Context window usage (mistral:7b)** | <80% of 8K | Avg tokens used |
| **Model routing efficiency** | >90% stay on small model | % not escalated |
| **Version conflicts** | 0 | Detected conflicts |

---

## References

### Event Sourcing & CQRS
- [Event Sourcing with FastAPI & Celery](https://dev.to/markoulis/how-i-learned-to-stop-worrying-and-love-raw-events-event-sourcing-cqrs-with-fastapi-and-celery-477e)
- [CQRS with FastAPI](https://www.pysquad.com/blogs/cqrs-and-event-sourcing-with-fastapi-building-even)
- [Event Sourcing Pattern](https://microservices.io/patterns/data/event-sourcing.html)

### Vector Clocks & Causality
- [Vector Clocks Explained](https://medium.com/big-data-processing/vector-clocks-182007060193)
- [Lamport Timestamps](https://www.geeksforgeeks.org/dsa/lamports-logical-clock/)

### Backpressure & Task Management
- [Backpressure Management](https://tech-champion.com/programming/python-programming/manage-async-i-o-backpressure-using-bounded-queues-and-timeouts/)
- [Async Concurrency Limiting](https://death.andgravity.com/limit-concurrency)

### Source of Truth & Consistency
- [Event Store as Source of Truth](https://beyondplm.com/2025/03/18/plm-evolution-single-source-of-truth-and-eventual-consistency/)
- [Eventual Consistency](https://en.wikipedia.org/wiki/Eventual_consistency)

### Context Window Management
- [LLM Context Management Guide](https://eval.16x.engineer/blog/llm-context-management-guide)
- [Context Caching](https://medium.com/@zbabar/context-window-caching-for-managing-context-in-llms-4eebb6c33b1c)
- [Hierarchical Caching (Strata)](https://arxiv.org/html/2508.18572v1)

---

## Key Takeaways

1. **Event Store = Source of Truth** - All state derived from immutable events
2. **Vector Clocks = Causality Tracking** - Determine event ordering across async processes
3. **Version Monotonicity** - Reject stale updates at both server and client
4. **Bounded Queues** - Backpressure prevents overflow
5. **Priority Hierarchy** - Critical tasks preempt background work
6. **Context Compression** - Summaries + caching for small LLMs (10x token savings)
7. **Client Reconciliation** - Handle latency-induced drift

**Bottom Line**: Latency doesn't change truth - it just delays observing it. With event sourcing + versioning + causality tracking, we maintain consistency despite async chaos.
