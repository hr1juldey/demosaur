"""
Context retrieval helpers for context management system.

Contains memory retrieval and context building functionality.
"""

from typing import Dict, Any, List
from src.context.context_manager import ContextManager, ContextSnapshot
from src.memory.mem0_client import Mem0Client


def retrieve_relevant_memories(context_manager: ContextManager, query: str,
                              user_id: str, limit: int) -> str:
    """Retrieve relevant memories from Mem0."""
    try:
        memory_results = context_manager.mem0_client.search_memories(
            query=query,
            user_id=user_id,
            limit=limit
        )

        if memory_results["success"] and memory_results["results"]:
            memory_parts = ["## Relevant Memories from Persistent Storage:"]
            for i, result in enumerate(memory_results["results"]):
                memory_parts.append(f"### Memory {i+1} (Score: {result['score']:.2f}):")
                memory_parts.append(result["memory"])
                memory_parts.append("")
            return "\n".join(memory_parts)
        else:
            return "## No Relevant Memories Found in Persistent Storage"
    except Exception as e:
        return f"## Error Retrieving Memories: {str(e)}"


def build_recent_context_from_snapshots(recent_snapshots: List[ContextSnapshot]) -> str:
    """
    Build context string from recent snapshots.

    PASSING CRITERIA:
    ✅ Context built properly from snapshots
    ✅ Proper formatting applied
    ✅ Returns meaningful context string
    """
    if not recent_snapshots:
        return "No recent context available."

    context_parts = ["## Recent Context:"]
    for snapshot in recent_snapshots:
        context_parts.append(f"### {snapshot.context_type.title()} ({snapshot.timestamp}):")
        context_parts.append(snapshot.content)
        context_parts.append("")  # Blank line between entries

    return "\n".join(context_parts)