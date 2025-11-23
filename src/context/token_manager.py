"""
Token manager for enforcing 4096 token budget with Ollama.

Manages token counting, budget enforcement, and fallback strategies
for the 4096 token limit imposed by Ollama system.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class TokenBudget:
    """Token budget allocation for 4096 token limit"""
    total_tokens: int = 4096
    system_reserve: int = 820      # 20% for system prompts
    generation_reserve: int = 1230  # 30% for generation
    context_budget: int = 2048      # 50% for active context
    reserved_buffer: int = 0        # Additional reserved tokens

    @property
    def available_for_context(self) -> int:
        """Calculate available tokens for context after reserves"""
        used = self.system_reserve + self.generation_reserve + self.reserved_buffer
        return max(0, self.total_tokens - used)

    def get_context_limit(self) -> int:
        """Get the context token limit respecting all reserves"""
        return min(self.context_budget, self.available_for_context)


class TokenManager:
    """Manages token counting and budget enforcement for 4096 limit"""

    def __init__(self, budget_config: Optional[TokenBudget] = None):
        self.budget = budget_config or TokenBudget()
        self.current_usage = 0

    def estimate_tokens(self, text: str) -> int:
        """Estimate tokens using chars/4 with reasonable overhead"""
        if not text:
            return 0
        # Rough estimate: 1 token ≈ 4 characters for English text
        base_estimate = max(1, len(text) // 4)
        # Add small overhead for tokenization patterns
        return int(base_estimate * 1.1)

    def estimate_tokens_in_dict(self, data: Dict[str, Any]) -> int:
        """Estimate tokens in a dictionary structure"""
        text = str(data)
        return self.estimate_tokens(text)

    def estimate_tokens_in_list(self, items: List[Any]) -> int:
        """Estimate tokens in a list"""
        total = 0
        for item in items:
            if isinstance(item, str):
                total += self.estimate_tokens(item)
            elif isinstance(item, dict):
                total += self.estimate_tokens_in_dict(item)
            elif isinstance(item, list):
                total += self.estimate_tokens_in_list(item)
            else:
                total += self.estimate_tokens(str(item))
        return total

    def would_exceed_budget(self, additional_tokens: int) -> bool:
        """Check if adding tokens would exceed budget"""
        return (self.current_usage + additional_tokens) > self.budget.get_context_limit()

    def can_fit_in_budget(self, text: str) -> bool:
        """Check if text can fit in remaining budget"""
        tokens = self.estimate_tokens(text)
        return not self.would_exceed_budget(tokens)

    def truncate_to_budget(self, text: str) -> str:
        """Truncate text to fit within token budget"""
        tokens_needed = self.estimate_tokens(text)
        if tokens_needed <= self.budget.get_context_limit():
            return text

        # Calculate target length to fit within budget (with safety margin)
        target_chars = int((self.budget.get_context_limit() * 4) * 0.9)  # 10% safety margin
        if len(text) <= target_chars:
            return text

        # Truncate with ellipsis
        truncated = text[:target_chars - 3] + "..."
        return truncated

    def add_tokens(self, tokens: int) -> bool:
        """Add tokens to current usage, return True if within budget"""
        if self.would_exceed_budget(tokens):
            return False
        self.current_usage += tokens
        return True

    def reset_usage(self):
        """Reset current token usage"""
        self.current_usage = 0

    def get_remaining_tokens(self) -> int:
        """Get remaining tokens in budget"""
        return max(0, self.budget.get_context_limit() - self.current_usage)

    def get_usage_percentage(self) -> float:
        """Get current usage as percentage of budget"""
        budget = self.budget.get_context_limit()
        if budget == 0:
            return 100.0 if self.current_usage > 0 else 0.0
        return (self.current_usage / budget) * 100.0