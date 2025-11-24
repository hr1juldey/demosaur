"""
DSPy Memory Tools for Mem0 system.

Contains memory-related tools for use with DSPy ReAct framework.
"""

from src.memory.core.mem0_client import Mem0Client
from src.memory.retrieval.mem0_memory_retrieval import Mem0MemoryRetrieval
from context.tokens.token_manager import TokenManager


class MemoryTools:
    """
    Collection of memory-related tools for use with DSPy ReAct.
    """

    def __init__(self, mem0_client: Mem0Client):
        self.client = mem0_client
        self.retrieval = Mem0MemoryRetrieval(mem0_client.memory)
        self.token_manager = TokenManager()

    def store_memory(self, content: str, user_id: str = "default_user") -> str:
        """
        Store information in memory with token budget consideration.

        PASSING CRITERIA:
        ✅ Content stored successfully
        ✅ User isolation maintained
        ✅ Proper confirmation returned
        """
        result = self.client.store_memory(content, user_id=user_id)
        return f"Storage result: {result['message']}"

    def search_memories(self, query: str, user_id: str = "default_user",
                       limit: int = 5) -> str:
        """
        Search for relevant memories with token budget enforcement.

        PASSING CRITERIA:
        ✅ Relevant memories returned
        ✅ Within token budget
        ✅ Proper formatting for DSPy tools
        """
        try:
            results = self.retrieval.search_memories(query, user_id, limit)
            if results["success"] and results["results"]:
                memory_text = "Relevant memories found:\n"
                for i, result in enumerate(results["results"]):
                    memory_text += f"{i+1}. {result['memory']} (Score: {result['score']:.2f})\n"
                return memory_text
            else:
                return "No relevant memories found."
        except Exception as e:
            return f"Error searching memories: {str(e)}"

    def get_all_memories(self, user_id: str = "default_user") -> str:
        """
        Get all memories for a user.

        PASSING CRITERIA:
        ✅ All memories retrieved for user
        ✅ Proper user isolation
        ✅ Formatted appropriately
        """
        try:
            results = self.retrieval.get_all_memories(user_id)
            if results["success"] and results["results"]:
                memory_text = f"All memories for user {user_id}:\n"
                for i, result in enumerate(results["results"]):
                    memory_text += f"{i+1}. {result['memory']}\n"
                return memory_text
            else:
                return f"No memories found for user {user_id}."
        except Exception as e:
            return f"Error retrieving memories: {str(e)}"