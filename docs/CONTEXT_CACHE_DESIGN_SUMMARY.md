# Context Cache Design Summary

**Date**: 2025-11-23
**Status**: Research Complete, Implementation Spec Added to Phase 3

---

## Problem Statement

When using DSPy's conversation history or any compression technique with small LLMs (Mistral 7B, Qwen3 8B), critical information gets lost in three dimensions:

1. **Semantic Loss**: Detailed reasoning → high-level conclusions only
2. **Temporal Loss**: Event sequences and causality → static summaries
3. **Relational Loss**: 3rd/4th degree dependencies → only direct links

**Impact**: Small LLMs forget:
- **What** they were doing (current task state)
- **Why** they were doing it (design decisions, iteration history)
- **How** they were doing it (approaches tried, test results)
- **Relationships**: Function dependencies, module interactions, test coverage

---

## Solution: Networked Cache Architecture

### Core Insight

Instead of **compressing** context into flat summaries, create a **graph-based cache** where:
- Each node is a summary (task, module, function, test, concept)
- Nodes have **explicit references** to related nodes
- Multi-level summaries: 100 tokens (task) → 300 tokens (module) → 150 tokens (function) → full code
- Event sourcing enables cache reconstruction and time-travel debugging

**Result**: 70% compression ratio while retaining 70% information (vs 50% in flat summaries)

---

## Architecture Overview

```
HybridCacheManager
├── OnlineCache (In-Memory, Fast Access)
│   ├── Current task context (8K-32K tokens)
│   ├── Priority-based eviction (LRU + priority)
│   └── Used for: Active task execution
│
├── OfflineCache (Disk + Graph)
│   ├── NetworkX graph of all nodes
│   ├── Vector embeddings for semantic search
│   ├── PageRank-based ranking
│   └── Used for: Historical patterns, similar solutions
│
├── DSPySummarizers
│   ├── Generate structured summaries
│   ├── Type-safe outputs via signatures
│   └── Consistent format across all levels
│
└── EventSourcedCache
    ├── Rebuild cache from event history
    ├── Time-travel debugging
    └── Vector clock-based invalidation
```

---

## Key Components Added to Phase 3

### 3.5 Networked Cache (Online + Offline)
- **CacheNode** dataclass with explicit references
- **NetworkedCache** class using NetworkX DiGraph
- Graph traversal within token budget
- Handles circular dependencies

### 3.6 Online Cache (Live Context)
- In-memory, fast access (<1ms)
- Priority-based eviction (keep CRITICAL, evict BACKGROUND)
- Token budget enforcement:
  - **Mistral 7B**: 8K total, 4K for context, 2.5K for generation
  - **Qwen3 8B**: 32K total, 12K for context, 15K for generation

### 3.7 Offline Cache (Persistent)
- Disk-based persistence (survives task completion)
- Semantic search via embeddings
- PageRank ranking for importance
- Graph serialization (JSON/pickle)

### 3.8 DSPy-Based Summary Generation
- **ModuleSummarizer**: 200-token structured summaries
- **FunctionSummarizer**: 100-token summaries with dependencies
- **TaskSummarizer**: High-level task overview
- Type-safe outputs, consistent format

### 3.9 Event Sourcing Integration
- **rebuild_cache()**: Reconstruct cache from event history
- **Time-travel**: Rebuild at any past timestamp
- **Vector clock invalidation**: Detect stale cache entries
- Deterministic replay (same events = same cache)

### 3.10 Hierarchical Context Builder
- Build context in priority order (CRITICAL → HIGH → MEDIUM → LOW)
- Respect token budget (stop at 80%)
- Include explicit references between levels ([→ ref])
- Gracefully handle missing nodes

---

## Token Budget Strategy

### Mistral 7B (8K context)
```
CRITICAL (Always):
  - Current module summary: 300 tokens
  - Latest error: 400 tokens
  - Immediate dependencies: 800 tokens

HIGH (If space):
  - Related functions: 1,200 tokens
  - Recent iteration: 400 tokens

Reserve for generation: 2,500 tokens (31%)
```

### Qwen3 8B (32K context)
```
CRITICAL (Always):
  - Current module summary: 500 tokens
  - Related modules (2 levels): 3,000 tokens
  - Latest 5 errors: 1,500 tokens

HIGH (If space):
  - Dependencies (detailed): 2,500 tokens
  - Test results (full): 2,500 tokens
  - Historical patterns: 2,000 tokens

Reserve for generation: 15,000 tokens (46%)
```

---

## What This Preserves That Simple Compression Loses

### 1. Causal Relationships
**Lost in flat compression**: "Function A somehow uses B"
**Preserved in graph**: `A → depends_on → B → contains → function_x`

### 2. Temporal Causality
**Lost**: "Module was refactored"
**Preserved**: Event history shows iteration 1 → test fail → iteration 2 → refactor → iteration 3 → pass

### 3. 3rd/4th Degree Relations
**Lost**: "validate_email uses some regex library"
**Preserved**:
```
validate_email
├─ depends_on → validators.py
    ├─ depends_on → pydantic
    └─ depends_on → re module
        └─ python stdlib
```

