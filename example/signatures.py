"""
DSPy signatures for different chatbot tasks.
"""
import dspy


class SentimentAnalysisSignature(dspy.Signature):
    """Analyze customer sentiment across multiple dimensions."""

    conversation_history: dspy.History = dspy.InputField(
        desc="Full conversation history between user and assistant"
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

    conversation_history: dspy.History = dspy.InputField(
        desc="Full conversation history for context"
    )
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

    conversation_history: dspy.History = dspy.InputField(
        desc="Full conversation history for context"
    )
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

    conversation_history: dspy.History = dspy.InputField(
        desc="Full conversation history for context"
    )
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


class SentimentToneSignature(dspy.Signature):
    """Determine appropriate tone and brevity based on sentiment scores."""

    interest_score = dspy.InputField(
        desc="Customer interest level (1-10)"
    )
    anger_score = dspy.InputField(
        desc="Customer anger level (1-10)"
    )
    disgust_score = dspy.InputField(
        desc="Customer disgust level (1-10)"
    )
    boredom_score = dspy.InputField(
        desc="Customer boredom level (1-10)"
    )
    neutral_score = dspy.InputField(
        desc="Customer neutral level (1-10)"
    )

    tone_directive = dspy.OutputField(
        desc="Tone instruction (e.g., 'direct and brief', 'engaging and conversational', 'detailed and helpful')"
    )
    max_sentences = dspy.OutputField(
        desc="Maximum number of sentences (1-4)"
    )
    reasoning = dspy.OutputField(
        desc="Why this tone and length"
    )


class ToneAwareResponseSignature(dspy.Signature):
    """Generate response adapted to tone and brevity constraints."""

    conversation_history: dspy.History = dspy.InputField(
        desc="Full conversation history"
    )
    user_message = dspy.InputField(
        desc="Latest user message"
    )
    tone_directive = dspy.InputField(
        desc="Tone instruction from SentimentToneAnalyzer"
    )
    max_sentences = dspy.InputField(
        desc="Maximum number of sentences to use"
    )
    current_state = dspy.InputField(
        desc="Current conversation state"
    )

    response = dspy.OutputField(
        desc="Concise, tone-appropriate response within sentence limit"
    )


class ResponseGenerationSignature(dspy.Signature):
    """Generate empathetic, context-aware response."""

    conversation_history: dspy.History = dspy.InputField(
        desc="Full conversation history"
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


class IntentClassificationSignature(dspy.Signature):
    """Classify user intent from message in context."""

    conversation_history: dspy.History = dspy.InputField(
        desc="Full conversation history to understand user's intent"
    )
    current_message = dspy.InputField(
        desc="Current user message to classify"
    )

    reasoning = dspy.OutputField(
        desc="Step-by-step reasoning for the intent classification"
    )
    intent_class = dspy.OutputField(
        desc="The classified intent (one of: book, inquire, complaint, small_talk, cancel, reschedule, payment)"
    )


class TypoCorrectionSignature(dspy.Signature):
    """Detect typos in user response to service cards/action buttons and suggest corrections.

    ONLY triggers when:
    1. A service card with action buttons was just shown (confirmation, options, etc.)
    2. User response is a typo/gibberish/null (not a formed reply)
    3. User response is NOT a proper one-word answer like 'yes', 'no', 'ok'
    """

    last_bot_message = dspy.InputField(
        desc="The last bot message shown to user (service card/confirmation with buttons)"
    )
    user_response = dspy.InputField(
        desc="User's response to the service card (potentially a typo)"
    )
    expected_actions = dspy.InputField(
        desc="List of expected action words from the service card buttons (e.g., 'confirm, edit, cancel')"
    )

    is_typo = dspy.OutputField(
        desc="true if user response is a typo/gibberish, false if it's a valid response (even one word)"
    )
    intended_action = dspy.OutputField(
        desc="The likely intended action based on typo analysis (e.g., 'confirm' from 'confrim'). Empty if not a typo."
    )
    confidence = dspy.OutputField(
        desc="Confidence in typo detection and correction (low/medium/high)"
    )
    suggestion = dspy.OutputField(
        desc="Friendly 'Did you mean...?' message for the user. Empty if not a typo."
    )

