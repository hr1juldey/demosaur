# Approach for Context Management with 4096 Token Limit

## Problem Statement

The Ollama system enforces a **hard 4096 token limit** for input context, regardless of the underlying model's native capabilities. Small LLMs (Mistral 7B, Qwen3 8B) need sophisticated context management to:
1. Maintain task state and progress
2. Preserve causal relationships between events
3. Provide sufficient context for code generation
4. Work within the 4096 token constraint

## Research-Based Solution: Hierarchical Context with 2-Way Linking

Based on analysis of `docs/CACHE_RESEARCH.md`, `docs/CONTEXT_CACHE_DESIGN_SUMMARY.md`, and `docs/PHASE3_ENHANCEMENTS.md`, the optimal approach is a **networked cache with explicit 2-way linking** that works within the 4096 token limit.

### Core Architecture

```
Context Management System
├── Token Budget Manager (4096 total)
│   ├── Reserve 20% (820 tokens) for system prompts
│   ├── Reserve 30% (1230 tokens) for generation space
│   └── Use 50% (2048 tokens) for active context
│
├── Networked Cache (Graph Structure)
│   ├── CacheNode: Structured, minimal token footprint
│   ├── Bidirectional References (2-way linking)
│   ├── Prioritized retrieval by importance
│   └── Event-sourced reconstruction
│
└── Hierarchical Context Builder
    ├── CRITICAL context: Must always be present
    ├── HIGH priority: Include if budget allows
    ├── MEDIUM priority: Optional enhancement
    └── LOW priority: Removed first under pressure
```

## 2-Way Linking Strategy

Following the requirements for bidirectional references:

### Forward References (Parent → Children)
- `Task → contains → Modules`
- `Module → contains → Functions`
- `Function → depends_on → Libraries`
- `Module → tested_by → Tests`

### Backward References (Children → Parents) 
- `Function → belongs_to → Module`
- `Test → tests → Module`
- `Library → used_by → Function`
- `Module → part_of → Task`

This creates a **fully connected graph** where each node knows both what it references and what references it.

## Token Budget Allocation (4096 tokens max)

### Mistral 7B Equivalent Budget:
```
Total: 4096 tokens (hard limit)
├── System prompts: 820 tokens (20%)
├── Generation space: 1230 tokens (30%)
├── Active context: 2048 tokens (50%)
└── Buffer: 0 tokens (0%, not guaranteed)
```

### Context Priority Strategy:
1. **CRITICAL (Always included, ~400 tokens)**:
   - Current task ID and status
   - Current module being worked on
   - Latest error/issue
   - Immediate dependencies

2. **HIGH (If space allows, ~800 tokens)**:
   - Related functions in current module
   - Recent iteration history (last 2)
   - Immediate parents (function→module→task)

3. **MEDIUM (If space allows, ~600 tokens)**:
   - Test results for current module
   - Direct dependencies and dependents
   - Recent successful approaches

4. **LOW (Removed first, ~248 tokens)**:
   - Historical patterns from similar tasks
   - Older iteration history
   - General project information

## Implementation Strategy

### Phase 3.5: Networked Cache with 2-Way Linking
- Implement `CacheNode` with bidirectional reference tracking
- Create graph structure that maintains both forward and backward links
- Implement efficient traversal within token budget

### Phase 3.6: Budget-Aware Context Building
- Create ContextBuilder that respects 4096 token limit
- Implement priority-based node selection
- Add fallback strategies when budget is exceeded

### Phase 3.7: Event Sourced Cache Integration
- Rebuild cache from event history with 2-way linking
- Maintain vector clock for cache invalidation
- Support "time travel" debugging within token limits

## Risk Mitigation

1. **Budget Overflow**: Implement strict token counting with immediate fallback
2. **Link Cycles**: Detect and break circular references during graph construction
3. **Performance**: Use efficient graph algorithms (O(n) where n is relevant nodes)
4. **Recovery**: Fallback to simpler context if complex graph exceeds budget

## Key Benefits

1. **Preserves Relationships**: 2-way linking maintains causal relationships even with aggressive compression
2. **Adapts to Limit**: Automatically adjusts context size based on 4096 token constraint  
3. **Maintains Traceability**: Can trace from any node to its dependencies and dependents
4. **Event-Sourced**: Cache can be rebuilt from events, ensuring consistency
5. **Prioritized**: Critical context always maintained, less important context removed first

This approach ensures that even with the 4096 token hard limit, the system can maintain sufficient context for effective code generation while preserving the critical relationships that small LLMs need to understand the task structure.