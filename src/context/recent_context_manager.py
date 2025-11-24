"""
Recent context manager for handling immediate context needs.

Manages short-term context within 4096 token limit - for instant/recent context that happened recently.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
import uuid

from src.memory.core.mem0_client import Mem0Client
from src.context.tokens.manager import TokenManager


@dataclass
class RecentContextSnapshot:
    """Represents a snapshot of recent context at a point in time"""
    id: str
    timestamp: str
    content: str
    tokens: int
    context_type: str  # "recent", "instant", "session", "interaction"
    metadata: Dict[str, Any] = field(default_factory=dict)


class RecentContextManager:
    """
    Manages recent and instant context within token budget.
    
    Handles immediate context needs (what happened recently/instantly) 
    and coordination with long-term memory system.
    """

    def __init__(self, mem0_client: Mem0Client, max_context_tokens: int = 2048):
        self.mem0_client = mem0_client
        self.token_manager = TokenManager()
        self.max_context_tokens = max_context_tokens

        # Recent context - what happened in current session
        self.recent_context: List[RecentContextSnapshot] = []
        self.session_start_time = datetime.now().isoformat()
        self.max_recent_items = 30  # Maximum recent context items

    def add_instant_context(self, content: str, context_type: str = "instant",
                           metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add instant context to short-term storage.
        
        PASSING CRITERIA:
        ✅ Content added to instant context
        ✅ Token count calculated correctly
        ✅ Context type tracked properly
        ✅ Returns context ID for reference
        """
        context_id = f"instant:{uuid.uuid4()}"

        tokens = self.token_manager.estimate_tokens(content)

        snapshot = RecentContextSnapshot(
            id=context_id,
            timestamp=datetime.now().isoformat(),
            content=content,
            tokens=tokens,
            context_type=context_type,
            metadata=metadata or {}
        )

        self.recent_context.append(snapshot)
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
        context_budget = int(self.max_context_tokens * 0.8)  # Use 80% for recent context

        while current_tokens > context_budget and len(self.recent_context) > 1:
            removed_item = self.recent_context.pop(0)  # Remove oldest first
            current_tokens -= removed_item.tokens

        # Then trim by maximum item count
        if len(self.recent_context) > self.max_recent_items:
            excess_count = len(self.recent_context) - self.max_recent_items
            self.recent_context = self.recent_context[excess_count:]  # Keep newest only

    def get_instant_context(self, limit: int = 10) -> str:
        """
        Get instant/recent context for immediate use.
        
        PASSING CRITERIA:
        ✅ Returns recent context properly formatted
        ✅ Within token budget
        ✅ Most recent items included
        ✅ Proper chronological order
        """
        if not self.recent_context:
            return ""

        # Take most recent items up to limit
        recent_items = self.recent_context[-min(limit, len(self.recent_context)):]

        context_parts = ["## Instant Context:"]
        for snapshot in recent_items:
            context_parts.append(f"### {snapshot.context_type.title()} ({snapshot.timestamp}):")
            context_parts.append(snapshot.content)
            context_parts.append("")  # Blank line between entries

        return "\n".join(context_parts)