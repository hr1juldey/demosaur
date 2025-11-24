"""
Extended operations for Mem0 client.

Contains search and token management methods separate from the base client.
"""

from typing import Dict, Any
from src.memory.core.mem0_client import Mem0Client


class Mem0ClientExtended:
    """
    Extended Mem0 client with additional search and token management methods.
    """

    def __init__(self, mem0_client: Mem0Client):
        self.client = mem0_client

    def search_memories(self, query: str, user_id: str = "default_user",
                       limit: int = 5) -> Dict[str, Any]:
        """
        Search for relevant memories within token budget constraints.

        PASSING CRITERIA:
        ✅ Relevant memories returned
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

    def get_token_usage_for_content(self, content: str) -> int:
        """
        Estimate token usage for content using conservative approximation.

        PASSING CRITERIA:
        ✅ Accurate token estimation
        ✅ Conservative calculation (with safety margin)
        ✅ Consistent across different content types
        """
        # Use the client's method
        return self.client.get_token_usage_for_content(content)

    def is_within_token_budget(self, content: str, budget: int = 2048) -> bool:
        """
        Check if content fits within token budget.

        PASSING CRITERIA:
        ✅ Accurate budget checking
        ✅ Proper safety margin applied
        ✅ Efficient calculation
        """
        return self.client.is_within_token_budget(content, budget)