"""
DSPy memory tools for context management system.

Contains DSPy-compatible tools for memory operations.
"""

import dspy
from typing import Dict, Any, List
from src.context.context_manager import ContextManager


class ContextMemoryTools:
    """
    DSPy-compatible tools for memory operations.

    PASSING CRITERIA:
    ✅ Tools work with DSPy ReAct framework
    ✅ Memory operations properly encapsulated
    ✅ DSPy tool interface maintained
    ✅ Error handling implemented
    """

    def __init__(self, context_manager: ContextManager):
        self.context_manager = context_manager

    def search_memory(self, query: str, user_id: str = "default_user",
                     limit: int = 5) -> str:
        """
        Search for relevant memories (DSPy tool).

        PASSING CRITERIA:
        ✅ Searches memory effectively
        ✅ Returns properly formatted results
        ✅ Handles errors gracefully
        ✅ DSPy tool interface compliant
        """
        try:
            memory_results = self.context_manager.mem0_client.search_memories(
                query=query,
                user_id=user_id,
                limit=limit
            )

            if memory_results["success"] and memory_results["results"]:
                result_text = "Relevant memories found:\n"
                for i, result in enumerate(memory_results["results"]):
                    result_text += f"{i+1}. {result['memory']} (Score: {result['score']:.2f})\n"
                return result_text
            else:
                return "No relevant memories found."
        except Exception as e:
            return f"Error searching memories: {str(e)}"

    def store_memory(self, content: str, user_id: str = "default_user") -> str:
        """
        Store information in memory (DSPy tool).

        PASSING CRITERIA:
        ✅ Stores memory successfully
        ✅ Returns confirmation
        ✅ Handles errors gracefully
        ✅ DSPy tool interface compliant
        """
        try:
            result = self.context_manager.store_to_memory(
                content=content,
                user_id=user_id
            )
            return f"Memory stored successfully: {result['message']}"
        except Exception as e:
            return f"Error storing memory: {str(e)}"

    def add_recent_context(self, content: str, context_type: str = "information") -> str:
        """
        Add content to recent context (short-term memory).

        PASSING CRITERIA:
        ✅ Adds to recent context properly
        ✅ Returns confirmation
        ✅ Maintains context type
        ✅ DSPy tool interface compliant
        """
        try:
            context_id = self.context_manager.add_recent_context(
                content=content,
                context_type=context_type
            )
            return f"Added to recent context: {context_id}"
        except Exception as e:
            return f"Error adding to recent context: {str(e)}"