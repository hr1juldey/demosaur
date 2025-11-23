# Code Intern MCP Server - Project Overview

## Vision

An MCP server that acts as a "junior developer intern" powered by DSPy and local Ollama models. It performs exploratory coding, iterative testing, and refinement - offloading expensive token-intensive work from Claude to free local models.

## The Problem

When Claude writes code, it:
- Spends many tokens learning libraries from docs
- Does trial-and-error coding (failed/semi-failed attempts)
- Lacks execution environment for testing
- Cannot iteratively refine based on test results
- Costs accumulate rapidly on output tokens

## The Solution

A DSPy-powered MCP server that:
1. **Gathers Requirements** - Asks structured questions about goals, approach, tech stack
2. **Plans Implementation** - Decides modules, tests, architecture
3. **Iterative Development** - Write → Test → Fix → Repeat loop
4. **Executes Code** - Uses Deno/Python sandbox via DSPy ProgramOfThought
5. **Generates Reports** - Error trails, performance metrics, test results
6. **Returns MVPs** - Delivers tested, working code to Claude

## Key Benefits

- **Cost Reduction**: 70-90% reduction in Claude output tokens
- **Quality**: Code is pre-tested and refined
- **Speed**: Parallel exploration of approaches
- **Transparency**: Full audit trail of attempts
- **Intervention**: Claude can monitor and guide

## Technology Stack

- **DSPy**: Framework for programming LMs
- **Ollama**: Local LLM execution (mistral:7b, qwen3:8b, etc)
- **Deno**: Sandboxed code execution
- **pytest**: Unit/integration testing
- **MCP**: Model Context Protocol for Claude integration
- **asyncio**: Async operation and monitoring

## Core Modules

1. **Requirement Gatherer** - Interactive Q&A system
2. **Code Generator** - DSPy ProgramOfThought + CodeAct
3. **Test Generator** - Automatic pytest generation
4. **Executor** - Sandboxed code/test execution
5. **Refiner** - Iterative improvement with performance scoring
6. **Logger** - Async, switchable logging system
7. **MCP Server** - Protocol handler and API

## Success Metrics

- Code quality: % of tests passing
- Performance: Time/space complexity scores
- Reliability: Success rate of MVPs
- Cost savings: Token reduction vs direct Claude coding
