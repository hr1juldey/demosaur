"""
Template Manager - Decides when to push templates vs. use LLM chatbot.

Strategy:
- Use templates when user explicitly asks for catalog/pricing/booking
- Use LLM when user asks questions, needs clarification, or shows sentiment
- Balance is key: Don't be silent dumper OR cheeky sales girl
"""

from enum import Enum
from typing import Tuple


class ResponseMode(Enum):
    """Response strategy decision."""
    TEMPLATE_ONLY = "template"      # Just push template, minimal LLM
    LLM_THEN_TEMPLATE = "llm_then"  # Chat first, then template
    TEMPLATE_THEN_LLM = "template_then_llm"  # Template first, offer to chat
    LLM_ONLY = "llm_only"           # Just chat, no template


class TemplateManager:
    """Decide when to use templates vs. LLM responses."""

    # Keywords that trigger TEMPLATE mode
    TEMPLATE_TRIGGERS = {
        "catalog": ["catalog", "services", "menu", "what do you offer"],
        "plans": ["plans", "pricing", "prices", "cost", "how much", "tiers"],
        "booking": ["book", "schedule", "appointment", "reserve"],
        "pricing": ["price", "cost", "rates", "charges"],
    }

    # Keywords that trigger LLM mode (questions, clarifications)
    LLM_TRIGGERS = {
        "question": ["?", "how", "why", "what is", "explain", "tell me"],
        "confusion": ["understand", "confused", "don't know", "help", "guide"],
        "complaint": ["problem", "issue", "complaint", "bad", "poor"],
    }

    def __init__(self):
        self.sentiment_threshold_interested = 7.0
        self.sentiment_threshold_disinterested = 3.0

    def decide_response_mode(
        self,
        user_message: str,
        sentiment_interest: float = 5.0,
        sentiment_anger: float = 1.0,
        current_state: str = "greeting"
    ) -> Tuple[ResponseMode, str]:
        """
        Decide whether to use template or LLM response.

        Args:
            user_message: User's input
            sentiment_interest: Interest score (1-10)
            sentiment_anger: Anger score (1-10)
            current_state: Current conversation state

        Returns:
            (ResponseMode, template_key_if_applicable)
        """
        message_lower = user_message.lower().strip()

        # Rule 1: Check for explicit template triggers
        template_trigger = self._check_template_trigger(message_lower)
        if template_trigger:
            return (ResponseMode.TEMPLATE_ONLY, template_trigger)

        # Rule 2: Check for anger or disgust - Don't push templates to angry customer
        if sentiment_anger > 6.0:
            return (ResponseMode.LLM_ONLY, "")

        # Rule 3: Check for questions or confusion - Use LLM first
        if self._is_question(message_lower):
            return (ResponseMode.LLM_THEN_TEMPLATE, "")

        # Rule 4: High interest - Be friendly but still deliver CTAs
        if sentiment_interest > self.sentiment_threshold_interested:
            return (ResponseMode.TEMPLATE_THEN_LLM, "catalog")

        # Rule 5: Low interest - Don't push, chat to engage
        if sentiment_interest < self.sentiment_threshold_disinterested:
            return (ResponseMode.LLM_ONLY, "")

        # Default: Mixed approach
        return (ResponseMode.TEMPLATE_THEN_LLM, "catalog")

    def _check_template_trigger(self, message: str) -> str:
        """Check if message matches template trigger keywords."""
        for template_type, keywords in self.TEMPLATE_TRIGGERS.items():
            if any(keyword in message for keyword in keywords):
                return template_type
        return ""

    def _is_question(self, message: str) -> bool:
        """Check if message is a question."""
        for keywords in self.LLM_TRIGGERS.values():
            if any(keyword in message for keyword in keywords):
                return True
        return False

    def should_send_template(self, mode: ResponseMode) -> bool:
        """Check if template should be sent in this mode."""
        return mode in [
            ResponseMode.TEMPLATE_ONLY,
            ResponseMode.TEMPLATE_THEN_LLM,
            ResponseMode.LLM_THEN_TEMPLATE,
        ]

    def should_send_llm_response(self, mode: ResponseMode) -> bool:
        """Check if LLM response should be sent in this mode."""
        return mode in [
            ResponseMode.LLM_ONLY,
            ResponseMode.LLM_THEN_TEMPLATE,
            ResponseMode.TEMPLATE_THEN_LLM,
        ]