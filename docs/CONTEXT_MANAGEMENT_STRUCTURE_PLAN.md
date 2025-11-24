# Context Management Structure Plan for Mem0 Integration

## Folder Structure

After analysis, the proper structure separates:
- **`src/memory/`** - Long-term memory storage and retrieval (Mem0 system)
- **`src/context/`** - Short-term context, recent history, and immediate context management

```
src/
├── memory/                   # Long-term memory (Mem0-based)
│   ├── __init__.py
│   ├── core/                 # Core Mem0 client
│   │   ├── __init__.py
│   │   ├── client.py         # Mem0Client base class
│   │   ├── extended.py       # Extended memory operations
│   │   └── token_ops.py      # Token management utilities
│   │
│   ├── cache/                # Cache node structures
│   │   ├── __init__.py
│   │   ├── node.py           # CacheNode dataclass
│   │   └── relations.py      # Bidirectional reference management
│   │
│   ├── dspy/                 # DSPy memory integration
│   │   ├── __init__.py
│   │   ├── integration.py    # MemoryEnhancedModule
│   │   └── tools.py          # Memory tools for ReAct
│   │
│   └── utils/                # Memory utilities
│       ├── __init__.py
│       ├── config.py         # Local configuration
│       └── helpers.py        # Memory helper functions
│
└── context/                  # Short-term context management
    ├── __init__.py
    ├── core/                 # Core context building
    │   ├── __init__.py
    │   ├── builder.py        # ContextBuilder for immediate context
    │   └── manager.py        # ContextManager for recent context
    │
    ├── tokens/               # Token budget management
    │   ├── __init__.py
    │   ├── manager.py        # TokenManager with budget enforcement
    │   └── budget.py         # TokenBudget dataclass
    │
    ├── events/               # Event-based context
    │   ├── __init__.py
    │   ├── summarizer.py     # Event summarization for context
    │   └── filters.py        # Relevance filtering for events
    │
    └── hierarchy/            # Hierarchical context building
        ├── __init__.py
        └── builder.py        # HierarchicalContextBuilder
```

## Component Responsibilities

### Memory Layer (`src/memory/`)

**Long-term persistent storage and retrieval:**
- **Mem0Client**: Core interface to Mem0's long-term memory
- **CacheNode**: Graph-based cache nodes with bidirectional linking
- **MemoryEnhancedModule**: DSPy integration with memory
- **Search operations**: Semantic retrieval of memories

### Context Layer (`src/context/`)

**Immediate context and recent history:**
- **ContextManager**: Manages recent context within session
- **TokenManager**: Enforces 4096 token budget compliance
- **EventSummarizer**: Compresses event history for immediate context
- **ContextBuilder**: Assembles context from recent and memory sources
- **RelevanceFilter**: Filters events by relevance to current query

## Token Management Strategy

**4096 Token Limit Distribution:**
- **System Prompts**: 820 tokens (20%)
- **Generation Space**: 1230 tokens (30%)
- **Active Context**: 2048 tokens (50%)
- **Buffer**: 188 tokens (additional safety)

**Context Priority Layers:**
- **CRITICAL**: Current task state, immediate issues (always included)
- **HIGH**: Recent interactions, key decisions (if budget allows)
- **MEDIUM**: Module details, dependencies (if budget allows)
- **LOW**: Historical context, general information (removed first)

## Integration Flow

```
LLM Request
├── ContextManager: Assembles recent context (immediate history)
├── TokenManager: Enforces budget compliance
├── Mem0Client: Retrieves relevant long-term memories
├── EventSummarizer: Compresses event history
├── RelevanceFilter: Filters for current query relevance
└── ContextBuilder: Combines all into final context (≤2048 tokens)
    └── Sent to DSPy for processing within 4096 token limit
```

## File Limits & SRP

- Each file ≤ 100 lines of code (with 10% flexibility)
- Single Responsibility Principle: Each file has one clear purpose
- Clear interfaces between memory and context layers
- No circular dependencies between modules

## Import Pattern

- Absolute imports only (from src.level)
- Memory components import from memory/
- Context components import from context/ and memory/
- Example: `from src.memory.core.client import Mem0Client`
- Example: `from src.context.core.builder import ContextBuilder`
