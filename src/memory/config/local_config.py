"""
Local Mem0 Configuration for File-Based Storage

Sets up Mem0 to work locally without requiring separate database servers.
Uses Qdrant's local file-based storage for persistence.
"""

from typing import Dict, Any


class LocalMem0Config:
    """
    Configuration class for local Mem0 deployment with file-based storage.
    """

    @staticmethod
    def get_local_config() -> Dict[str, Any]:
        """
        Get configuration for local file-based Mem0 deployment.
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
                    "path": "./local_mem0_storage",  # Local file storage
                    "collection_name": "code_intern_memories",
                    "prefer_grpc": False,
                },
            }
        }

    @staticmethod
    def create_storage_directories():
        """
        Create necessary storage directories if they don't exist.
        """
        import os
        storage_path = "./local_mem0_storage"
        os.makedirs(storage_path, exist_ok=True)