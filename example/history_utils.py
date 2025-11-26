"""
Lean utilities for DSPy conversation history management.
Follows https://dspy.ai/tutorials/conversation_history/
"""

import dspy
from typing import List, Dict, Any


def empty_dspy_history() -> dspy.History:
    """Return empty dspy.History for modules that need default history."""
    return dspy.History(messages=[])


def get_default_history(history: dspy.History = None) -> dspy.History:
    """
    Factory function to ensure conversation_history is always dspy.History.

    Args:
        history: dspy.History object or None

    Returns:
        Provided history or empty history if None

    Usage in modules:
        conversation_history = get_default_history(conversation_history)
    """
    return history if history is not None else empty_dspy_history()


def create_dspy_history(messages: List[Dict[str, str]], max_messages: int = 25) -> dspy.History:
    """
    Convert message list to dspy.History object.

    Args:
        messages: List of dicts with 'role' and 'content' keys
        max_messages: Keep only recent N messages for context window (default 25)

    Returns:
        dspy.History object formatted for DSPy modules
    """
    recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages

    formatted_messages = []
    for msg in recent_messages:
        if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
            formatted_messages.append({
                "role": msg['role'],
                "content": str(msg['content']).strip()
            })
        elif hasattr(msg, 'role') and hasattr(msg, 'content'):
            formatted_messages.append({
                "role": msg.role,
                "content": str(msg.content).strip()
            })

    return dspy.History(messages=formatted_messages)


def messages_to_dspy_history(conversation_context: Any, max_messages: int = 25) -> dspy.History:
    """
    Convert ValidatedConversationContext to dspy.History.

    Args:
        conversation_context: Object with .messages attribute from conversation_manager
        max_messages: Keep only recent N messages

    Returns:
        dspy.History ready for DSPy modules
    """
    if not hasattr(conversation_context, 'messages') or not conversation_context.messages:
        return empty_dspy_history()

    return create_dspy_history(
        [{"role": msg.role, "content": msg.content} for msg in conversation_context.messages],
        max_messages=max_messages
    )