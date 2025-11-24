"""
Context manager for short-term context and recent history management.

Coordinates immediate context needs with long-term memory from Mem0 system.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
import uuid

from src.memory.core.client import Mem0Client
from src.context.tokens.manager import TokenManager


@dataclass
class ContextSnapshot:
    """Represents a snapshot of context at a point in time"""
    id: str
    timestamp: str
    content: str
    tokens: int
    context_type: str  # "recent", "memory", "planning", "execution"
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextManager:
    """
    Manages immediate context and recent history within 4096 token limit.

    Handles short-term context (current session) and coordinates with
    long-term memory system (Mem0Client) for persistent storage.
    """

    def __init__(self, mem0_client: Mem0Client, max_context_tokens: int = 2048):
        self.mem0_client = mem0_client
        self.token_manager = TokenManager()
        self.max_context_tokens = max_context_tokens

        # Recent context - interactions that happened in current session
        self.recent_context: List[ContextSnapshot] = []
        self.session_start_time = datetime.now().isoformat()
        self.max_recent_items = 50  # Maximum recent context items to maintain

    def add_recent_context(self, content: str, context_type: str = "interaction",
                          metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add recent context to short-term storage.

        PASSING CRITERIA:
        ✅ Content added to recent context
        ✅ Token count calculated correctly
        ✅ Context type tracked properly
        ✅ Returns context ID for reference
        """
        context_id = f"context:{uuid.uuid4()}"

        tokens = self.token_manager.estimate_tokens(content)

        snapshot = ContextSnapshot(
            id=context_id,
            timestamp=datetime.now().isoformat(),
            content=content,
            tokens=tokens,
            context_type=context_type,
            metadata=metadata or {}
        )

        self.recent_context.append(snapshot)

        # Trim recent context to stay within budget and limits
        self._trim_recent_context()

        return context_id

    def _trim_recent_context(self):
        """
        Trim recent context to stay within token and size budgets.

        PASSING CRITERIA:
        ✅ Total tokens stay within recent context budget
        ✅ Most recent items preserved
        ✅ Oldest items removed first when over budget
        ✅ Maximum item count respected
        """
        # First trim by token budget
        current_tokens = sum(ctx.tokens for ctx in self.recent_context)
        context_budget = int(self.max_context_tokens * 0.6)  # Use 60% for recent context

        while current_tokens > context_budget and len(self.recent_context) > 1:
            removed_item = self.recent_context.pop(0)  # Remove oldest first
            current_tokens -= removed_item.tokens

        # Then trim by maximum item count
        if len(self.recent_context) > self.max_recent_items:
            excess_count = len(self.recent_context) - self.max_recent_items
            self.recent_context = self.recent_context[excess_count:]  # Keep newest only

    def get_context_with_memory(self, query: str, user_id: str = "default_user",
                              memory_limit: int = 5, recent_limit: int = 10) -> str:
        """
        Build comprehensive context from recent and long-term memory.

        PASSING CRITERIA:
        ✅ Recent context included
        ✅ Relevant memories retrieved from Mem0
        ✅ Total context within token budget
        ✅ Context properly formatted for LLM
        """
        # Build recent context
        recent_context = self._build_recent_context(recent_limit)

        # Retrieve relevant memories from Mem0
        memory_context = self._get_relevant_memories(query, user_id, memory_limit)

        # Combine contexts
        context_parts = [recent_context, memory_context]
        final_context = "\n\n".join(part for part in context_parts if part.strip())

        # Ensure within token budget
        if not self.token_manager.can_fit_in_budget(final_context):
            final_context = self.token_manager.truncate_to_budget(final_context)

        return final_context

    def _build_recent_context(self, limit: int) -> str:
        """
        Build context string from recent snapshots.

        PASSING CRITERIA:
        ✅ Context built properly from snapshots
        ✅ Proper formatting applied
        ✅ Limited to specified number of items
        ✅ Returns meaningful context string
        """
        if not self.recent_context:
            return ""

        # Take most recent items up to limit
        recent_items = self.recent_context[-min(limit, len(self.recent_context)):]

        context_parts = ["## Recent Context:"]
        for snapshot in recent_items:
            context_parts.append(f"### {snapshot.context_type.title()} ({snapshot.timestamp}):")
            context_parts.append(snapshot.content)
            context_parts.append("")  # Blank line between entries

        return "\n".join(context_parts)

    def _get_relevant_memories(self, query: str, user_id: str, limit: int) -> str:
        """
        Retrieve relevant memories from Mem0 system.

        PASSING CRITERIA:
        ✅ Relevant memories retrieved from persistent storage
        ✅ User isolation maintained
        ✅ Results limited appropriately
        ✅ Proper formatting for context inclusion
        """
        try:
            # Note: We need to call the search method on the Memory instance
            results = self.mem0_client.memory.search(
                query,
                user_ids=[user_id],  # Pass as list in Mem0 format
                limit=limit
            )

            if results and "results" in results and results["results"]:
                memory_parts = ["## Relevant Memories from Long-term Storage:"]
                for i, result in enumerate(results["results"][:limit]):
                    memory_parts.append(f"### Memory {i+1} (Score: {result.get('score', 0.0):.2f}):")
                    memory_parts.append(result.get("memory", ""))
                    memory_parts.append("")
                return "\n".join(memory_parts)
            else:
                return "## No Relevant Memories Found in Long-term Storage"
        except Exception as e:
            return f"## Error Retrieving Memories: {str(e)}"

    def get_token_usage(self) -> Dict[str, int]:
        """Get current token usage breakdown."""
        recent_tokens = sum(ctx.tokens for ctx in self.recent_context)
        return {
            "recent_context": recent_tokens,
            "available_for_memories": max(0, self.max_context_tokens - recent_tokens),
            "total_budget": self.max_context_tokens
        }