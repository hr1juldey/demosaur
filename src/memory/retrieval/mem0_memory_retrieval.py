"""
Mem0 memory retrieval component for Ollama integration.

Implements memory search and retrieval operations.
"""

from typing import Dict, Any
from mem0 import Memory


class Mem0MemoryRetrieval:
    """
    Memory retrieval component for searching and basic operations.
    """

    def __init__(self, memory_client: Memory):
        self.memory = memory_client

    def search_memories(self, query: str, user_id: str = "default_user",
                       limit: int = 5) -> Dict[str, Any]:
        """
        Search for relevant memories.
        """
        try:
            results = self.memory.search(
                query=query,
                user_id=user_id,
                limit=limit
            )

            # Filter and format results for DSPy compatibility
            formatted_results = []
            if "results" in results and results["results"]:
                for result in results["results"]:
                    formatted_results.append({
                        "id": result.get("id"),
                        "memory": result.get("memory", ""),
                        "score": result.get("score", 0.0),
                        "metadata": result.get("metadata", {}),
                        "timestamp": result.get("created_at")
                    })

            return {
                "success": True,
                "results": formatted_results,
                "query": query,
                "user_id": user_id
            }
        except Exception as e:
            return {
                "success": False,
                "results": [],
                "message": f"Error searching memories: {str(e)}",
                "error": str(e)
            }

    def get_all_memories(self, user_id: str = "default_user") -> Dict[str, Any]:
        """
        Retrieve all memories for a user.
        """
        try:
            results = self.memory.get_all(user_id=user_id)

            formatted_results = []
            if "results" in results and results["results"]:
                for result in results["results"]:
                    formatted_results.append({
                        "id": result.get("id"),
                        "memory": result.get("memory", ""),
                        "metadata": result.get("metadata", {}),
                        "timestamp": result.get("created_at")
                    })

            return {
                "success": True,
                "results": formatted_results,
                "user_id": user_id
            }
        except Exception as e:
            return {
                "success": False,
                "results": [],
                "message": f"Error retrieving all memories: {str(e)}",
                "error": str(e)
            }