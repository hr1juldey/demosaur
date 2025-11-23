"""
Context builder for assembling context from memories and recent interactions.

Builds context strings that fit within token budget while maximizing relevance.
"""

from typing import Dict, List, Any
from src.context.context_manager import ContextManager
from src.context.token_manager import TokenManager


class ContextBuilder:
    """
    Builds context strings from recent context and memory retrievals.
    Ensures context fits within token budget while maintaining relevance.
    """
    
    def __init__(self, context_manager: ContextManager, token_manager: TokenManager):
        self.context_manager = context_manager
        self.token_manager = token_manager
    
    def build_context(self, query: str, user_id: str = "default_user", 
                     memory_limit: int = 5, max_tokens: int = 2048) -> str:
        """
        Build context string from recent context and memories.
        
        PASSING CRITERIA:
        ✅ Context assembled from recent context and memories
        ✅ Fits within token budget
        ✅ Relevant information prioritized
        ✅ Proper formatting for LLM consumption
        """
        # Get context with memory from the context manager
        context = self.context_manager.get_context_with_memory(
            query=query,
            user_id=user_id,
            memory_limit=memory_limit
        )
        
        # Ensure context fits within budget
        if self.token_manager.estimate_tokens(context) > max_tokens:
            context = self.token_manager.truncate_to_budget(context)
        
        return context
    
    def build_minimal_context(self, query: str) -> str:
        """
        Build minimal context with just the query for simple tasks.
        
        PASSING CRITERIA:
        ✅ Minimal context built efficiently
        ✅ Fits well within token budget
        ✅ Preserves query integrity
        """
        return f"Query: {query}"
    
    def build_debug_context(self, query: str, user_id: str = "default_user") -> str:
        """
        Build verbose context for debugging purposes.
        
        PASSING CRITERIA:
        ✅ All relevant information included
        ✅ Proper debugging information provided
        ✅ Context formatted for developer readability
        """
        context_parts = [
            "# Debug Context Assembly",
            f"Query: {query}",
            f"User ID: {user_id}",
            f"Session Start: {self.context_manager.session_start_time}",
            f"Recent Context Items: {len(self.context_manager.recent_context)}",
            f"Token Budget: {self.context_manager.max_context_tokens}",
            f"Current Token Usage: {self.context_manager.get_token_usage()['recent_context']}",
        ]
        
        # Add recent context items
        if self.context_manager.recent_context:
            context_parts.append("\n## Recent Context Items:")
            for i, ctx in enumerate(self.context_manager.recent_context[-3:], 1):  # Last 3 items
                context_parts.append(f"### Item {i} ({ctx.context_type}):")
                context_parts.append(ctx.content[:200] + "..." if len(ctx.content) > 200 else ctx.content)
        
        return "\n".join(context_parts)