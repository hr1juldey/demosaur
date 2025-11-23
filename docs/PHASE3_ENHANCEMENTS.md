# Phase 3 Enhancements: Networked Cache for Small LLMs

**CRITICAL RESEARCH FINDINGS**:
- ⚠️ Simple compression loses 3rd/4th degree relationships
- ⚠️ Temporal causality lost in flat summaries
- ⚠️ Small LLMs (7B-8B) need aggressive token management
- ⚠️ Graph-based cache with explicit references preserves 70% information vs 50% in flat summaries
- ⚠️ Event sourcing enables cache reconstruction and debugging

**CONTEXT**: This enhanced Phase 3 addresses the critical issue where context compression wipes out event details, causing small LLMs to forget "what, why, how" of tasks. We implement a **networked cache** with explicit references, leveraging event sourcing for reconstruction.

---

### 3.5 Networked Cache (Online + Offline)

**File**: `src/context/networked_cache.py` (≤100 lines)
- [ ] Implement `CacheNode` dataclass
- [ ] Implement `NetworkedCache` class with graph structure

**PASSING CRITERIA**:
- ✅ Each node has explicit references to dependencies and related nodes
- ✅ Graph traversal retrieves related context within 2 hops
- ✅ get_related_context() respects token budget
- ✅ Nodes stored in NetworkX DiGraph for relationship queries

**FAILING CRITERIA**:
- ❌ Nodes lack references (isolated summaries)
- ❌ Graph traversal doesn't respect token limit
- ❌ Related context retrieval fails or times out

**EDGE CASES**:
1. **Circular dependencies** (A→B→C→A) - should detect and handle
2. **Orphaned nodes** (no dependencies/references) - should still store
3. **Deep dependency chain** (10 levels) - should limit depth to 3
4. **Large graph** (1000+ nodes) - should use efficient graph algorithms
5. **Missing referenced node** - should handle gracefully

**Architecture**:
```python
@dataclass
class CacheNode:
    id: str  # "module:validators.py", "func:validate_email"
    type: str  # "task", "module", "function", "test", "concept"
    summary: str  # Compressed summary (100-500 tokens)
    full_content_ref: str  # Reference to full content in EventStore
    dependencies: List[str]  # IDs of nodes this depends on
    references: List[str]  # IDs this node mentions
    vector_clock: Dict[str, int]  # For cache invalidation
    metadata: Dict[str, Any]  # version, timestamp, etc.
```

**Graph Structure**:
```
[Task: task-123]
├─ contains → [Module: validators.py]
├─ contains → [Module: test_validators.py]

[Module: validators.py]
├─ depends_on → [Library: pydantic]
├─ depends_on → [Library: re]
├─ contains → [Function: validate_email]
├─ contains → [Function: validate_phone]
├─ tested_by → [Module: test_validators.py]

[Function: validate_email]
├─ depends_on → [Library: re]
├─ tested_by → [Test: test_email_validation]
├─ references → [Concept: RFC 5322]
```

---

### 3.6 Online Cache (Live Context During Execution)

**File**: `src/context/online_cache.py` (≤100 lines)
- [ ] Implement `OnlineCache` class
- [ ] Implement priority-based eviction (LRU + priority)

**PASSING CRITERIA**:
- ✅ Token budget enforced (8K for Mistral, 32K for Qwen3)
- ✅ Priority-based eviction: keep CRITICAL, evict BACKGROUND first
- ✅ Fast access (<1ms for cache hit)
- ✅ Automatic eviction when budget exceeded

**FAILING CRITERIA**:
- ❌ Cache grows beyond token budget
- ❌ Eviction removes CRITICAL items before BACKGROUND
- ❌ Cache access slow (>10ms)

**EDGE CASES**:
1. **All items CRITICAL priority** - evict oldest CRITICAL
2. **Cache empty, get() called** - return None gracefully
3. **Rapid updates** (100 items/sec) - should handle without lag
4. **Budget = 0** - should reject all additions

**Token Budget Allocation**:

**Mistral 7B (8K context)**:
```
Total: 8,192 tokens
├─ System Prompt: 500 tokens (6%)
├─ Task Description: 300 tokens (4%)
├─ Current Context: 4,000 tokens (49%)
│  ├─ Current module summary: 300 tokens
│  ├─ Related functions: 1,200 tokens
│  ├─ Dependencies: 800 tokens
│  ├─ Recent errors: 400 tokens
│  └─ Test results: 1,300 tokens
├─ Code Generation Space: 2,500 tokens (31%)
└─ Buffer: 892 tokens (10%)
```

