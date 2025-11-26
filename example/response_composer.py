"""
Response Composer - Combines LLM responses with template strings.

This is where the "balance" happens:
- Not a silent dumper (templates only)
- Not a cheeky sales girl (chat only, no CTA)
"""

from template_manager import TemplateManager, ResponseMode
from template_strings import get_template, render_template
from typing import Dict, Any


class ResponseComposer:
    """Compose responses mixing LLM intelligence with template CTAs."""

    def __init__(self):
        self.template_manager = TemplateManager()

    def compose_response(
        self,
        user_message: str,
        llm_response: str = "",
        sentiment_interest: float = 5.0,
        sentiment_anger: float = 1.0,
        current_state: str = "greeting",
        template_variables: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Compose final response combining LLM + Templates.

        Args:
            user_message: User's input
            llm_response: Response from LLM chatbot
            sentiment_interest: Interest level (1-10)
            sentiment_anger: Anger level (1-10)
            current_state: Conversation state
            template_variables: Variables to render templates

        Returns:
            Dict with final response and metadata
        """
        template_variables = template_variables or {}

        # Decide response mode
        mode, template_key = self.template_manager.decide_response_mode(
            user_message, sentiment_interest, sentiment_anger, current_state
        )

        # Build response
        response_parts = []

        # Part 1: Send LLM response if needed
        if self.template_manager.should_send_llm_response(mode) and llm_response:
            response_parts.append(llm_response)

        # Part 2: Send template if needed
        if self.template_manager.should_send_template(mode) and template_key:
            template = get_template(template_key)
            if template:
                template_content = render_template(template_key, **template_variables)
                if template_content:
                    # Add separator if both LLM and template
                    if llm_response:
                        response_parts.append("\n" + "—" * 40)
                    response_parts.append(template_content)

        # Combine all parts
        final_response = "\n".join(response_parts)

        # Ensure we never return empty response
        if not final_response or not final_response.strip():
            final_response = "I understand. How can I help you further?"

        return {
            "response": final_response,
            "mode": mode.value,
            "has_llm_response": self.template_manager.should_send_llm_response(mode),
            "has_template": self.template_manager.should_send_template(mode),
            "template_type": template_key,
            "requires_cta": self.template_manager.should_send_template(mode),
        }


# Example usage patterns
EXAMPLE_SCENARIOS = {
    "customer_asks_catalog": {
        "user_message": "What services do you offer?",
        "llm_response": "",  # Template mode: no LLM needed
        "expected_mode": ResponseMode.TEMPLATE_ONLY,
        "expected_template": "catalog",
    },

    "customer_confused": {
        "user_message": "How do I book a service? I'm confused about the process",
        "llm_response": "You can book in 3 easy steps...",  # LLM first
        "expected_mode": ResponseMode.LLM_THEN_TEMPLATE,
        "expected_template": "catalog",
    },

    "customer_interested": {
        "user_message": "Tell me more about your premium detailing service",
        "llm_response": "Our premium detailing includes...",  # Chat + template
        "expected_mode": ResponseMode.TEMPLATE_THEN_LLM,
        "expected_template": "plans",
    },

    "customer_angry": {
        "user_message": "This is terrible service! Why are you wasting my time?",
        "llm_response": "I understand you're frustrated. Let me help...",
        "expected_mode": ResponseMode.LLM_ONLY,  # NO templates to angry customer
        "expected_template": None,
    },

    "customer_disinterested": {
        "user_message": "meh",
        "llm_response": "I'd love to help! What can I tell you about our services?",
        "expected_mode": ResponseMode.LLM_ONLY,  # Engage, don't push
        "expected_template": None,
    },
}