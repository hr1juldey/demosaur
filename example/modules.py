"""
DSPy modules (predictors) for different tasks.
"""
import dspy
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

    def forward(self, conversation_history: str, current_message: str):
        """Analyze sentiment."""
        result = self.predictor(
            conversation_history=conversation_history,
            current_message=current_message
        )
        return result


class IntentClassifier(dspy.Module):
    """Classify user intent using DSPy Chain of Thought."""

    def __init__(self):
        super().__init__()
        self.predictor = dspy.ChainOfThought(IntentClassificationSignature)

    def forward(self, conversation_history: str, current_message: str):
        """Classify user intent."""
        result = self.predictor(
            conversation_history=conversation_history,
            current_message=current_message
        )
        return result


class NameExtractor(dspy.Module):
    """Extract customer name from unstructured text."""

    def __init__(self):
        super().__init__()
        self.predictor = dspy.ChainOfThought(NameExtractionSignature)

    def forward(self, user_message: str, context: str = "collecting customer name"):
        """Extract name."""
        result = self.predictor(
            user_message=user_message,
            context=context
        )
        return result


class VehicleDetailsExtractor(dspy.Module):
    """Extract vehicle details from unstructured text."""

    def __init__(self):
        super().__init__()
        self.predictor = dspy.ChainOfThought(VehicleDetailsExtractionSignature)

    def forward(self, user_message: str):
        """Extract vehicle details."""
        result = self.predictor(user_message=user_message)
        return result


class DateParser(dspy.Module):
    """Parse natural language dates."""

    def __init__(self):
        super().__init__()
        self.predictor = dspy.ChainOfThought(DateParsingSignature)

    def forward(self, user_message: str, current_date: str):
        """Parse date from natural language."""
        result = self.predictor(
            user_message=user_message,
            current_date=current_date
        )
        return result


class EmpathyResponseGenerator(dspy.Module):
    """Generate empathetic, context-aware responses."""

    def __init__(self):
        super().__init__()
        self.predictor = dspy.ChainOfThought(ResponseGenerationSignature)

    def forward(
        self,
        conversation_history: str,
        current_state: str,
        user_message: str,
        sentiment_context: str
    ):
        """Generate empathetic response."""
        result = self.predictor(
            conversation_history=conversation_history,
            current_state=current_state,
            user_message=user_message,
            sentiment_context=sentiment_context
        )
        return result
