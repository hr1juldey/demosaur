# DSPy Key Findings & Usage Patterns

## PythonInterpreter

**Source**: [DSPy PythonInterpreter API](https://dspy.ai/api/tools/PythonInterpreter/)

**Requires**: Deno installation

**Key Features**:
- Sandboxed code execution using Deno + Pyodide
- Context manager support
- Fine-grained permissions

**Usage**:
```python
from dspy.primitives import PythonInterpreter

# Basic usage
code_string = "print('Hello'); 1 + 2"
with PythonInterpreter() as interp:
    output = interp(code_string)

# With permissions
with PythonInterpreter(
    enable_read_paths=["/tmp"],
    enable_write_paths=["/tmp/output"],
    enable_env_vars=["API_KEY"],
    enable_network_access=["api.example.com"],
    sync_files=True
) as interp:
    result = interp(code)
```

## ProgramOfThought (POT)

**Source**: [DSPy ProgramOfThought Tutorial](https://dspy.ai/tutorials/program_of_thought/)

**Purpose**: Generate code AND execute it to verify correctness

**Usage**:
```python
from dspy import ProgramOfThought

# Simple signature
pot = dspy.ProgramOfThought("question -> answer")
result = pot(question="what is 1+1?")

# Custom signature
class BasicGenerateAnswer(dspy.Signature):
    question: str = dspy.InputField()
    answer: str = dspy.OutputField()

pot = dspy.ProgramOfThought(BasicGenerateAnswer)
result = pot(question="factorial of 6")
# Generates: def fact(n): return 1 if n==0 else n*fact(n-1); fact(6)
# Executes: 720
```

**Benefits**:
- Mitigates computation errors vs ChainOfThought
- Improves correctness for numerical/logical queries
- Returns both generated code and execution result

## CodeAct

**Source**: [DSPy CodeAct API](https://dspy.ai/api/modules/CodeAct/)

**Purpose**: Generate code that uses tools to solve problems

**Usage**:
```python
from dspy import CodeAct

def factorial(n: int) -> int:
    """Calculate factorial of n"""
    return 1 if n == 0 else n * factorial(n-1)

act = CodeAct("n -> factorial_result", tools=[factorial])
result = act(n=5)  # Returns 120
```

**Key Points**:
- Generates Python code snippets
- Can use provided tools + Python stdlib
- Executes generated code

## ReAct

**Source**: [DSPy ReAct API](https://dspy.ai/api/modules/ReAct/)

**Purpose**: Reasoning + Acting pattern for tool-using agents

**Usage**:
```python
from dspy import ReAct

def get_weather(city: str) -> str:
    """Get current weather for a city"""
    return f"Weather in {city}: Sunny, 72°F"

def search_web(query: str) -> str:
    """Search the web for information"""
    return f"Search results for: {query}"

agent = ReAct(
    signature="question -> answer",
    tools=[get_weather, search_web],
    max_iters=5
)

result = agent(question="What's the weather in Paris?")
```

**Features**:
- Trajectory tracking (full history of reasoning + tool calls)
- Error recovery for failed tool calls
- Signature polymorphism (works with any signature)

**Requirements**:
- Tools must have docstrings
- Tools must have type hints for arguments

## Refine

**Source**: [DSPy Refine API](https://dspy.ai/api/modules/Refine/)

**Purpose**: Iteratively improve outputs with automatic feedback

**Usage**:
```python
from dspy import Refine, ChainOfThought

# Base module
qa = ChainOfThought("question -> answer")

# Reward function
def one_word_answer(prediction) -> float:
    return 1.0 if len(prediction.answer.split()) == 1 else 0.0

# Refine module
refined = Refine(
    module=qa,
    N=3,  # Max attempts
    reward_fn=one_word_answer,
    threshold=1.0
)

result = refined(question="What color is the sky?")
```

**How it Works**:
1. Runs module N times at temperature=1.0
2. After each attempt (except last), generates feedback
3. Uses feedback as hints for next runs
4. Returns best prediction (highest reward or first > threshold)

**Key Benefits**:
- Automatic feedback generation
- Reward-based selection
- No manual prompt engineering needed

## ChainOfThought

**Purpose**: Add reasoning steps to improve output quality

**Usage**:
```python
from dspy import ChainOfThought

# Inline signature
cot = ChainOfThought("question -> reasoning: str, answer: str")
result = cot(question="Why is the sky blue?")

# Returns: result.reasoning and result.answer
```

## Best Practices for Our Use Case

### 1. Code Generation Pipeline

```python
# Step 1: Plan with ChainOfThought
planner = ChainOfThought(ModulePlannerSignature)
plan = planner(requirements=requirements)

# Step 2: Generate code with ProgramOfThought
code_gen = ProgramOfThought(PythonCodeGenerator)
code_result = code_gen(specification=spec)
# POT executes the code automatically!

# Step 3: If errors, refine
if code_result.has_errors:
    refiner = Refine(
        module=code_gen,
        N=5,
        reward_fn=lambda p: 1.0 if no_errors(p) else 0.0
    )
    code_result = refiner(specification=spec)
```

### 2. Test Generation

```python
# Use ChainOfThought for test generation
test_gen = ChainOfThought(TestGeneratorSignature)
tests = test_gen(code=code, module_spec=spec)
```

### 3. Documentation Fetching

```python
# Use ReAct with tools
doc_fetcher = ReAct(
    signature="library_name, urls -> documentation: str",
    tools=[fetch_url, parse_html],
    max_iters=10
)
docs = doc_fetcher(library_name="FastAPI", urls=urls)
```

### 4. Performance Optimization

```python
# Use Refine with performance scorer
def performance_score(prediction) -> float:
    metrics = measure_performance(prediction.code)
    test_score = run_tests(prediction.code)
    return 0.7 * test_score + 0.3 * metrics.efficiency_score

optimizer = Refine(
    module=code_generator,
    N=10,
    reward_fn=performance_score,
    threshold=0.9
)
```

## Integration Pattern for Code Intern

```python
class CodeInternWorkflow:
    def __init__(self):
        # Planning
        self.planner = ChainOfThought(ModulePlanner)

        # Code generation (with execution)
        self.code_gen = ProgramOfThought(CodeGenerator)

        # Test generation
        self.test_gen = ChainOfThought(TestGenerator)

        # Refinement
        self.refiner = Refine(
            module=self.code_gen,
            N=10,
            reward_fn=self.calculate_score
        )

        # Documentation agent
        self.doc_agent = ReAct(
            signature="query -> docs",
            tools=[fetch_docs, parse_docs],
            max_iters=5
        )

    async def generate_module(self, spec):
        # 1. Generate initial code (POT executes it)
        result = self.code_gen(specification=spec)

        # 2. Generate tests
        tests = self.test_gen(code=result.code, spec=spec)

        # 3. Run tests
        test_results = await run_tests(tests)

        # 4. If score low, refine
        score = self.calculate_score(result, test_results)
        if score < 0.8:
            result = self.refiner(specification=spec)

        return result

    def calculate_score(self, prediction, test_results=None):
        # Combine test pass rate + performance metrics
        pass_rate = test_results.passed / test_results.total
        perf_score = evaluate_complexity(prediction.code)
        return 0.7 * pass_rate + 0.3 * perf_score
```

## References

- [PythonInterpreter API](https://dspy.ai/api/tools/PythonInterpreter/)
- [ProgramOfThought Tutorial](https://dspy.ai/tutorials/program_of_thought/)
- [CodeAct API](https://dspy.ai/api/modules/CodeAct/)
- [ReAct API](https://dspy.ai/api/modules/ReAct/)
- [Refine API](https://dspy.ai/api/modules/Refine/)
- [DSPy Tools](https://dspy.ai/learn/programming/tools/)
- [DSPy Modules](https://dspy.ai/learn/programming/modules/)
