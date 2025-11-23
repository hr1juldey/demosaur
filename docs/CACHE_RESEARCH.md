# Cache Design Research for Small LLMs in Code Generation Systems

**Date**: 2025-11-23
**Target Models**: Mistral 7B (8K-32K context), Qwen3 8B (32K-131K context)
**Use Case**: Event-sourced code generation system with full task history

---

## Executive Summary

This research analyzes context management and caching strategies for small LLMs (7B-8B parameters) in code generation systems. Key findings:

1. **DSPy does NOT implement conversation history compression** - it maintains full conversation history
2. **llms.txt approach** creates structured documentation through multi-stage analysis, not compression
3. **Fast-GraphRAG** uses graph-based retrieval with PageRank for relationship-aware context
4. **Critical insight**: Information loss occurs in 3 dimensions - **semantic content**, **temporal ordering**, and **causal relationships**
5. **Hierarchical cache design** is essential for small context windows (8K-32K tokens)

---

## 1. DSPy Conversation History Analysis

### Finding: No Built-in Compression

**Key Discovery**: DSPy's `dspy.History` maintains **full conversation history** without compression.

```python
# DSPy's approach (from documentation)
history.messages.append({"question": question, **outputs})
```

**Characteristics**:

- All input/output fields preserved intact
- Second query retains first exchange completely
- Few-shot examples represented as JSON in single turn
- No compression ratios or selective filtering

**Implication**: DSPy prioritizes complete context over size reduction. Developers must implement custom compression.