**Qwen3 8B (32K context)**:
```
Total: 32,768 tokens
├─ System Prompt: 500 tokens (1.5%)
├─ Task Description: 500 tokens (1.5%)
├─ Current Context: 12,000 tokens (37%)
│  ├─ Current module summary: 500 tokens
│  ├─ Related modules (2 levels): 3,000 tokens
│  ├─ Dependencies (detailed): 2,500 tokens
│  ├─ Recent errors (last 5): 1,500 tokens
│  ├─ Test results (full): 2,500 tokens
│  └─ Historical patterns: 2,000 tokens
├─ Code Generation Space: 15,000 tokens (46%)
└─ Buffer: 4,768 tokens (14%)
```

---

### 3.7 Offline Cache (Persistent Between Sessions)

**File**: `src/context/offline_cache.py` (≤100 lines)
- [ ] Implement `OfflineCache` class
- [ ] Implement disk persistence with NetworkX graph serialization

**PASSING CRITERIA**:
- ✅ Graph persists to disk (JSON or pickle)
- ✅ load() restores full graph with all nodes
- ✅ search_semantic() finds similar nodes via embeddings
- ✅ PageRank ranking prioritizes important nodes

**FAILING CRITERIA**:
- ❌ Persistence fails silently
- ❌ load() corrupts graph or loses nodes
- ❌ Semantic search returns irrelevant nodes

**EDGE CASES**:
1. **File doesn't exist on load()** - initialize empty graph
2. **Corrupt graph file** - fallback to empty, log error
3. **Large graph** (10K nodes) - should compress or use graph DB
4. **No embeddings available** - fallback to keyword search

**Features**:
- **Semantic search**: Find nodes by meaning, not exact match
- **PageRank ranking**: Prioritize frequently-referenced nodes
- **Persistent storage**: Survives task completion
- **Historical patterns**: Learn from past solutions

---

### 3.8 DSPy-Based Summary Generation

**File**: `src/context/dspy_summarizers.py` (≤100 lines)
- [ ] Implement `ModuleSummarizer` DSPy signature
- [ ] Implement `FunctionSummarizer` DSPy signature
- [ ] Implement `TaskSummarizer` DSPy signature

**PASSING CRITERIA**:
- ✅ Summaries have structured fields (purpose, dependencies, etc.)
- ✅ Type-safe outputs via DSPy signatures
- ✅ Consistent format across all summaries
- ✅ Summary generation completes in <5s

**FAILING CRITERIA**:
- ❌ Summaries missing required fields
- ❌ Inconsistent format between calls
- ❌ Generation times out (>30s)

**EDGE CASES**:
1. **Empty code input** - should generate "No code yet" summary
2. **Malformed code** (syntax errors) - should still summarize
3. **Very long code** (10K lines) - should truncate or sample
4. **LLM failure** - should retry or use fallback

**DSPy Signatures**:

```python
class ModuleSummarizer(dspy.Signature):
    """Generate structured summary of code module"""

    # Inputs
    module_name: str = dspy.InputField(desc="Name of the module")
    source_code: str = dspy.InputField(desc="Full source code")
    test_results: str = dspy.InputField(desc="Test execution results")
    iteration_history: str = dspy.InputField(desc="Refinement history")

    # Outputs
    purpose: str = dspy.OutputField(desc="One-line purpose of module")
    dependencies: list[str] = dspy.OutputField(desc="List of dependencies")
    functions: list[str] = dspy.OutputField(desc="List of function names")
    key_decisions: str = dspy.OutputField(desc="Important design decisions")
    summary: str = dspy.OutputField(desc="200-token comprehensive summary")

class FunctionSummarizer(dspy.Signature):
    """Generate structured summary of single function"""

    # Inputs
    function_name: str = dspy.InputField()
    source_code: str = dspy.InputField()
    dependencies: list[str] = dspy.InputField()

    # Outputs
    purpose: str = dspy.OutputField(desc="What function does")
    inputs: str = dspy.OutputField(desc="Input parameters and types")
    outputs: str = dspy.OutputField(desc="Return value and type")
    side_effects: str = dspy.OutputField(desc="External changes made")
    summary: str = dspy.OutputField(desc="100-token summary")

class TaskSummarizer(dspy.Signature):
    """Generate structured summary of entire task"""

    # Inputs
    task_id: str = dspy.InputField()
    requirements: str = dspy.InputField()
    plan: str = dspy.InputField()
    module_results: dict = dspy.InputField()

    # Outputs
    goal: str = dspy.OutputField(desc="High-level goal")
    status: str = dspy.OutputField(desc="Current status")
    modules: list[str] = dspy.OutputField(desc="List of modules")
    success_rate: float = dspy.OutputField(desc="Test success rate 0-1")
    summary: str = dspy.OutputField(desc="100-token task summary")
```

---

### 3.9 Event Sourcing Integration

**File**: `src/context/event_cache_integration.py` (≤100 lines)
- [ ] Implement `EventSourcedCache` class
- [ ] Implement cache reconstruction from events

