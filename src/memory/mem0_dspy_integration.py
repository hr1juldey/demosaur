"""
Main integration file for Mem0 + DSPy context management system.

Coordinates all components to work together within 4096 token limit.
"""

import dspy
from typing import Dict, Any
from src.memory.mem0_client import Mem0Client
from src.memory.dspy_memory_integration import MemoryEnhancedModule
from src.memory.dspy_memory_tools import MemoryTools


class Mem0DSPyIntegration:
    """
    Main integration class coordinating Mem0 and DSPy components.

    PASSING CRITERIA:
    ✅ All components properly coordinated
    ✅ 4096 token limit respected
    ✅ Memory and DSPy work together seamlessly
    ✅ Configuration handled properly
    """

    def __init__(self, config: Dict[str, Any] = None):
        # Initialize Mem0 client
        self.mem0_client = Mem0Client(config)

        # Initialize DSPy memory components
        self.memory_enhanced_module = MemoryEnhancedModule(self.mem0_client)
        self.memory_tools = MemoryTools(self.mem0_client)

    def process_with_memory(self, query: str, user_id: str = "default_user",
                           memory_limit: int = 5) -> dspy.Prediction:
        """
        Process query with memory enhancement.

        PASSING CRITERIA:
        ✅ Query processed with memory context
        ✅ Token budget respected
        ✅ User isolation maintained
        """
        return self.memory_enhanced_module(query, user_id, memory_limit)

    def get_memory_tools(self) -> MemoryTools:
        """
        Get access to memory tools for use with DSPy ReAct.

        PASSING CRITERIA:
        ✅ Tools returned properly
        ✅ Tools properly configured
        ✅ Ready for DSPy integration
        """
        return self.memory_tools


# Example usage pattern:
"""
# Initialize the integration
integration = Mem0DSPyIntegration()

# Create a ReAct agent with memory tools
react_with_memory = dspy.ReAct(
    signature=dspy.Signature("input -> output"),
    tools=[
        integration.get_memory_tools().search_memories,
        integration.get_memory_tools().store_memory,
        get_current_time,  # standard tool
    ],
    max_iters=6
)

# Process with memory enhancement
result = integration.process_with_memory("What do you know about me?", "user123")
"""