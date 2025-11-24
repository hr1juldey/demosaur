"""
Token manager priority enforcement methods.

Contains the priority enforcement method that was in the original token_manager.py file.
"""

from typing import List
from src.context.tokens.manager import TokenManager


class TokenManagerPriority:
    """
    Priority-based token enforcement methods for TokenManager.
    """

    def __init__(self, token_manager: TokenManager):
        self.token_manager = token_manager

    def enforce_budget_with_priority(self,
                                   items: List[str],
                                   priorities: List[int]) -> List[str]:
        """
        Select items based on priority to fit within budget.
        Lower priority number = higher priority.
        """
        # Pair items with priorities and sort by priority
        item_priority_pairs = list(zip(items, priorities))
        item_priority_pairs.sort(key=lambda x: x[1])  # Sort by priority (ascending)

        selected_items = []
        current_tokens = 0

        for item, priority in item_priority_pairs:
            item_tokens = self.token_manager.estimate_tokens(item)

            if current_tokens + item_tokens <= self.token_manager.budget.get_context_limit():
                selected_items.append(item)
                current_tokens += item_tokens
            else:
                # Budget exceeded, stop adding lower priority items
                break

        return selected_items


# Example usage:
"""
token_manager = TokenManager()
priority_handler = TokenManagerPriority(token_manager)

items = ["high priority content", "medium priority content", "low priority content"]
priorities = [1, 2, 3]  # Lower number = higher priority
selected = priority_handler.enforce_budget_with_priority(items, priorities)
"""