### 4. Design Decisions
**Lost**: "Email validation works"
**Preserved**: "RFC 5322 regex chosen after 3 iterations (edge cases fixed)"

### 5. Test Coverage
**Lost**: "Tests passed"
**Preserved**:
```
validate_email
├─ tested_by → test_email_valid (5 test cases)
├─ tested_by → test_email_invalid (7 edge cases)
└─ coverage: 100% (12/12 passed, iteration 3)
```

---

## Research Sources

### Academic Papers (2025 State-of-the-Art)
1. **Context Cascade Compression (C3)** - 32-64 token compression
2. **RAGCache** - Hierarchical knowledge trees
3. **GraphRAG** - Query-focused summarization with PageRank
4. **DAST** - Context-aware compression for small LLMs

### Key Findings
- **KVzip**: 3-4× memory reduction, 2× faster, **no accuracy loss**
- **Hierarchical indices**: 250× token cost reduction
- **Graph+Semantic**: 70% compression with 70% info retention (best balance)
- **Small LLMs**: 20-46% performance improvements with optimized context

### DSPy Reality
- **DSPy does NOT compress** - maintains full conversation history
- **DSPy excels at**: Generating structured summaries via signatures
- **Use case**: Create type-safe, consistent summaries for cache nodes

---

## Implementation Timeline

### Phase 1: Foundation (Week 1)
- OnlineCache, OfflineCache classes
- EventStore integration
- Token budget management

### Phase 2: Summaries (Week 2)
- DSPy signatures (Module, Function, Task)
- Hierarchical summary pipeline
- Vector embeddings

### Phase 3: Intelligence (Week 3)
- Graph-based retrieval (PageRank)
- Semantic search
- Event-driven invalidation

### Phase 4: Optimization (Week 4)
- Fine-tune compression ratios
- Model-specific budgets
- Performance benchmarks

---

## Trade-offs Matrix

| Strategy | Compression | Info Retained | Rebuild Cost | Latency | Recommended For |
|----------|-------------|---------------|--------------|---------|-----------------|
| No Cache | 0% | 100% | High | High | Not viable |
| Online Only | 50% | 75% | Medium | Low | Simple tasks |
| Hierarchical | 70% | 60% | Low | Medium | Most tasks |
| **Graph+Semantic** | **75%** | **70%** | **Low** | **Medium** | **Best balance** |
| Full Replay | 0% | 100% | Very High | Very High | Debugging only |

---

## Expected Outcomes

### For Mistral 7B (8K context)
- **Before**: Loses context after 3-4 iterations, forgets why decisions made
- **After**: Maintains task goal, current module, and immediate dependencies across 10+ iterations

### For Qwen3 8B (32K context)
- **Before**: Loses 3rd degree relationships, forgets historical patterns
- **After**: Maintains 2 levels of dependencies, learns from past solutions, preserves iteration history

### For Both
- **Compression**: 70-75% reduction in token usage
- **Retention**: 70% of critical information preserved
- **Performance**: <100ms for graph traversal, <1ms for cache hits
- **Debugging**: Can reconstruct cache at any point in history via event replay

---

## Integration with Existing System

### Leverages Existing Components
- ✅ **EventStore** (Phase 1): Full event history for cache reconstruction
- ✅ **VectorClock** (Phase 1): Cache invalidation via vector clocks
- ✅ **TaskOrchestrator** (Phase 2): Priority system for context prioritization
- ✅ **WorkflowEvent** types: Direct mapping to cache nodes

### Backward Compatible
- Existing context management continues to work
- Networked cache runs alongside, not replacing
- Gradual migration path
- Can A/B test effectiveness

---

## Success Metrics

### Quantitative
- **Token savings**: ≥60% reduction vs full context
- **Information retention**: ≥65% of critical info preserved
- **Cache hit rate**: ≥80% for similar tasks
- **Performance**: <100ms for context building

### Qualitative
- **LLM doesn't forget**: Current task goal across iterations
- **LLM doesn't repeat**: Same mistake not made twice
- **LLM doesn't ask**: "What was I doing?" mid-task
- **LLM generates better code**: Uses historical patterns

---

## Next Steps

1. ✅ Research complete
2. ✅ Spec added to IMPLEMENTATION_CHECKLIST_DETAILED.md
3. ⏳ Implement Phase 3.5-3.10 (networked cache components)
4. ⏳ Write comprehensive tests
5. ⏳ Benchmark compression ratio vs information retention
6. ⏳ Fine-tune token budgets for Mistral 7B and Qwen3 8B

---

**Research Document**: `/home/riju279/Downloads/demo/docs/CACHE_RESEARCH.md` (1461 lines, 30+ sources)
**Implementation Spec**: `/home/riju279/Downloads/demo/docs/IMPLEMENTATION_CHECKLIST_DETAILED.md` (Phase 3.5-3.10)
**Summary Document**: This file

---
