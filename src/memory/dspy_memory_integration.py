"""
DSPy memory integration module for Mem0 system.

Implements memory-enhanced DSPy modules for token limit constraints.
"""

import dspy
from typing import List, Dict, Any
from src.memory.mem0_client import Mem0Client
from src.memory.mem0_memory_retrieval import Mem0MemoryRetrieval
from src.context.token_manager import TokenManager


class MemoryEnhancedModule(dspy.Module):
    """
    DSPy module enhanced with Mem0 memory capabilities.
    Respects token limit through smart memory retrieval and context building.
    """

    def __init__(self, mem0_client: Mem0Client, max_context_tokens: int = 2048):
        super().__init__()
        self.mem0_client = mem0_client
        self.memory_retrieval = Mem0MemoryRetrieval(mem0_client.memory)
        self.token_manager = TokenManager()
        self.max_context_tokens = max_context_tokens

    def forward(self, query: str, user_id: str = "default_user",
                memory_limit: int = 5) -> dspy.Prediction:
        """
        Process query with memory enhancement within token limits.
        """
        # Retrieve relevant memories from Mem0
        memory_results = self.memory_retrieval.search_memories(
            query=query,
            user_id=user_id,
            limit=memory_limit
        )

        # Build context within token budget
        context = self.build_context_from_memories(
            memories=memory_results.get("results", []),
            query=query,
            user_id=user_id
        )

        # Create DSPy prediction with the context
        result = dspy.Prediction(
            context=context,
            query=query,
            user_id=user_id,
            memory_results=memory_results
        )

        return result

    def build_context_from_memories(self, memories: List[Dict[str, Any]],
                                   query: str, user_id: str) -> str:
        """
        Build context string from memories within token budget.
        """
        # Start with the original query
        context_parts = [f"Query: {query}", f"User: {user_id}", "Relevant Context:"]

        # Add memories in order of relevance (highest score first)
        sorted_memories = sorted(
            memories,
            key=lambda x: x.get("score", 0.0),
            reverse=True
        )

        # Add memories while staying within budget
        current_token_usage = self.token_manager.estimate_tokens("\n".join(context_parts))

        for memory in sorted_memories:
            memory_text = f"- {memory.get('memory', '')}"
            memory_tokens = self.token_manager.estimate_tokens(memory_text)

            # Check if adding this memory would exceed budget
            if current_token_usage + memory_tokens > self.max_context_tokens:
                # Try to add partial content if possible
                truncated_memory = self.token_manager.truncate_to_budget(
                    memory_text
                )
                truncated_tokens = self.token_manager.estimate_tokens(truncated_memory)

                if current_token_usage + truncated_tokens <= self.max_context_tokens:
                    context_parts.append(truncated_memory)
                    current_token_usage += truncated_tokens
                break  # Stop adding memories once budget is tight
            else:
                context_parts.append(memory_text)
                current_token_usage += memory_tokens

        # Join all context parts
        final_context = "\n".join(context_parts)

        # Verify final context is within token limits
        if self.token_manager.estimate_tokens(final_context) > self.max_context_tokens:
            final_context = self.token_manager.truncate_to_budget(final_context)

        return final_context