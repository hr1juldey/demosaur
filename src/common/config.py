"""
Configuration management for Code Intern MCP Server.

Centralizes all configuration using Pydantic settings.
Follows SRP: Single source for configuration values.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings with sensible defaults"""

    # DSPy / LLM Configuration
    ollama_base_url: str = "http://localhost:11434"
    model_name: str = "mistral:7b"
    temperature: float = 0.7
    max_tokens: int = 4096

    # Execution Configuration
    max_iterations_per_module: int = 10
    test_timeout_seconds: int = 30
    sandbox_memory_limit_mb: int = 1024
    sandbox_timeout_seconds: int = 60

    # MCP Server Configuration
    max_concurrent_tasks: int = 3
    task_timeout_minutes: int = 30
    log_level: str = "INFO"

    # Quality Thresholds
    min_score_threshold: float = 0.8
    min_test_pass_rate: float = 0.9
    max_acceptable_failures: int = 3

    # Performance Targets
    default_time_complexity: str = "O(n)"
    default_space_complexity: str = "O(1)"

    # Code Generation
    max_lines_per_file: int = 100
    enable_type_hints: bool = True
    enable_docstrings: bool = True

    # Sandbox Permissions
    sandbox_enable_network: bool = False
    sandbox_allowed_imports: List[str] = [
        "typing", "dataclasses", "enum", "collections",
        "itertools", "functools", "math", "json", "re"
    ]

    # Logging
    log_to_file: bool = True
    log_directory: str = "./logs"
    log_rotation_mb: int = 10

    class Config:
        env_prefix = "CODE_INTERN_"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get global settings instance"""
    return settings


def update_settings(**kwargs) -> None:
    """Update settings programmatically"""
    global settings
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
