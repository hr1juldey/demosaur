"""
Context manager for Mem0-based short-term and long-term memory system.

Coordinates between immediate context needs and persistent memory storage via Mem0.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
import uuid

from src.memory.mem0_client import Mem0Client
from src.context.token_manager import TokenManager
from src.context.context_retrieval_helpers import retrieve_relevant_memories, build_recent_context_from_snapshots


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
    Main context coordinator that manages the flow between:
    - Short-term context (recent interactions, current state)
    - Long-term memory (via Mem0 for persistent storage)
    - Token budget management (4096 token limit)
    """

    def __init__(self, mem0_client: Mem0Client, max_context_tokens: int = 2048):
        self.mem0_client = mem0_client
        self.token_manager = TokenManager()
        self.max_context_tokens = max_context_tokens

        # Short-term context - recent interactions that happened in this session
        self.recent_context: List[ContextSnapshot] = []
        self.session_start_time = datetime.now().isoformat()

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

        # Keep only most recent contexts within token budget
        self._trim_recent_context()

        return context_id

    def _trim_recent_context(self):
        """
        Trim recent context to stay within token budget.

        PASSING CRITERIA:
        ✅ Total tokens stay within recent context budget
        ✅ Most recent items preserved
        ✅ Oldest items removed first when over budget
        """
        current_tokens = sum(ctx.tokens for ctx in self.recent_context)

        # Reserve some tokens for memory retrieval (60% for recent, 40% for memories)
        recent_budget = int(self.max_context_tokens * 0.6)

        while current_tokens > recent_budget and len(self.recent_context) > 1:
            # Remove oldest item
            removed_item = self.recent_context.pop(0)
            current_tokens -= removed_item.tokens

    def get_context_with_memory(self, query: str, user_id: str = "default_user",
                              memory_limit: int = 5) -> str:
        """
        Build comprehensive context combining recent context and Mem0 memories.

        PASSING CRITERIA:
        ✅ Recent context included
        ✅ Relevant memories retrieved from Mem0
        ✅ Total context within token budget
        ✅ Context properly formatted for LLM
        """
        # Get recent context
        recent_part = build_recent_context_from_snapshots(self.recent_context)

        # Get relevant memories from Mem0
        memory_part = retrieve_relevant_memories(self, query, user_id, memory_limit)  # Pass self as context_manager to access mem0_client

        # Combine and ensure within budget
        combined_context = f"{recent_part}\n\n{memory_part}".strip()

        # Truncate if necessary
        if self.token_manager.estimate_tokens(combined_context) > self.max_context_tokens:
            combined_context = self.token_manager.truncate_to_budget(combined_context)

        return combined_context

