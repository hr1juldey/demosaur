"""
Helper methods for hierarchical context building.

Contains additional methods for hierarchical context management that were in the main file.
"""

from src.context.core.manager import ContextManager


class HierarchicalContextHelpers:
    """
    Helper methods for hierarchical context building operations.
    """
    
    @staticmethod
    def build_high_context(context_manager: ContextManager,
                          user_id: str, 
                          recent_limit: int, 
                          memory_limit: int) -> str:
        """
        Build high priority context (recent interactions, key decisions).
        """
        high_parts = ["# HIGH PRIORITY CONTEXT"]
        
        # Add recent context
        recent_context = context_manager._build_recent_context(recent_limit)
        if recent_context.strip():
            high_parts.append("## Recent Interactions:")
            high_parts.append(recent_context)
        
        # Add relevant memories
        memory_context = context_manager._get_relevant_memories(
            "key decisions and important information", 
            user_id, 
            memory_limit
        )
        if memory_context.strip():
            high_parts.append("## Important Memories:")
            high_parts.append(memory_context)
        
        return "\n".join(high_parts)
    
    @staticmethod
    def build_medium_context(context_manager: ContextManager, user_id: str) -> str:
        """
        Build medium priority context (module details, dependencies, test results).
        """
        medium_parts = ["# MEDIUM PRIORITY CONTEXT"]
        
        # Add module and dependency context if available
        try:
            module_context = context_manager._get_relevant_memories(
                "module structure and dependencies", 
                user_id, 
                limit=3
            )
            if module_context.strip():
                medium_parts.append("## Module Context:")
                medium_parts.append(module_context)
        except Exception:
            medium_parts.append("## Module Context: Not available")
        
        return "\n".join(medium_parts)