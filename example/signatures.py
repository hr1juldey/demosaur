"""
DSPy signatures for different chatbot tasks.
"""
import dspy


class SentimentAnalysisSignature(dspy.Signature):
    """Analyze customer sentiment across multiple dimensions."""
    
    conversation_history = dspy.InputField(
        desc="Recent conversation messages between user and assistant"
    )
    current_message = dspy.InputField(
        desc="Current user message to analyze"
    )
    
    reasoning = dspy.OutputField(
        desc="Brief explanation of the sentiment analysis"
    )
    interest_score = dspy.OutputField(
        desc="Interest level from 1-10"
    )
    anger_score = dspy.OutputField(
        desc="Anger level from 1-10"
    )
    disgust_score = dspy.OutputField(
        desc="Disgust level from 1-10"
    )
    boredom_score = dspy.OutputField(
        desc="Boredom level from 1-10"
    )
    neutral_score = dspy.OutputField(
        desc="Neutral level from 1-10"
    )


class NameExtractionSignature(dspy.Signature):
    """Extract customer name from unstructured input."""
    
    user_message = dspy.InputField(
        desc="User's message that may contain their name"
    )
    context = dspy.InputField(
        desc="Conversation context indicating we're collecting name"
    )
    
    first_name = dspy.OutputField(
        desc="Extracted first name only, properly capitalized"
    )
    last_name = dspy.OutputField(
        desc="Extracted last name if provided, empty string otherwise"
    )
    confidence = dspy.OutputField(
        desc="Confidence in extraction (low/medium/high)"
    )


class VehicleDetailsExtractionSignature(dspy.Signature):
    """Extract vehicle details from unstructured input."""
    
    user_message = dspy.InputField(
        desc="User's message containing vehicle information"
    )
    
    brand = dspy.OutputField(
        desc="Vehicle brand/make (e.g., Toyota, Honda, BMW)"
    )
    model = dspy.OutputField(
        desc="Vehicle model name (e.g., Corolla, Civic, X5)"
    )
    number_plate = dspy.OutputField(
        desc="License plate number, normalized format"
    )


class DateParsingSignature(dspy.Signature):
    """Parse natural language date into structured format."""
    
    user_message = dspy.InputField(
        desc="User's message containing date/day reference"
    )
    current_date = dspy.InputField(
        desc="Today's date for reference (YYYY-MM-DD format)"
    )
    
    parsed_date = dspy.OutputField(
        desc="Parsed date in YYYY-MM-DD format"
    )
    confidence = dspy.OutputField(
        desc="Confidence in parsing (low/medium/high)"
    )


class ResponseGenerationSignature(dspy.Signature):
    """Generate empathetic, context-aware response."""
    
    conversation_history = dspy.InputField(
        desc="Recent conversation context"
    )
    current_state = dspy.InputField(
        desc="Current conversation state (e.g., collecting name, service selection)"
    )
    user_message = dspy.InputField(
        desc="Latest user message"
    )
    sentiment_context = dspy.InputField(
        desc="Current sentiment analysis summary"
    )
    
    response = dspy.OutputField(
        desc="Natural, empathetic response that maintains conversation flow"
    )
