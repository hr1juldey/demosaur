"""
Helper functions for context management system.

Contains utility functions for context building and management.
"""

from typing import List
from src.context.context_manager import ContextSnapshot


def build_recent_context(context_snapshots: List[ContextSnapshot]) -> str:
    """
    Build context string from recent snapshots.
    
    PASSING CRITERIA:
    ✅ Context built properly from snapshots
    ✅ Proper formatting applied
    ✅ Returns meaningful context string
    """
    if not context_snapshots:
        return "No recent context available."

    context_parts = ["## Recent Context:"]
    for snapshot in context_snapshots:
        context_parts.append(f"### {snapshot.context_type.title()} ({snapshot.timestamp}):")
        context_parts.append(snapshot.content)
        context_parts.append("")  # Blank line between entries

    return "\n".join(context_parts)