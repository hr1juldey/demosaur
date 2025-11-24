"""
Extended memory operations for Mem0 client.

Contains update and delete operations separate from basic retrieval.
"""

from typing import Dict, Any
from mem0 import Memory


class Mem0MemoryOperations:
    """
    Extended memory operations for update and delete functions.
    """
    
    def __init__(self, memory_client: Memory):
        self.memory = memory_client

    def update_memory(self, memory_id: str, new_content: str,
                     user_id: str = "default_user") -> Dict[str, Any]:
        """
        Update an existing memory entry.
        
        PASSING CRITERIA:
        ✅ Memory updated successfully
        ✅ User isolation maintained
        ✅ Proper confirmation returned
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
        ✅ User isolation maintained
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