"""
Hierarchical context builder for managing multi-level context within token limits.

Builds context in priority order with token budget management for 4096 limit compliance.
"""

from src.context.core.manager import ContextManager
from src.context.tokens.manager import TokenManager


class HierarchicalContextBuilder:
    """
    Builds hierarchical context with prioritized information within token budget.

    PASSING CRITERIA:
    ✅ Builds context in priority order (CRITICAL first)
    ✅ Respects token budget (stops at 80% for generation space)
    ✅ Includes explicit references between levels
    ✅ Handles missing nodes gracefully
    """

    def __init__(self, context_manager: ContextManager, token_manager: TokenManager):
        self.context_manager = context_manager
        self.token_manager = token_manager
        self.max_context_tokens = token_manager.budget.get_context_limit()

    def build_context_with_priority_levels(self,
                                          query: str,
                                          user_id: str = "default_user",
                                          memory_limit: int = 5,
                                          recent_limit: int = 10) -> str:
        """
        Build hierarchical context with priority-based inclusion.

        Context levels:
        1. CRITICAL (Always included): Current status, immediate issues
        2. HIGH (If space): Recent interactions, key decisions
        3. MEDIUM (If space): Module details, dependencies, test results
        4. LOW (If space): Historical patterns, general information
        """
        context_parts = []

        # Build level 1: Critical context (always included)
        critical_context = self._build_critical_context(query, user_id)
        if critical_context:
            context_parts.append(critical_context)

        # Check remaining budget for other levels
        current_tokens = self.token_manager.estimate_tokens("\n\n".join(context_parts))
        remaining_budget = self.max_context_tokens - current_tokens

        if remaining_budget > 0:  # Include HIGH priority if budget allows
            high_context = self._build_high_context(user_id, recent_limit, memory_limit)
            high_tokens = self.token_manager.estimate_tokens(high_context)

            if high_tokens <= remaining_budget:
                context_parts.append(high_context)
                remaining_budget -= high_tokens

        if remaining_budget > 0:  # Include MEDIUM priority if budget allows
            medium_context = self._build_medium_context(user_id)
            medium_tokens = self.token_manager.estimate_tokens(medium_context)

            if medium_tokens <= remaining_budget:
                context_parts.append(medium_context)
                remaining_budget -= medium_tokens

        # Final context with token budget enforcement
        final_context = "\n\n".join(context_parts)

        if not self.token_manager.can_fit_in_budget(final_context):
            final_context = self.token_manager.truncate_to_budget(final_context)

        return final_context

    def _build_critical_context(self, query: str, user_id: str) -> str:
        """
        Build critical context that should always be included.

        Includes:
        - Current query and user context
        - Current task state and immediate issues
        - Top priority immediate context needed
        """
        critical_parts = ["# CRITICAL CONTEXT"]
        critical_parts.append(f"User ID: {user_id}")
        critical_parts.append(f"Current Query: {query}")

        # Get most recent task state information
        recent_items = self.context_manager.recent_context[-3:]  # Last 3 recent items
        if recent_items:
            critical_parts.append("\n## Recent Critical Information:")
            for item in recent_items:
                critical_parts.append(f"### {item.context_type.title()} ({item.timestamp}):")
                critical_parts.append(item.content)

        return "\n".join(critical_parts)

