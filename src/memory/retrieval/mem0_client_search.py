"""
Extended memory operations for Mem0 client.

Contains additional methods like search and retrieval functions.
"""

from typing import Dict, Any
from src.memory.core.mem0_client import Mem0Client


class Mem0ClientExtended:
    """
    Extended Mem0 client methods for search and retrieval operations.
    """
    
    def __init__(self, mem0_client: Mem0Client):
        self.client = mem0_client

    def search_memories(self, query: str, user_id: str = "default_user",
                       limit: int = 5) -> Dict[str, Any]:
        """
        Search for relevant memories in the local storage.

        PASSING CRITERIA:
        ✅ Relevant memories returned from local storage
        ✅ User isolation maintained
        ✅ Results limited appropriately
        ✅ Semantic search used effectively
        """
        try:
            results = self.client.memory.search(
                query=query,
                user_id=user_id,
                limit=limit
            )

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