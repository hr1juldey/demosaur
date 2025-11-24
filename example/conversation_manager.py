"""
Conversation manager for handling chat history and state.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from config import config, ConversationState


@dataclass
class Message:
    """Represents a single message in conversation."""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ConversationContext:
    """Complete conversation context."""
    conversation_id: str
    state: ConversationState
    messages: List[Message] = field(default_factory=list)
    user_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to history."""
        self.messages.append(Message(role=role, content=content))
        
        # Keep only last N messages
        if len(self.messages) > config.MAX_CHAT_HISTORY:
            self.messages = self.messages[-config.MAX_CHAT_HISTORY:]
    
    def get_history_text(self, max_messages: Optional[int] = None) -> str:
        """Get conversation history as formatted text."""
        messages = self.messages
        if max_messages:
            messages = messages[-max_messages:]
        
        history_lines = []
        for msg in messages:
            prefix = "User" if msg.role == "user" else "Assistant"
            history_lines.append(f"{prefix}: {msg.content}")
        
        return "\n".join(history_lines)
    
    def get_recent_user_messages(self, count: int = 3) -> List[str]:
        """Get recent user messages."""
        user_messages = [m.content for m in self.messages if m.role == "user"]
        return user_messages[-count:] if user_messages else []


class ConversationManager:
    """Manages conversation contexts and history."""
    
    def __init__(self):
        self.conversations: Dict[str, ConversationContext] = {}
    
    def get_or_create(
        self,
        conversation_id: str,
        initial_state: ConversationState = ConversationState.GREETING
    ) -> ConversationContext:
        """Get existing or create new conversation context."""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = ConversationContext(
                conversation_id=conversation_id,
                state=initial_state
            )
        return self.conversations[conversation_id]
    
    def add_user_message(self, conversation_id: str, content: str) -> ConversationContext:
        """Add user message to conversation."""
        context = self.get_or_create(conversation_id)
        context.add_message("user", content)
        return context
    
    def add_assistant_message(self, conversation_id: str, content: str) -> ConversationContext:
        """Add assistant message to conversation."""
        context = self.get_or_create(conversation_id)
        context.add_message("assistant", content)
        return context
    
    def update_state(self, conversation_id: str, new_state: ConversationState) -> None:
        """Update conversation state."""
        context = self.get_or_create(conversation_id)
        context.state = new_state
    
    def store_user_data(self, conversation_id: str, key: str, value: Any) -> None:
        """Store extracted user data."""
        context = self.get_or_create(conversation_id)
        context.user_data[key] = value
    
    def get_user_data(self, conversation_id: str, key: str, default: Any = None) -> Any:
        """Get stored user data."""
        context = self.get_or_create(conversation_id)
        return context.user_data.get(key, default)
    
    def clear_conversation(self, conversation_id: str) -> None:
        """Clear conversation history."""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
