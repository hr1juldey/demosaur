"""
Extended context manager methods for Mem0 integration.

Contains additional methods for ContextManager that were in the original file.
"""

from typing import Dict, Any, Optional
from src.context.core.context_manager import ContextManager


class ContextManagerExtensions:
    """
    Extended methods for ContextManager class.
    """
    
    def __init__(self, context_manager: ContextManager):
        self.ctx_manager = context_manager
    
    def store_to_memory(self, content: str, user_id: str = "default_user",
                       metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Store content to persistent memory via Mem0.

        PASSING CRITERIA:
        ✅ Content stored in Mem0
        ✅ User isolation maintained
        ✅ Proper storage confirmation returned
        """
        return self.ctx_manager.mem0_client.store_memory(content, user_id, metadata)

    def get_token_usage(self) -> Dict[str, int]:
        """Get current token usage breakdown."""
        recent_tokens = sum(ctx.tokens for ctx in self.ctx_manager.recent_context)
        return {
            "recent_context": recent_tokens,
            "available_for_memories": max(0, self.ctx_manager.max_context_tokens - recent_tokens),
            "total_budget": self.ctx_manager.max_context_tokens
        }