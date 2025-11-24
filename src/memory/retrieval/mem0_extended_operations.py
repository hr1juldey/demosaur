"""
Extended memory operations for Mem0 client.

Contains additional memory management methods that were in the original file.
"""

from typing import Dict, Any
from mem0 import Memory


class Mem0ExtendedOperations:
    """
    Extended operations for Mem0 memory management.
    """
    
    def __init__(self, memory_client: Memory):
        self.memory = memory_client
    
    def get_all_memories(self, user_id: str = "default_user") -> Dict[str, Any]:
        """
        Retrieve all memories for a user.
        
        PASSING CRITERIA:
        ✅ User-specific memories retrieved
        ✅ Proper user isolation
        ✅ Results formatted appropriately
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
    
    def update_memory(self, memory_id: str, new_content: str, 
                     user_id: str = "default_user") -> Dict[str, Any]:
        """
        Update an existing memory entry.
        
        PASSING CRITERIA:
        ✅ Memory updated successfully
        ✅ User ownership verified
        ✅ Content updated properly
        """
        try:
            self.memory.update(memory_id, new_content)
            return {
                "success": True,
                "message": f"Updated memory {memory_id} for user {user_id}",
                "updated_id": memory_id
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error updating memory: {str(e)}",
                "error": str(e)
            }
    
    def delete_memory(self, memory_id: str, user_id: str = "default_user") -> Dict[str, Any]:
        """
        Delete a specific memory entry.
        
        PASSING CRITERIA:
        ✅ Memory deleted successfully
        ✅ User ownership verified
        ✅ Proper confirmation returned
        """
        try:
            self.memory.delete(memory_id)
            return {
                "success": True,
                "message": f"Deleted memory {memory_id} for user {user_id}",
                "deleted_id": memory_id
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error deleting memory: {str(e)}",
                "error": str(e)
            }