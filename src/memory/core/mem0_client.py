"""
Mem0 client wrapper for local Ollama integration.

Implements core Mem0 functionality with local file-based storage configuration.
"""

from typing import Dict, Any, Optional
from mem0 import Memory
import os


class Mem0Client:
    """
    Mem0 client wrapper configured for local Ollama with file-based storage.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, storage_path: str = "./local_mem0_storage"):
        """
        Initialize Mem0 client with local configuration.

        Args:
            config: Optional custom configuration. If None, uses default local config.
            storage_path: Directory for local file-based storage.
        """
        # Create storage directory if it doesn't exist
        os.makedirs(storage_path, exist_ok=True)

        if config is None:
            self.config = self._get_default_local_config(storage_path)
        else:
            self.config = config

        self.storage_path = storage_path
        self.memory = Memory.from_config(self.config)

    def _get_default_local_config(self, storage_path: str) -> Dict[str, Any]:
        """
        Get default configuration for local file-based Mem0 deployment.
        """
        return {
            "llm": {
                "provider": "ollama",
                "config": {
                    "model": "mistral:7b",
                    "temperature": 0.1,
                    "max_tokens": 2000,
                    "ollama_base_url": "http://localhost:11434",
                }
            },
            "embedder": {
                "provider": "ollama",
                "config": {
                    "model": "mxbai-embed-large:latest",
                    "ollama_base_url": "http://localhost:11434",
                }
            },
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "path": storage_path,  # Local file-based storage
                    "collection_name": "mem0_default",
                },
            }
        }

    def store_memory(self, content: str, user_id: str = "default_user",
                     metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Store memory content for a user with proper isolation.
        """
        try:
            result = self.memory.add(
                content,
                user_id=user_id,
                metadata=metadata or {}
            )
            return {
                "success": True,
                "message": f"Stored memory for user {user_id}",
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error storing memory: {str(e)}",
                "error": str(e)
            }

