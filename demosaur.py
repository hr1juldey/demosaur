"""
Demosaur MCP Server - Main Entry Point.

A DSPy-powered MCP server that acts as a coding intern,
doing exploratory coding, testing, and refinement using local Ollama models.

Usage:
    python code_intern_server.py
"""

import asyncio
import dspy
from src.common.config import settings
from src.mcp.server import get_server


def configure_dspy():
    """Configure DSPy with Ollama"""
    print(f"Configuring DSPy with model: {settings.model_name}")

    lm = dspy.LM(
        model=f"ollama_chat/{settings.model_name}",
        api_base=settings.ollama_base_url,
        api_key="",  # Not needed for Ollama
        temperature=settings.temperature,
        max_tokens=settings.max_tokens
    )

    dspy.configure(lm=lm)
    print("DSPy configured successfully")


async def demo_workflow():
    """Demo workflow for testing"""
    server = get_server()

    print("\n" + "="*60)
    print("CODE INTERN MCP SERVER - Demo Workflow")
    print("="*60 + "\n")

    # Start task
    print("Starting task...")
    result = await server.start_task("Build an email validator")
    task_id = result["task_id"]
    print(f"Task ID: {task_id}")
    print(f"Question: {result['text']}\n")

    # Answer questions
    answers = [
        "Build an email validation function using regex",
        "Use regex pattern matching with RFC 5322 compliance",
        "Python standard library",
        "re: pattern matching, email validation",
        ""
    ]

    for answer in answers:
        print(f"Answer: {answer or '(skipped)'}")
        result = await server.answer_question(task_id, answer)

        if result.get("status") == "in_progress":
            print(f"Next question: {result['question']['text']}\n")
        elif result.get("status") == "workflow_started":
            print("Workflow started!\n")
            break

    # Monitor progress
    print("Monitoring progress...")
    for _ in range(10):
        await asyncio.sleep(2)
        status = await server.get_status(task_id)
        print(f"Status: {status}")

        if status.get("status") == "completed":
            break

    # Get results
    print("\nGetting final results...")
    results = await server.get_results(task_id)
    print(f"Results: {results}")

    print("\n" + "="*60)
    print("Demo complete!")
    print("="*60)


async def main():
    """Main entry point"""
    try:
        # Configure DSPy
        configure_dspy()

        # Run demo
        await demo_workflow()

    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
