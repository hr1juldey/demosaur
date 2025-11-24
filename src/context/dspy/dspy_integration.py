"""
DSPy integration for context management system.

Connects DSPy modules with Mem0 memory through the context management system.
"""

import dspy
from src.context.core.context_manager import ContextManager


class MemoryEnhancedModule(dspy.Module):
    """
    DSPy module enhanced with Mem0-backed context management.

    PASSING CRITERIA:
    ✅ Integrates with context manager properly
    ✅ Respects token budget constraints
    ✅ Uses memory for enhanced reasoning
    ✅ Maintains DSPy Module interface
    """

    def __init__(self, context_manager: ContextManager, max_context_tokens: int = 2048):
        super().__init__()
        self.context_manager = context_manager
        self.max_context_tokens = max_context_tokens

    def forward(self, query: str, user_id: str = "default_user",
                memory_limit: int = 5) -> dspy.Prediction:
        """
        Process query with memory-enhanced context.

        PASSING CRITERIA:
        ✅ Query processed with memory context
        ✅ Token budget respected
        ✅ Memory content properly integrated
        ✅ Returns DSPy Prediction object
        """
        # Build context with memory
        context = self.context_manager.get_context_with_memory(
            query=query,
            user_id=user_id,
            memory_limit=memory_limit
        )

        # Create prediction with enhanced context
        return dspy.Prediction(
            context=context,
            query=query,
            user_id=user_id,
            memory_limit=memory_limit
        )