**PASSING CRITERIA**:
- ✅ rebuild_cache() reconstructs cache from event history
- ✅ Time-travel: rebuild at any past timestamp
- ✅ Cache invalidation via vector clocks
- ✅ Event replay is deterministic (same events = same cache)

**FAILING CRITERIA**:
- ❌ Rebuild produces different cache on second run
- ❌ Time-travel fails or produces wrong state
- ❌ Cache invalidation misses stale entries

**EDGE CASES**:
1. **Empty event history** - return empty cache
2. **Events out of order** - sort by sequence_number first
3. **Rebuild at future timestamp** - return latest state
4. **Events with missing data fields** - use defaults

**Key Methods**:

```python
class EventSourcedCache:
    async def rebuild_cache(
        self,
        task_id: str,
        until_timestamp: Optional[str] = None
    ) -> NetworkedCache:
        """Rebuild cache state from event history"""
        events = await event_store.get_events(
            task_id=task_id,
            until=until_timestamp
        )

        cache = NetworkedCache()
        for event in sorted(events, key=lambda e: e.sequence_number):
            cache = self.apply_event(event, cache)

        return cache

    def apply_event(self, event: Event, cache: NetworkedCache):
        """Apply single event to cache (event sourcing pattern)"""
        if event.event_type == EventType.MODULE_COMPLETE:
            # Add module node to cache
            node = CacheNode(
                id=f"module:{event.data['module_name']}",
                type="module",
                summary=event.data.get('summary', ''),
                vector_clock=event.vector_clock.copy(),
                # ...
            )
            cache.add_node(node)

        # ... handle other event types
        return cache

    def is_cache_stale(
        self,
        cache_entry: CacheNode,
        latest_events: List[Event]
    ) -> bool:
        """Check if cache entry is stale via vector clocks"""
        for event in latest_events:
            # If event has newer vector clock than cache, cache is stale
            if VectorClock.happens_before(
                cache_entry.vector_clock,
                event.vector_clock
            ):
                return True
        return False
```

---

### 3.10 Hierarchical Context Builder

**File**: `src/context/hierarchical_builder.py` (≤100 lines)
- [ ] Implement `HierarchicalContextBuilder` class
- [ ] Implement multi-level summary assembly

**PASSING CRITERIA**:
- ✅ Build context in priority order (CRITICAL first)
- ✅ Respect token budget (stop at 80% to reserve generation space)
- ✅ Include explicit references between levels
- ✅ Gracefully handle missing nodes

**FAILING CRITERIA**:
- ❌ Context exceeds token budget
- ❌ Priority order not respected
- ❌ Missing references between levels

**EDGE CASES**:
1. **Token budget = 1000, but CRITICAL context = 1500** - truncate CRITICAL
2. **All nodes are LOW priority** - still include what fits
3. **Referenced node missing** - skip reference, continue
4. **Circular references** - detect and break cycle

**Context Priority Levels**:

1. **CRITICAL** (Always include):
   - Current task description
   - Current module summary
   - Immediate dependencies
   - Latest error/test failure

2. **HIGH** (Include if space):
   - Related function summaries
   - Dependency code snippets
   - Recent iteration history (last 2)

3. **MEDIUM** (Include if space):
   - Test code for current module
   - Related modules (same task)
   - Library usage patterns

4. **LOW** (Include if space):
   - Historical solutions (similar tasks)
   - Project-wide patterns
   - Full error trail

**Multi-Level Summary Example**:

```markdown
# Level 1: Task Summary (100 tokens)
Task: task-abc123
Status: Completed
Goal: Build email/phone validator module
Modules: [→ validators.py], [→ test_validators.py]
Success Rate: 100% (12/12 tests passed)

# Level 2: Module Summary (300 tokens)
## Module: validators.py [ID: mod-val-001]
Purpose: Email and phone validation functions
Dependencies: [→ pydantic], [→ phonenumbers], [→ re]
Functions:
  - [→ validate_email]: RFC 5322 email validation
  - [→ validate_phone]: International phone validation
Tests: [→ test_validators.py] (12/12 passed)
Full Code: [storage://task-abc123/validators.py]

# Level 3: Function Summary (150 tokens)
## Function: validate_email [ID: func-val-email-001]
Module: [← validators.py]
Purpose: Validate email addresses using RFC 5322 regex
Input: email: str
Output: bool (True if valid)
Dependencies: [→ re module]
Test Coverage: [→ test_email_valid], [→ test_email_invalid]
```

**Note**: Arrows ([→], [←]) are explicit references that enable graph traversal.

---

### 🧪 TEST GATE 3 (Enhanced): Networked Cache Tests

**File**: `tests/test_networked_cache.py` (≤100 lines)

