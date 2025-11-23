# Dead Code Detection System - Implementation Plan

## Research Summary

### The Problem

Dead code accumulation in AI-generated codebases causes:
1. **Context Window Overflow** - Analogous to memory leaks
2. **Code Quality Degradation** - Confusing unused code
3. **Maintenance Burden** - Extra code to read/understand
4. **Token Waste** - LLM processes unused code

---

## Available Tools Analysis

### 1. Vulture ⭐ RECOMMENDED

**Source**: [Vulture GitHub](https://github.com/jendrikseipp/vulture)

**Capabilities**:
- Detects unused: imports, variables, functions, classes, attributes, properties
- Detects unreachable code (after return/break/continue/raise)
- Confidence scores: 60%-100% (100% = definitely dead)
- AST-based static analysis

**Strengths**:
- Comprehensive detection
- Low false positives with confidence filtering
- Simple CLI interface
- JSON output available

**Limitations**:
- Can't detect dynamically called code
- May flag metaprogramming as unused

---

### 2. deadcode (Alternative)

**Source**: [deadcode PyPI](https://pypi.org/project/deadcode/)

**Capabilities**:
- Whole codebase analysis
- `--fix` option for auto-removal
- DCXXX diagnostic codes

**Strengths**:
- Auto-fix capability
- Newer, more comprehensive than Vulture

**Limitations**:
- Less mature than Vulture
- Smaller community

---

### 3. Ruff (Already Have)

**Source**: [Ruff unused-import](https://docs.astral.sh/ruff/rules/unused-import/)

**Capabilities**:
- F401: Unused imports
- F841: Unused local variables
- Auto-fix with `--fix`

**Limitations**:
- Only local scope (not global functions/classes)
- No unreachable code detection

---

### 4. Pyright (Already Have)

**Capabilities**:
- reportUnusedImport
- reportUnusedVariable
- reportUnusedParameter

**Limitations**:
- Primarily a type checker
- Limited dead code detection

---

### 5. coverage.py + pytest

**Source**: [coverage.py docs](https://coverage.readthedocs.io/)

**Capabilities**:
- Runtime execution tracking
- `--source=.` finds completely unused files
- Integration with Vulture possible

**Usage**: Complement static analysis with runtime data

---

## Recommended Approach

### Multi-Layered Detection

```
Layer 1: Ruff (F401, F841)          ← Already integrated
         ↓
Layer 2: Vulture (comprehensive)    ← NEW: Primary detector
         ↓
Layer 3: coverage.py (unused files) ← NEW: Runtime complement
         ↓
Layer 4: Manual review (confidence < 100%)
```

---

## Implementation Architecture

### Files to Create (All ≤100 lines)

1. **src/deadcode/detector.py**
   - VultureDetector class
   - Runs vulture on code
   - Parses JSON output

2. **src/deadcode/analyzer.py**
   - DeadCodeAnalyzer class
   - Combines Ruff + Vulture results
   - Confidence scoring

3. **src/deadcode/reporter.py**
   - DeadCodeReporter class
   - Formats reports for display
   - Groups by type (imports, functions, etc.)

4. **src/deadcode/cleaner.py**
   - DeadCodeCleaner class
   - Auto-removes high-confidence dead code
   - Creates backup before removal

5. **src/mcp/deadcode_tools.py**
   - MCP tools for dead code detection
   - `detect_dead_code(task_id, module_name)`
   - `clean_dead_code(task_id, module_name, min_confidence)`

---

## Integration Points

### 1. During Code Generation

```python
# In src/codegen/generator.py
async def generate(...):
    code = await generate_code(...)

    # Quality checks (existing)
    code = await quality_checker.check(code)

    # Dead code detection (NEW)
    dead_code = await dead_code_detector.detect(code)
    if dead_code.high_confidence_items:
        code = await dead_code_cleaner.remove(code, min_confidence=100)

    return code
```

### 2. During Refinement

```python
# In src/refinement/refiner.py
async def refine(...):
    # Refine code
    refined = await refine_logic(...)

    # Clean dead code (NEW)
    cleaned = await remove_dead_code(refined, min_confidence=90)

    return cleaned
```

### 3. Post-Generation Analysis

```python
# MCP Tool
@mcp.tool()
async def analyze_dead_code(task_id: str, module_name: str):
    """Analyze generated code for dead code"""
    code = get_module_code(task_id, module_name)

    detector = DeadCodeDetector()
    results = await detector.analyze(code)

    return {
        "total_items": len(results),
        "by_confidence": {
            "100": [item for item in results if item.confidence == 100],
            "80-99": [item for item in results if 80 <= item.confidence < 100],
            "60-79": [item for item in results if 60 <= item.confidence < 80]
        },
        "by_type": {
            "imports": [item for item in results if item.type == "import"],
            "functions": [item for item in results if item.type == "function"],
            "classes": [item for item in results if item.type == "class"],
            "variables": [item for item in results if item.type == "variable"]
        }
    }
```

---

## Data Models

```python
@dataclass
class DeadCodeItem:
    type: Literal["import", "function", "class", "variable", "property", "unreachable"]
    name: str
    line: int
    confidence: int  # 60-100
    file: str
    reason: str  # Why it's considered dead

@dataclass
class DeadCodeReport:
    items: List[DeadCodeItem]
    total_items: int
    high_confidence_count: int  # confidence >= 90
    removable_lines: int
    potential_token_savings: int
```

---

## MCP Resources

```python
@mcp.resource("deadcode://task/{task_id}/module/{module_name}")
async def get_dead_code_report(task_id: str, module_name: str) -> str:
    """Get dead code analysis for a module"""

@mcp.resource("deadcode://task/{task_id}/summary")
async def get_dead_code_summary(task_id: str) -> str:
    """Get dead code summary for all modules"""
```

---

## MCP Tools

```python
@mcp.tool()
async def detect_dead_code(
    task_id: str,
    module_name: str,
    min_confidence: int = 80
) -> dict:
    """Detect dead code in a module"""

@mcp.tool()
async def clean_dead_code(
    task_id: str,
    module_name: str,
    min_confidence: int = 100,
    auto_apply: bool = False
) -> dict:
    """Clean dead code from a module"""
```

---

## Installation Requirements

```txt
# requirements.txt additions
vulture>=2.11  # Dead code detection
```

---

## Usage Examples

### Example 1: Detect During Generation

```python
# Generated code with dead code
code = '''
import os  # Unused
import sys

def used_function():
    return sys.version

def unused_function():  # Never called
    return "hello"

x = 10  # Unused variable
'''

# Detect
report = await detector.detect(code)
# Returns:
# - import os (100% confidence)
# - unused_function (80% confidence)
# - x variable (100% confidence)

# Auto-clean high confidence
cleaned = await cleaner.clean(code, min_confidence=100)
# Removes: import os, x variable
# Keeps: unused_function (only 80%)
```

### Example 2: Post-Generation Analysis

```python
# After task completes
report = await analyze_dead_code("task-123", "validator.py")

# Claude sees:
{
    "total_items": 5,
    "high_confidence": 3,
    "potential_token_savings": 150,
    "items": [
        {"type": "import", "name": "os", "confidence": 100},
        {"type": "function", "name": "old_validate", "confidence": 90},
        ...
    ]
}

# Claude decides to clean
await clean_dead_code("task-123", "validator.py", min_confidence=90)
```

---

## Configuration

```python
# src/common/config.py additions
class Settings:
    # Dead code detection
    enable_dead_code_detection: bool = True
    dead_code_min_confidence: int = 80
    dead_code_auto_clean: bool = False  # Safe default
    dead_code_auto_clean_threshold: int = 100  # Only 100% confidence
```

---

## Success Metrics

- **Detection Accuracy**: % of dead code found
- **False Positive Rate**: < 10% for confidence >= 90
- **Token Savings**: Average tokens saved per module
- **Context Window Efficiency**: Reduction in code size

---

## Implementation Phases

### Phase 1: Detection (Week 1)
- [x] Install vulture
- [ ] Create detector.py
- [ ] Create analyzer.py
- [ ] Create reporter.py
- [ ] Unit tests

### Phase 2: Cleaning (Week 1)
- [ ] Create cleaner.py
- [ ] Backup mechanism
- [ ] Safety checks
- [ ] Integration tests

### Phase 3: MCP Integration (Week 2)
- [ ] Create deadcode_tools.py
- [ ] Add MCP resources
- [ ] Add MCP tools
- [ ] Documentation

### Phase 4: Generator Integration (Week 2)
- [ ] Integrate into code generator
- [ ] Integrate into refiner
- [ ] Performance testing
- [ ] Documentation updates

---

## References

- [Vulture GitHub](https://github.com/jendrikseipp/vulture)
- [deadcode PyPI](https://pypi.org/project/deadcode/)
- [Ruff unused-import](https://docs.astral.sh/ruff/rules/unused-import/)
- [coverage.py docs](https://coverage.readthedocs.io/)
- [Dead Code Detection in Python](https://medium.com/@kinjaldave299/dead-code-detection-in-python-6bbec093b86b)