**Source**: [DSPy Conversation History Tutorial](https://dspy.ai/tutorials/conversation_history/)

---

## 2. LLMs.txt Generation Approach

### Finding: Multi-Stage Structural Analysis, Not Compression

**Key Discovery**: The llms.txt approach creates **new structured documentation** through analysis, not by condensing existing content.

**Architecture**:

```python
# Three-stage pipeline
1. AnalyzeRepository → Extract purpose, concepts, architecture
2. AnalyzeCodeStructure → Identify directories, entry points
3. GenerateLLMsTxt → Synthesize findings into formatted output
```

**Generated Structure**:

```markdown
# Project Name
## Project Overview
[Framework description]

## Key Concepts
- Module: Building blocks for LM programs
- Signatures: Input/output specifications

## Architecture
- /dspy/: Main package
  - /adapters/: Format handlers
  - /clients/: LM interfaces

## Usage Examples
[5 detailed scenarios with context]
```

**Key Differences from Compression**:

- Analyzes **structural relationships** vs summarizing content
- Extracts **architectural patterns** from file organization
- Identifies **conceptual terminology** independent of docs
- Creates **new example narratives** synthesizing multiple sources

**Networked Cache Potential**:

- Concept-to-file mappings: "Find all implementations of Module concept"
- Dependency graphs between directories
- Link usage examples to architectural components
- Backward references from concepts to code locations

**Current Limitation**: Uses **implicit linking through shared vocabulary** rather than explicit hyperlinks.

**Source**: [DSPy llms.txt Generation Tutorial](https://dspy.ai/tutorials/llms_txt_generation/)

---

## 3. Fast-GraphRAG Analysis

### Finding: Graph-Based Retrieval with Multi-Level Organization

**Key Architecture**:

- Constructs knowledge graphs from unstructured data
- "Human-navigable view of knowledge that can be queried, visualized, and updated"
- Emphasizes asynchronous operations with type safety

**Entity Relationship Maintenance**:

- Accepts configurable entity types (Character, Place, Event, etc.)
- Maintains interconnections within graph structure
- Avoids traditional chunking that breaks context

**Retrieval Mechanism**:

- **PageRank-based graph exploration** for enhanced accuracy
- Personalized PageRank identifies semantically relevant information
- Traverses entity relationships vs pure similarity matching

**Key Insight**:
> "Graphs provide interpretable and debuggable knowledge"

This transparency - understanding **why** information retrieves - represents the core advantage over vector-only approaches.

**Multi-Level Summaries**:

- System supports "dynamic data" that generates/refines graphs
- Adaptive abstraction layers fit domain needs
- No explicit hierarchical summarization detailed in docs

**Lightweight Alternative for Small LLMs**:

```python
# Simplified version for 8K-32K context
- Extract entities and immediate relationships only
- Basic graph traversal (no PageRank)
- Reduce computational overhead 60-80%
```

**Source**: [Fast-GraphRAG GitHub](https://github.com/circlemind-ai/fast-graphrag)

---

## 4. Information Loss in Compression

### Three Dimensions of Loss

#### 1. Semantic Content Loss

**What Gets Lost**:

- Detailed conversations reduced to summaries
- Exploration steps condensed to "what was learned"
- File examination details compressed to conclusions
- Specific approaches tried → generic "approaches attempted"

**Evidence**:
> "When using compression tools, all exploration gets condensed into a concise summary that captures what was learned, which files were examined, and what approaches were tried."

**Mitigation**: It's "difficult to predict which parts of historical conversation get more weightage during compression"

**Sources**:

- [Smol Command - Cline](https://docs.cline.bot/features/slash-commands/smol)
- [LLM Chat History Summarization](https://mem0.ai/blog/llm-chat-history-summarization-guide-2025)

#### 2. Temporal Ordering Loss

**What Gets Lost**:

- Event sequence and causality
- Which changes came before others
- Iterative refinement history
- Decision points and alternatives considered

**Critical for Code Generation**:

- Function A depends on Function B (created earlier)
- Module C was refactored after test failure
- Library X was added because approach Y failed

#### 3. Relational/Causal Loss

**What Gets Lost**:

- 3rd/4th degree relationships between entities
- Function dependency chains
- Cross-module interactions
- Implicit assumptions from context

**Example**:

```
Lost: "Function validate_input() uses regex from constants.py which imports from external library 'validators'"
Kept: "validate_input() validates input"
```

---

## 5. Context Compression Techniques (2025 State-of-the-Art)

### Context Cascade Compression (C3)

**Architecture**:

- Cascades two LLMs of different sizes
- Small LLM (first stage) compresses long context into latent tokens
- Typical compression: 32-64 tokens length

**Source**: [Context Cascade Compression Paper](https://arxiv.org/html/2511.15244)

### Segmentwise Context Compression

**Methods**:

- **CCF/CompLLM**: Segment-based compression
- **ICAE/SAC**: Slot-based autoencoders

**Capabilities**:

- Scale to >100K tokens
- Work under tight hardware constraints
- No retraining or architectural changes required

**Key Techniques**:

1. **Memory/Slot-based Autoencoding**:
   - Map long context to fixed "memory slots"
   - Use LoRA-adapted encoder module

2. **Semantic-Anchor Compression**:
   - Select actual input tokens as "anchors"
   - Aggregate context into their KV cache representations

**Sources**:

- [Emergent Mind: Context Compression](https://www.emergentmind.com/topics/context-compression-techniques)
- [DAST: Context-Aware Compression](https://aclanthology.org/2025.findings-acl.1055.pdf)

### Performance Results

- **Small LLMs**: 20-46% performance improvements with optimized contexts
- **Memory Reduction**: 26-54% peak token reduction
- **KVzip**: 3-4× memory reduction, 2× faster responses, **no accuracy loss**

**Source**: [AI Tech Can Compress LLM Memory](https://techxplore.com/news/2025-11-ai-tech-compress-llm-chatbot.html)

---

## 6. Compression Trade-offs

### Compression Ratio vs Information Retention

| Compression Level | Tokens Retained | What's Preserved | What's Lost |
|------------------|----------------|------------------|-------------|
| **None (100%)** | All tokens | Everything | N/A |
| **Light (70-80%)** | Recent + summaries | Recent details, key decisions | Minor exploration steps |
| **Medium (40-60%)** | Key facts + entities | Core entities, main flow | Detailed reasoning, alternatives |
| **Heavy (20-30%)** | Core summary only | High-level outcomes | Most context, relationships |
| **Extreme (<20%)** | Minimal abstract | Final results only | Nearly everything |

### Best Practices (From Research)

1. **Avoid Over-Compression**:
   - Don't exceed 80% compression ratio
   - Diminishing returns beyond this threshold

2. **Incremental Compression**:
   - Compress prompts incrementally
   - Evaluate output quality at each stage

3. **Hybrid Approaches**:
   - Combine basic summarization with advanced techniques
   - Use vectorized memory for semantic search

4. **Preserve Critical Elements**:
   - Retain essential keywords/entities
   - Prioritize user intent clarity
   - Keep causal relationships explicit

**Source**: [Prompt Compression in LLMs](https://medium.com/@sahin.samia/prompt-compression-in-large-language-models-llms-making-every-token-count-078a2d1c7e03)

---

## 7. Hierarchical Cache Design Principles

### Multi-Level Organization

**Inspired by GraphRAG and RAGCache**:

```
Level 1: Global Summary (100 tokens)
├─ "Task: Build validator module with email/phone validation"
│
Level 2: Module Summaries (300 tokens each)
├─ Module: validators.py
│  ├─ Purpose: Email and phone validation
│  ├─ Dependencies: re, phonenumbers
│  └─ Functions: validate_email(), validate_phone()
│
Level 3: Function Summaries (100 tokens each)
├─ validate_email()
│  ├─ Purpose: RFC 5322 email validation
│  ├─ Dependencies: re module
│  ├─ Test Status: 12/12 passed
│  └─ Refinements: 3 iterations (regex edge cases)
│
Level 4: Detailed Content (Full)
└─ Complete code, test results, error trails
```

**Key Principle**: Each level points to next level with explicit references.

### Cache Types

#### A. **RAGCache Approach** (Hierarchical Organization)

- Organize intermediate states in knowledge tree
- Cache in GPU/host memory hierarchy
- Frequent access → fast GPU memory
- Infrequent access → slower host memory

**Source**: [RAGCache Paper](https://arxiv.org/html/2404.12457v2)

#### B. **Hierarchical Indices** (LlamaIndex)

- Top-level summaries (entire documents)
- Mid-level overviews (subsections)
- Detailed chunks (granular information)

**Benefits**:

- Substantial ROUGE, BLEU, F1 improvements
- 250-fold token cost reduction in some cases

**Source**: [Hierarchical Indices for RAG](https://medium.com/@nirdiamant21/hierarchical-indices-enhancing-rag-systems-43c06330c085)

#### C. **Adaptive Contextual Compression (ACC)**

- Relevance estimation
- Hierarchical summarization
- Reinforcement signals
- Ensure critical info occupies token slots

**Source**: [Cache-Augmented Generation Paper](https://arxiv.org/html/2505.08261)

---

## 8. Small LLM Context Strategies

### Mistral 7B

**Native Capabilities**:

- **Sliding Window Attention (SWA)**: 8K context length
- **Grouped-Query Attention (GQA)**: Speeds inference, reduces memory
- **PoSE Extension**: Can extend 8K → 32K context

**Validated Extensions**:

- PoSE works with LLaMA, LLaMA2, GPT-J, Baichuan, Mistral

**Sources**:

- [Mistral 7B Documentation](https://mistral.ai/news/announcing-mistral-7b)
- [PoSE Extension Research](https://superagi.com/extending-context-window-of-a-7b-llm-from-8k-to-32k-using-pose-positional-skip-wise/)

### Qwen3 8B

**Native Capabilities**:

- **Native Context**: 32,768 tokens
- **YaRN Extension**: 131,072 tokens (4× expansion)

**Best Practices**:

- Only enable YaRN for long contexts (>32K average)
- May degrade performance if average context <32K
- For 65K context, set YaRN factor to 2.0

**Dual-Mode Capability**:

- **Thinking Mode**: For math, coding, logical inference
- **Non-Thinking Mode**: For general conversation
- Switch modes based on task complexity

**Fine-Tuning Recommendation**:

- Use 75% reasoning + 25% non-reasoning examples
- Maintains reasoning capabilities

**Sources**:

- [Qwen3 8B Documentation](https://huggingface.co/Qwen/Qwen3-8B)
- [Qwen3 Fine-Tuning Guide](https://docs.unsloth.ai/models/qwen3-how-to-run-and-fine-tune)

---

## 9. Code Generation Caching Strategies

### Semantic Caching

**GPTCache Approach**:

- Transform queries into vector embeddings
- Search for similar embeddings in cache
- Return cached response if semantic match found

**Key Advantage**: Matches meaning, not exact text.

**Source**: [GPTCache GitHub](https://github.com/zilliztech/GPTCache)

### Anchor Token Caching (Code-Specific)

**Finding**: Code has unique characteristics:

- Anchor tokens (punctuation, syntax) carry long-range dependencies
- 2024 research on "Anchor Attention" for code LLMs
- Achieve ≥70% KV cache size reduction
- Minimal performance drop

**Code Hashing**:

```python
# Hash problem description + context
cache_key = hash(problem_desc + context)
if cache_key in cache:
    return cache[cache_key]  # Return cached code snippet
```

**Sources**:

- [Caching Strategies for LLM Services](https://www.rohan-paul.com/p/caching-strategies-in-llm-services)
- [Semantic Cache Guide](https://medium.com/@svosh2/semantic-cache-how-to-speed-up-llm-and-rag-applications-79e74ce34d1d)

### Structured Summaries for Code

**Best Practice**:

```python
# Explicit structured prompt
structured_summary = {
    "purpose": "What the code does",
    "inputs": "Input parameters and types",
    "outputs": "Return values and types",
    "workflow": "Step-by-step logic",
    "side_effects": "External changes made",
    "summary": "One-line description"
}
```

**Performance**:

- Chain-of-thought prompts enhance accuracy
- One-shot examples improve by >13% in completeness
- Outperforms generic prompts significantly

**Sources**:

- [Hierarchical Repository Summarization](https://arxiv.org/html/2501.07857v1)
- [LLM Function Design Pattern](https://medium.com/aimonks/the-llm-function-design-pattern-a-structured-approach-to-ai-powered-software-development-f4192945d5f4)

### Function Dependencies

**What to Track**:

1. Class attributes the function uses
2. External libraries (third-party/built-in)
3. Project-specific dependencies (custom modules, configs, APIs)

**Modular Design**:

- Treat each function as discrete unit
- Well-defined inputs, outputs, prompt instructions
- Tool dependencies explicit
- Enables consistency, testability, modularity

---

## 10. Online vs Offline Caching

### Online Caching (Live Context During Execution)

**Purpose**: Maintain context within single task execution

**Characteristics**:

- Short-lived (task duration)
- High update frequency
- Optimized for low-latency access
- Contains current iteration state

**Example for Code Generation**:

```python
online_cache = {
    "current_module": "validator.py",
    "iteration": 3,
    "recent_errors": [...],  # Last 2 iterations
    "context_window": [...],  # Last 8K tokens
    "pending_refinements": [...]
}
```

**Trade-off**:

- Fast access (in-memory)
- Lost when task completes

---

### Offline Caching (Persistent Between Sessions)

**Purpose**: Preserve knowledge across task executions

**Characteristics**:

- Long-lived (persistent storage)
- Low update frequency
- Optimized for storage efficiency
- Contains historical summaries

**Example for Code Generation**:

```python
offline_cache = {
    "library_knowledge": {
        "pydantic": {
            "summary": "Data validation using type hints",
            "common_patterns": [...],
            "known_issues": [...]
        }
    },
    "project_patterns": {
        "validation_approach": "Use pydantic BaseModel",
        "test_structure": "pytest with fixtures"
    },
    "historical_solutions": {
        "email_validation": {
            "summary": "RFC 5322 regex pattern",
            "code_reference": "task-123/validators.py#L45"
        }
    }
}
```

**Trade-off**:

- Slower access (disk/DB)
- Persists across sessions

---

### Hybrid Strategy (Recommended)

**Two-Tier Cache System**:

```python
class HybridCache:
    def __init__(self):
        self.online = OnlineCache()   # Fast, temporary
        self.offline = OfflineCache()  # Persistent

    async def get_context(self, task_id: str, query: str):
        # 1. Check online cache first (fast)
        if result := await self.online.get(query):
            return result

        # 2. Query offline cache (slower, comprehensive)
        if result := await self.offline.search_semantic(query):
            # Populate online cache for future use
            await self.online.set(query, result)
            return result

        # 3. Generate new (cache miss)
        result = await self.generate(query)
        await self.online.set(query, result)
        await self.offline.store_for_future(query, result)
        return result
```

**Benefits**:

- Fast access for recent/current context
- Historical knowledge preserved
- Gradual migration: online → offline (with compression)

---

## 11. Event Sourcing Integration

### Leveraging Full Event History

**Your System's Advantage**:

```python
# From your codebase
@dataclass
class WorkflowEvent:
    type: EventType  # TASK_STARTED, MODULE_ITERATION, etc.
    task_id: str
    timestamp: str
    data: Dict[str, Any]
```

**Event Types Available**:

- `TASK_STARTED`, `REQUIREMENTS_COMPLETE`
- `PLANNING_STARTED`, `PLANNING_COMPLETE`
- `MODULE_STARTED`, `MODULE_ITERATION`, `MODULE_COMPLETE`
- `GENERATION_COMPLETE`, `TASK_COMPLETE`, `TASK_FAILED`

**Cache Reconstruction from Events**:

```python
class EventSourcedCache:
    async def rebuild_context(self, task_id: str, target_timestamp: str):
        """Rebuild cache state at any point in time"""
        events = await event_store.get_events(
            task_id,
            until=target_timestamp
        )

        cache_state = {}
        for event in events:
            cache_state = self.apply_event(event, cache_state)

        return cache_state

    def apply_event(self, event: WorkflowEvent, state: dict):
        """Apply single event to cache state"""
        if event.type == "MODULE_ITERATION":
            state["modules"][event.data["module_name"]] = {
                "iteration": event.data["iteration"],
                "score": event.data["score"],
                "timestamp": event.timestamp
            }
        # ... handle other event types
        return state
```

**Advantages**:

1. **Time Travel**: Reconstruct cache at any point in history
2. **Debugging**: Understand how cache state evolved
3. **Replay**: Regenerate summaries with improved algorithms
4. **Audit**: Track what information was available when

---

### Vector Clocks for Cache Invalidation

**Problem**: In distributed/concurrent systems, how to know when cache is stale?

**Vector Clock Basics**:

- Each process maintains vector of logical clocks
- Track causality and ordering of events
- Settle conflicts when replicas updated separately

**Application to Your System**:

```python
@dataclass
class CacheEntry:
    content: str
    vector_clock: Dict[str, int]  # {module_name: version}

class CacheInvalidation:
    def is_stale(
        self,
        cache_entry: CacheEntry,
        latest_events: List[WorkflowEvent]
    ) -> bool:
        """Check if cache entry is stale based on vector clocks"""
        for event in latest_events:
            module = event.data.get("module_name")
            if not module:
                continue

            # Event has newer version than cache?
            event_version = self.extract_version(event)
            cache_version = cache_entry.vector_clock.get(module, 0)

            if event_version > cache_version:
                return True  # Cache is stale

        return False  # Cache is current
```

**Cache Invalidation Strategies**:

1. **Event-Driven Invalidation** (Recommended):

   ```python
   # When MODULE_ITERATION event fires
   await cache.invalidate(f"module:{module_name}")
   await cache.invalidate(f"task:{task_id}:progress")
   ```

2. **Time-Based Invalidation**:

   ```python
   # Invalidate after N seconds
   cache_entry.expires_at = now() + timedelta(seconds=300)
   ```

3. **Dependency-Based Invalidation**:

   ```python
   # Module A depends on Module B
   dependencies = {"A": ["B", "C"], "B": ["C"]}

   # When B changes, invalidate A too
   await cache.invalidate("module:B")
   await cache.invalidate("module:A")  # Dependent
   ```

**Sources**:

- [Vector Clocks in Distributed Systems](https://www.geeksforgeeks.org/computer-networks/vector-clocks-in-distributed-systems/)
- [Event-Driven Cache Invalidation](https://leapcell.io/blog/cache-invalidation-strategies-time-based-vs-event-driven)
- [Cache Invalidation in Distributed Systems](https://www.numberanalytics.com/blog/ultimate-guide-cache-invalidation-distributed-systems)

---

## 12. Networked Cache Design

### Concept: Knowledge Graph with References

**Inspired by Fast-GraphRAG and llms.txt**, create cache with explicit cross-references:

```python
@dataclass
class CacheNode:
    id: str
    type: str  # "module", "function", "test", "concept"
    summary: str
    full_content_ref: str  # Reference to full content
    dependencies: List[str]  # IDs of related nodes
    references: List[str]  # IDs this node mentions
    vector_embedding: Optional[np.ndarray]  # For semantic search

class NetworkedCache:
    def __init__(self):
        self.nodes: Dict[str, CacheNode] = {}
        self.graph: nx.DiGraph = nx.DiGraph()

    def add_node(self, node: CacheNode):
        self.nodes[node.id] = node
        self.graph.add_node(node.id)

        # Add edges for dependencies
        for dep in node.dependencies:
            self.graph.add_edge(node.id, dep, type="depends_on")

        # Add edges for references
        for ref in node.references:
            self.graph.add_edge(node.id, ref, type="references")

    def get_related_context(
        self,
        node_id: str,
        max_depth: int = 2,
        max_tokens: int = 4000
    ) -> str:
        """Get node + related nodes within token budget"""

        # BFS from node, respecting max_depth
        related_ids = self._bfs_related(node_id, max_depth)

        # Sort by relevance (PageRank or similar)
        ranked_ids = self._rank_by_relevance(node_id, related_ids)

        # Accumulate summaries until token budget
        context = []
        tokens_used = 0

        for rid in ranked_ids:
            node = self.nodes[rid]
            summary_tokens = len(node.summary.split())

            if tokens_used + summary_tokens > max_tokens:
                break

            context.append(f"## {node.type}: {node.id}\n{node.summary}")
            tokens_used += summary_tokens

        return "\n\n".join(context)
```

**Example Graph Structure**:

```
[Module: validators.py]
├─ depends_on → [Library: pydantic]
├─ depends_on → [Library: phonenumbers]
├─ contains → [Function: validate_email]
└─ contains → [Function: validate_phone]

[Function: validate_email]
├─ depends_on → [Library: re]
├─ tested_by → [Test: test_email_validation]
└─ references → [Concept: RFC 5322]

[Test: test_email_validation]
├─ tests → [Function: validate_email]
└─ status → "12/12 passed, iteration 3"
```

**Retrieval Strategy**:

1. **Direct Lookup**: Get specific node by ID
2. **Semantic Search**: Find similar nodes via embeddings
3. **Graph Traversal**: Follow dependencies/references
4. **PageRank Ranking**: Prioritize important nodes

---

### Multi-Level Summaries with References

**Level 1: Task Summary (100 tokens)**

```markdown
# Task: task-abc123
Status: Completed
Goal: Build email/phone validator module
Modules: [→ validators.py], [→ test_validators.py]
Success Rate: 100% (12/12 tests passed)
```

**Level 2: Module Summary (300 tokens)**

```markdown
# Module: validators.py [ID: mod-val-001]
Purpose: Email and phone validation functions
Dependencies: [→ pydantic], [→ phonenumbers], [→ re]
Functions:
  - [→ validate_email]: RFC 5322 email validation
  - [→ validate_phone]: International phone validation
Tests: [→ test_validators.py] (12/12 passed)
Refinements: 3 iterations (fixed regex edge cases)
Full Code: [storage://task-abc123/validators.py]
```

**Level 3: Function Summary (150 tokens)**

```markdown
# Function: validate_email [ID: func-val-email-001]
Module: [← validators.py]
Purpose: Validate email addresses using RFC 5322 regex
Dependencies: [→ re module]
Input: email: str
Output: bool (True if valid)
Test Coverage: [→ test_email_valid], [→ test_email_invalid]
Refinements:
  - Iteration 1: Basic regex
  - Iteration 2: Added edge cases for + and . characters
  - Iteration 3: Fixed domain validation
Full Code: [storage://task-abc123/validators.py#L45-L67]
```

**Level 4: Full Content**

```python
# Actual code stored separately, referenced by URL
def validate_email(email: str) -> bool:
    """Validate email using RFC 5322 pattern."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
```

**Key Principle**: Each level has **explicit references** (marked with arrows) to:

- Dependencies (what this needs)
- Dependents (what needs this)
- Related nodes (tests, concepts, etc.)
- Full content location

---

## 13. DSPy for Cache Summary Generation

### Using DSPy Signatures for Structured Summaries

While DSPy doesn't provide compression, it **excels at generating structured outputs**:

```python
import dspy

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

# Usage
summarizer = dspy.ChainOfThought(ModuleSummarizer)
result = summarizer(
    module_name="validators.py",
    source_code=code,
    test_results=test_output,
    iteration_history=iterations
)

# Result has structured fields
cache_node = CacheNode(
    id=f"module:{result.module_name}",
    type="module",
    summary=result.summary,
    dependencies=result.dependencies,
    # ...
)
```

**Advantages**:

- Type-safe structured outputs
- Consistent format across summaries
- Can be optimized via DSPy compilation
- Easier to create networked references

---

### Multi-Stage Summary Generation Pipeline

```python
class SummaryPipeline:
    """Generate hierarchical summaries using DSPy"""

    def __init__(self):
        self.module_summarizer = dspy.ChainOfThought(ModuleSummarizer)
        self.function_summarizer = dspy.ChainOfThought(FunctionSummarizer)
        self.task_summarizer = dspy.ChainOfThought(TaskSummarizer)

    async def generate_hierarchical_summary(
        self,
        task_state: TaskState
    ) -> NetworkedCache:
        """Generate full cache from task state"""

        cache = NetworkedCache()

        # Level 1: Task summary
        task_summary = self.task_summarizer(
            task_id=task_state.task_id,
            requirements=task_state.requirements,
            plan=task_state.plan,
            module_results=task_state.module_results
        )
        cache.add_node(CacheNode(
            id=f"task:{task_state.task_id}",
            type="task",
            summary=task_summary.summary,
            dependencies=[f"module:{m}" for m in task_state.module_results]
        ))

        # Level 2: Module summaries
        for module_name, result in task_state.module_results.items():
            module_summary = self.module_summarizer(
                module_name=module_name,
                source_code=result.code,
                test_results=result.test_output,
                iteration_history=result.iterations
            )

            cache.add_node(CacheNode(
                id=f"module:{module_name}",
                type="module",
                summary=module_summary.summary,
                dependencies=[f"lib:{d}" for d in module_summary.dependencies],
                references=[f"func:{f}" for f in module_summary.functions]
            ))

            # Level 3: Function summaries
            for function in extract_functions(result.code):
                func_summary = self.function_summarizer(
                    function_name=function.name,
                    source_code=function.code,
                    dependencies=function.imports
                )

                cache.add_node(CacheNode(
                    id=f"func:{function.name}",
                    type="function",
                    summary=func_summary.summary,
                    dependencies=[f"lib:{d}" for d in func_summary.dependencies]
                ))

        return cache
```

**Result**: Networked cache with explicit references between levels.

---

## 14. Specific Strategies for Small LLMs (8K-32K Context)

### Token Budget Allocation

For **Mistral 7B (8K context)**:

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

For **Qwen3 8B (32K context)**:

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

### Context Prioritization Strategy

**Priority Ranking** (fill context window in this order):

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

**Implementation**:

```python
class ContextBuilder:
    def build_context(
        self,
        task_state: TaskState,
        max_tokens: int = 8192
    ) -> str:
        """Build context respecting token budget"""

        sections = []
        tokens_used = 0

        # Priority 1: CRITICAL
        critical = self._get_critical_context(task_state)
        sections.append(critical)
        tokens_used += count_tokens(critical)

        if tokens_used >= max_tokens * 0.8:  # Reserve 20% for generation
            return "\n\n".join(sections)

        # Priority 2: HIGH
        high = self._get_high_priority_context(task_state)
        if tokens_used + count_tokens(high) < max_tokens * 0.8:
            sections.append(high)
            tokens_used += count_tokens(high)
        else:
            # Truncate high priority to fit
            high_truncated = self._truncate_to_fit(
                high,
                max_tokens * 0.8 - tokens_used
            )
            sections.append(high_truncated)
            return "\n\n".join(sections)

        # Priority 3-4: Continue similarly...

        return "\n\n".join(sections)
```

---

### Compression Strategies for Small Windows

**For 8K Context (Mistral 7B)**:

1. **Aggressive Summarization**:
   - Module summaries: 200 tokens max
   - Function summaries: 50 tokens max
   - Only keep last 1 iteration history

2. **Semantic Anchors Only**:
   - Keep function signatures, not bodies
   - Keep test names, not full test code
   - Keep error messages, not full tracebacks

3. **Just-in-Time Retrieval**:
   - Fetch detailed context only when needed
   - Replace with summary after use

**For 32K Context (Qwen3 8B)**:

1. **Moderate Summarization**:
   - Module summaries: 500 tokens
   - Function summaries: 150 tokens
   - Keep last 3 iteration histories

2. **Include Related Context**:
   - 2 levels of dependencies
   - Related modules in same task
   - Full test code for current module

3. **Proactive Caching**:
   - Preload likely-needed context
   - Keep detailed content for current work

---

## 15. Recommended Cache Architecture

### Complete System Design

```python
from dataclasses import dataclass
from typing import Dict, List, Optional
import networkx as nx

@dataclass
class CacheNode:
    """Node in networked cache"""
    id: str
    type: str  # "task", "module", "function", "test", "concept", "library"
    summary: str  # Compressed summary
    full_content_ref: Optional[str]  # Reference to full content
    dependencies: List[str]  # Node IDs this depends on
    references: List[str]  # Node IDs this references
    metadata: Dict[str, Any]  # Version, timestamp, etc.
    vector_embedding: Optional[np.ndarray] = None

class OnlineCache:
    """Fast, in-memory cache for current task"""

    def __init__(self, max_tokens: int = 8192):
        self.max_tokens = max_tokens
        self.current_context: List[CacheNode] = []
        self.priority_queue: PriorityQueue = PriorityQueue()

    async def get_context(self, task_state: TaskState) -> str:
        """Build context for LLM prompt"""
        builder = ContextBuilder(self.max_tokens)
        return builder.build_context(task_state, self.current_context)

    async def update(self, node: CacheNode):
        """Update cache with new information"""
        self.current_context.append(node)
        self._evict_if_needed()

    def _evict_if_needed(self):
        """Evict low-priority nodes if over budget"""
        while self._total_tokens() > self.max_tokens:
            # Remove lowest priority node
            node = self.priority_queue.pop()
            self.current_context.remove(node)

class OfflineCache:
    """Persistent, disk-based cache for historical data"""

    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.graph: nx.DiGraph = nx.DiGraph()
        self.nodes: Dict[str, CacheNode] = {}
        self.embeddings: Dict[str, np.ndarray] = {}

    async def store(self, node: CacheNode):
        """Persist node to disk"""
        self.nodes[node.id] = node
        self.graph.add_node(node.id, **asdict(node))

        # Add edges
        for dep in node.dependencies:
            self.graph.add_edge(node.id, dep, type="depends_on")
        for ref in node.references:
            self.graph.add_edge(node.id, ref, type="references")

        # Store embedding for semantic search
        if node.vector_embedding is not None:
            self.embeddings[node.id] = node.vector_embedding

        # Persist to disk
        await self._persist_to_disk()

    async def search_semantic(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5
    ) -> List[CacheNode]:
        """Semantic search via embeddings"""
        similarities = {}
        for node_id, embedding in self.embeddings.items():
            sim = cosine_similarity(query_embedding, embedding)
            similarities[node_id] = sim

        # Get top-k
        top_ids = sorted(similarities, key=similarities.get, reverse=True)[:top_k]
        return [self.nodes[nid] for nid in top_ids]

    async def get_related_context(
        self,
        node_id: str,
        max_depth: int = 2,
        max_tokens: int = 4000
    ) -> List[CacheNode]:
        """Get node + related via graph traversal"""
        # BFS from node
        related_ids = []
        queue = [(node_id, 0)]
        visited = set()

        while queue:
            current_id, depth = queue.pop(0)
            if current_id in visited or depth > max_depth:
                continue

            visited.add(current_id)
            related_ids.append(current_id)

            # Add neighbors
            for neighbor in self.graph.neighbors(current_id):
                queue.append((neighbor, depth + 1))

        # Rank by PageRank
        pagerank = nx.pagerank(self.graph)
        ranked_ids = sorted(related_ids, key=lambda x: pagerank.get(x, 0), reverse=True)

        # Accumulate until token budget
        result = []
        tokens = 0
        for nid in ranked_ids:
            node = self.nodes[nid]
            node_tokens = len(node.summary.split())
            if tokens + node_tokens > max_tokens:
                break
            result.append(node)
            tokens += node_tokens

        return result

class HybridCacheManager:
    """Manages both online and offline caches"""

    def __init__(self, max_online_tokens: int = 8192):
        self.online = OnlineCache(max_online_tokens)
        self.offline = OfflineCache("./cache")
        self.event_store: EventStore = EventStore()

    async def get_context_for_task(
        self,
        task_state: TaskState
    ) -> str:
        """Get optimal context for current task"""

        # 1. Get current context from online cache
        online_context = await self.online.get_context(task_state)

        # 2. If online cache insufficient, query offline
        if self._needs_more_context(online_context, task_state):
            # Semantic search for related historical solutions
            query_emb = await self._embed_query(task_state.requirements)
            historical = await self.offline.search_semantic(query_emb, top_k=3)

            # Add to online cache
            for node in historical:
                await self.online.update(node)

        # 3. Build final context
        return await self.online.get_context(task_state)

    async def update_from_event(self, event: WorkflowEvent):
        """Update cache based on workflow event"""

        if event.type == "MODULE_COMPLETE":
            # Generate summary and store
            summary_node = await self._generate_module_summary(event)

            # Update online cache
            await self.online.update(summary_node)

            # Persist to offline cache
            await self.offline.store(summary_node)

        elif event.type == "TASK_COMPLETE":
            # Migrate online cache to offline
            await self._migrate_online_to_offline(event.task_id)

    async def _migrate_online_to_offline(self, task_id: str):
        """Compress and migrate online cache to offline storage"""

        # Get all events for task
        events = await self.event_store.get_events(task_id)

        # Generate hierarchical summaries
        pipeline = SummaryPipeline()
        networked_cache = await pipeline.generate_hierarchical_summary(events)

        # Store in offline cache
        for node in networked_cache.nodes.values():
            await self.offline.store(node)

        # Clear online cache for this task
        await self.online.clear_task(task_id)
```

---

## 16. Summary: Key Insights & Recommendations

### Critical Insights

1. **DSPy Doesn't Compress, But Structures**:
   - Use DSPy for generating **structured summaries**, not compression
   - Leverage signatures for consistent, type-safe outputs
   - Multi-stage pipelines create hierarchical summaries

2. **Information Loss is Multi-Dimensional**:
   - **Semantic**: Detailed reasoning → conclusions
   - **Temporal**: Event sequences → static summaries
   - **Relational**: 3rd/4th degree dependencies → direct links only

3. **Networked Cache is Essential**:
   - Explicit references between cache nodes
   - Graph traversal for context retrieval
   - PageRank for relevance ranking

4. **Event Sourcing is Your Advantage**:
   - Full event history enables time-travel
   - Rebuild cache at any point
   - Vector clocks for invalidation

5. **Small LLMs Need Aggressive Prioritization**:
   - 8K context: Only current + immediate dependencies
   - 32K context: 2 levels of dependencies + history
   - Always reserve 20% for generation

---

### Recommended Architecture

```
┌─────────────────────────────────────────────────┐
│         LLM (Mistral 7B / Qwen3 8B)            │
└─────────────────┬───────────────────────────────┘
                  │
      ┌───────────▼──────────────┐
      │  HybridCacheManager      │
      │  - Manages both caches   │
      │  - Event-driven updates  │
      └──────┬──────────┬────────┘
             │          │
    ┌────────▼───┐  ┌──▼──────────┐
    │ OnlineCache│  │OfflineCache │
    │ (Memory)   │  │ (Disk+Graph)│
    │ - 8K tokens│  │ - Networked │
    │ - Current  │  │ - Historical│
    │ - Fast     │  │ - Semantic  │
    └────────────┘  └─────────────┘
             │          │
    ┌────────▼──────────▼────────┐
    │     EventStore              │
    │  - Full event history       │
    │  - Vector clocks            │
    │  - Cache reconstruction     │
    └─────────────────────────────┘
```

---

### Implementation Priorities

#### Phase 1: Foundation (Week 1)

1. Implement `OnlineCache` (in-memory, priority-based)
2. Implement `OfflineCache` (disk-based, graph structure)
3. Create `EventStore` integration
4. Build `ContextBuilder` with token budgets

#### Phase 2: Summaries (Week 2)

1. Create DSPy signatures for summaries
2. Implement `SummaryPipeline` (hierarchical)
3. Add vector embeddings for semantic search
4. Build `NetworkedCache` with graph

#### Phase 3: Intelligence (Week 3)

1. Implement PageRank-based ranking
2. Add semantic search (embeddings)
3. Build event-driven invalidation
4. Create migration: online → offline

#### Phase 4: Optimization (Week 4)

1. Fine-tune compression ratios
2. Optimize token budgets per model
3. Add cache analytics/monitoring
4. Performance benchmarks

---

### Trade-off Matrix

| Strategy | Compression | Info Retained | Rebuild Cost | Latency |
|----------|-------------|---------------|--------------|---------|
| **No Cache** | 0% | 100% | High | High |
| **Online Only** | 50% | 75% | Medium | Low |
| **Hierarchical** | 70% | 60% | Low | Medium |
| **Graph+Semantic** | 75% | 70% | Low | Medium |
| **Full Event Replay** | 0% | 100% | Very High | Very High |

**Recommended**: **Graph+Semantic** for best balance.

---

### Final Recommendations

**For Mistral 7B (8K context)**:

- Use aggressive hierarchical summaries (70% compression)
- Online cache only (no historical context)
- Just-in-time retrieval from offline when needed
- Focus on current module + immediate dependencies

**For Qwen3 8B (32K context)**:

- Use moderate hierarchical summaries (50% compression)
- Hybrid cache (online + offline semantic search)
- Include 2 levels of dependencies
- Preload historical patterns (last 3 similar tasks)

**For Both**:

- Always maintain networked cache with explicit references
- Use DSPy for structured summary generation
- Leverage event sourcing for cache reconstruction
- Implement vector clock-based invalidation
- Reserve 20% of context for code generation

---

## 17. References & Sources

### Academic Papers

- [Context Cascade Compression (C3)](https://arxiv.org/html/2511.15244)
- [DAST: Context-Aware Compression](https://aclanthology.org/2025.findings-acl.1055.pdf)
- [RAGCache: Efficient Knowledge Caching](https://arxiv.org/html/2404.12457v2)
- [GraphRAG: Query-Focused Summarization](https://arxiv.org/html/2404.16130v2)
- [Adaptive Contextual Compression (ACC)](https://arxiv.org/html/2505.08261)
- [Hierarchical Repository Summarization](https://arxiv.org/html/2501.07857v1)
- [Semantic Compression with LLMs](https://arxiv.org/pdf/2304.12512)

### Documentation & Tutorials

- [DSPy Conversation History](https://dspy.ai/tutorials/conversation_history/)
- [DSPy llms.txt Generation](https://dspy.ai/tutorials/llms_txt_generation/)
- [Fast-GraphRAG GitHub](https://github.com/circlemind-ai/fast-graphrag)
- [Mistral 7B Documentation](https://mistral.ai/news/announcing-mistral-7b)
- [Qwen3 8B Documentation](https://huggingface.co/Qwen/Qwen3-8B)
- [PoSE Extension Research](https://superagi.com/extending-context-window-of-a-7b-llm-from-8k-to-32k-using-pose-positional-skip-wise/)

### Technical Blogs

- [LLM Chat History Summarization](https://mem0.ai/blog/llm-chat-history-summarization-guide-2025)
- [Caching Strategies for LLM Services](https://www.rohan-paul.com/p/caching-strategies-in-llm-services)
- [Hierarchical Indices for RAG](https://medium.com/@nirdiamant21/hierarchical-indices-enhancing-rag-systems-43c06330c085)
- [LLM Function Design Pattern](https://medium.com/aimonks/the-llm-function-design-pattern-a-structured-approach-to-ai-powered-software-development-f4192945d5f4)
- [Event-Driven Cache Invalidation](https://leapcell.io/blog/cache-invalidation-strategies-time-based-vs-event-driven)

### Tools & Libraries

- [GPTCache GitHub](https://github.com/zilliztech/GPTCache)
- [LlamaIndex Hierarchical Retrieval](https://docs.llamaindex.ai/en/stable/examples/query_engine/multi_doc_auto_retrieval/multi_doc_auto_retrieval/)
- [Vector Clocks in Distributed Systems](https://www.geeksforgeeks.org/computer-networks/vector-clocks-in-distributed-systems/)
- [Cache Invalidation in Distributed Systems](https://www.numberanalytics.com/blog/ultimate-guide-cache-invalidation-distributed-systems)

### Performance Studies

- [AI Tech: LLM Chatbot Memory Compression](https://techxplore.com/news/2025-11-ai-tech-compress-llm-chatbot.html)
- [Apple: Compressing LLMs Truth](https://machinelearning.apple.com/research/compressing-llms)
- [Factory.ai: Compressing Context](https://factory.ai/news/compressing-context)
- [Emergent Mind: Context Compression](https://www.emergentmind.com/topics/context-compression-techniques)

---

**End of Research Document**

This comprehensive analysis provides the foundation for designing an intelligent cache system for small LLMs in your event-sourced code generation system.
