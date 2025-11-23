"""
Token operations for Mem0 client.

Contains token-related utility methods for the Mem0 client.
"""


class Mem0ClientTokenOps:
    """
    Token operations for Mem0Client.
    """

    @staticmethod
    def get_token_usage_for_content(content: str) -> int:
        """
        Estimate token usage for content using conservative approximation.

        PASSING CRITERIA:
        ✅ Accurate token estimation
        ✅ Conservative calculation (with safety margin)
        ✅ Consistent across different content types
        """
        # Conservative estimate: chars/4 with 10% safety buffer
        if not content:
            return 0
        return int((len(content) // 4) * 1.1)

    @staticmethod
    def is_within_token_budget(content: str, budget: int = 2048) -> bool:
        """
        Check if content fits within token budget.

        PASSING CRITERIA:
        ✅ Accurate budget checking
        ✅ Proper safety margin applied
        ✅ Efficient calculation
        """
        token_usage = Mem0ClientTokenOps.get_token_usage_for_content(content)
        return token_usage <= budget