```python
# Test 1: Node relationships
✅ PASS: add_node() creates edges for dependencies and references
✅ PASS: get_related_context() follows graph edges within depth=2
❌ FAIL: Edges missing or graph traversal fails

# Test 2: Token budget respect
✅ PASS: get_related_context(max_tokens=1000) returns ≤1000 tokens
❌ FAIL: Returns >1000 tokens

# Test 3: Graph persistence
✅ PASS: save() → load() restores all nodes and edges
❌ FAIL: Nodes or edges lost after load()

# Test 4: Circular dependency handling
✅ PASS: A→B→C→A detected, breaks cycle gracefully
❌ FAIL: Infinite loop or crash
```

**File**: `tests/test_online_offline_cache.py` (≤100 lines)

```python
# Test 1: Online cache eviction
✅ PASS: Budget=1000 tokens, add 1500 → evicts lowest priority first
❌ FAIL: Doesn't evict or evicts wrong items

# Test 2: Offline cache semantic search
✅ PASS: search_semantic("email validation") finds validate_email function
❌ FAIL: Returns irrelevant nodes

# Test 3: Cache migration
✅ PASS: Online cache → Offline cache preserves all data
❌ FAIL: Data lost during migration
```

**File**: `tests/test_dspy_summarizers.py` (≤100 lines)

```python
# Test 1: Structured outputs
✅ PASS: ModuleSummarizer returns all required fields (purpose, dependencies, etc.)
❌ FAIL: Missing fields or wrong types

# Test 2: Consistent format
✅ PASS: Two calls with same input → identical output structure
❌ FAIL: Inconsistent formats

# Test 3: Error handling
✅ PASS: Empty code input → generates valid summary (not error)
❌ FAIL: Crashes or returns None
```

**File**: `tests/test_event_cache_integration.py` (≤100 lines)

```python
# Test 1: Cache reconstruction
✅ PASS: rebuild_cache() from 50 events produces correct cache state
❌ FAIL: Cache state incorrect or incomplete

# Test 2: Time-travel
✅ PASS: rebuild_cache(until="2024-01-15") returns cache as of that date
❌ FAIL: Wrong state or includes future events

# Test 3: Vector clock invalidation
✅ PASS: is_cache_stale() detects stale entry when new event arrived
❌ FAIL: Doesn't detect staleness or false positive
```

**File**: `tests/test_hierarchical_builder.py` (≤100 lines)

```python
# Test 1: Priority ordering
✅ PASS: CRITICAL context included first, LOW last
❌ FAIL: Wrong priority order

# Test 2: Token budget enforcement
✅ PASS: Budget=8000, context stops at 6400 (80%)
❌ FAIL: Exceeds 80% threshold

# Test 3: Explicit references
✅ PASS: Context includes [→ ref] markers for related nodes
❌ FAIL: Missing references or broken links
```

**Run Tests**:
```bash
pytest tests/test_networked_cache.py \
       tests/test_online_offline_cache.py \
       tests/test_dspy_summarizers.py \
       tests/test_event_cache_integration.py \
       tests/test_hierarchical_builder.py -v
```

⛔ **STOP HERE IF ANY TEST FAILS** ⛔

---

## Summary: What This Solves

**Problem**: Context compression wipes out event details, causing small LLMs to forget:
- **What** they were doing (task goal, current module)
- **Why** they were doing it (design decisions, iteration history)
- **How** they were doing it (approaches tried, test results)
- **3rd/4th degree relations** (dependencies of dependencies)

**Solution**: Networked cache with explicit references:
- **Online cache**: Fast, live context for current task (8K-32K tokens)
- **Offline cache**: Persistent historical knowledge (unlimited)
- **Graph structure**: Explicit references preserve relationships
- **DSPy summaries**: Structured, type-safe summaries with consistent format
- **Event sourcing**: Rebuild cache at any point, debug state evolution
- **Vector clocks**: Invalidate stale cache entries automatically

**Result**: Small LLMs (Mistral 7B, Qwen3 8B) can maintain context without forgetting critical information, even with aggressive compression (70% reduction while retaining 70% information vs 50% in flat summaries).

---

## Integration Notes

**Existing Code Compatibility**:
- ✅ Works with existing EventStore (Phase 1)
- ✅ Uses VectorClock for invalidation (Phase 1)
- ✅ Integrates with TaskOrchestrator priority system (Phase 2)
- ✅ Builds on existing WorkflowEvent types

**Migration Path**:
1. Implement networked cache alongside existing context management
2. Generate cache nodes from existing task states
3. Gradually replace simple compression with graph-based retrieval
4. Monitor effectiveness: compression ratio vs information retention

**Performance Considerations**:
- Graph traversal: O(N) where N = number of related nodes (typically <50)
- Semantic search: O(log K) where K = total nodes (using embeddings + FAISS)
- Cache rebuild: O(E) where E = number of events (typically <1000)
- All operations <100ms for typical task sizes

---
