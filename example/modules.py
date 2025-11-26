"""
DSPy modules (predictors) for different tasks.
Uses history_utils for clean conversation history handling.
"""
import dspy
from history_utils import get_default_history
from signatures import (
    SentimentAnalysisSignature,
    NameExtractionSignature,
    VehicleDetailsExtractionSignature,
    DateParsingSignature,
    ResponseGenerationSignature,
    IntentClassificationSignature,
)


class SentimentAnalyzer(dspy.Module):
    """Analyze customer sentiment across multiple dimensions."""

    def __init__(self):
        super().__init__()
        self.predictor = dspy.ChainOfThought(SentimentAnalysisSignature)

    def forward(self, conversation_history=None, current_message: str = ""):
        """Analyze sentiment with proper conversation context."""
        conversation_history = get_default_history(conversation_history)
        return self.predictor(
            conversation_history=conversation_history,
            current_message=current_message
        )


class IntentClassifier(dspy.Module):
    """Classify user intent using DSPy Chain of Thought."""

    def __init__(self):
        super().__init__()
        self.predictor = dspy.ChainOfThought(IntentClassificationSignature)

    def forward(self, conversation_history=None, current_message: str = ""):
        """Classify user intent with conversation context."""
        conversation_history = get_default_history(conversation_history)
        return self.predictor(
            conversation_history=conversation_history,
            current_message=current_message
        )


class NameExtractor(dspy.Module):
    """Extract customer name from unstructured text."""

    def __init__(self):
        super().__init__()
        self.predictor = dspy.ChainOfThought(NameExtractionSignature)

    def forward(self, conversation_history=None, user_message: str = "", context: str = ""):
        """Extract name with conversation context."""
        conversation_history = get_default_history(conversation_history)
        return self.predictor(
            conversation_history=conversation_history,
            user_message=user_message,
            context=context or "collecting customer name"
        )


class VehicleDetailsExtractor(dspy.Module):
    """Extract vehicle details from unstructured text."""

    def __init__(self):
        super().__init__()
        self.predictor = dspy.ChainOfThought(VehicleDetailsExtractionSignature)

    def forward(self, conversation_history=None, user_message: str = ""):
        """Extract vehicle details with conversation context."""
        conversation_history = get_default_history(conversation_history)
        return self.predictor(
            conversation_history=conversation_history,
            user_message=user_message
        )


class DateParser(dspy.Module):
    """Parse natural language dates."""

    def __init__(self):
        super().__init__()
        self.predictor = dspy.ChainOfThought(DateParsingSignature)

    def forward(self, conversation_history=None, user_message: str = "", current_date: str = ""):
        """Parse date with conversation context."""
        conversation_history = get_default_history(conversation_history)
        return self.predictor(
            conversation_history=conversation_history,
            user_message=user_message,
            current_date=current_date
        )


class EmpathyResponseGenerator(dspy.Module):
    """Generate empathetic, context-aware responses."""

    def __init__(self):
        super().__init__()
        self.predictor = dspy.ChainOfThought(ResponseGenerationSignature)

    def forward(self, conversation_history=None, current_state: str = "", user_message: str = "", sentiment_context: str = ""):
        """Generate response with full conversation context."""
        conversation_history = get_default_history(conversation_history)
        return self.predictor(
            conversation_history=conversation_history,
            current_state=current_state,
            user_message=user_message,
            sentiment_context=sentiment_context
        )