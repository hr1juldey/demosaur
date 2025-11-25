"""
Main chatbot orchestrator that coordinates all components.
"""
import asyncio
import concurrent.futures
import random
import time
import dspy
from typing import Dict, Any, Optional
from enum import Enum
from config import config, ConversationState
from conversation_manager import ConversationManager
from sentiment_analyzer import SentimentAnalysisService
from data_extractor import DataExtractionService
from modules import EmpathyResponseGenerator, IntentClassifier
from models import ValidatedChatbotResponse, ValidatedSentimentScores


class Intent(str, Enum):
    """Possible user intents."""
    BOOK = "book"
    INQUIRE = "inquire"
    COMPLAINT = "complaint"
    SMALL_TALK = "small_talk"
    CANCEL = "cancel"
    RESCHEDULE = "reschedule"
    PAYMENT = "payment"


class ChatbotOrchestrator:
    """Main orchestrator for intelligent chatbot."""

    def __init__(self):
        self.conversation_manager = ConversationManager()
        self.sentiment_service = SentimentAnalysisService()
        self.data_extractor = DataExtractionService()
        self.intent_classifier = IntentClassifier()  # LLM-based intent classifier
        self._message_count: Dict[str, int] = {}

        # ThreadPoolExecutor for parallel processing
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

        # Define state transition matrix
        self._state_transition_matrix = {
            ConversationState.GREETING: {
                Intent.BOOK: ConversationState.NAME_COLLECTION,
                Intent.INQUIRE: ConversationState.SERVICE_SELECTION,
                Intent.SMALL_TALK: ConversationState.GREETING
            },
            ConversationState.NAME_COLLECTION: {
                Intent.BOOK: ConversationState.VEHICLE_DETAILS,
                Intent.INQUIRE: ConversationState.SERVICE_SELECTION
            },
            ConversationState.VEHICLE_DETAILS: {
                Intent.BOOK: ConversationState.DATE_SELECTION,
                Intent.INQUIRE: ConversationState.SERVICE_SELECTION
            },
            ConversationState.DATE_SELECTION: {
                Intent.BOOK: ConversationState.CONFIRMATION,
                Intent.INQUIRE: ConversationState.SERVICE_SELECTION,
                Intent.RESCHEDULE: ConversationState.DATE_SELECTION
            },
            ConversationState.SERVICE_SELECTION: {
                Intent.BOOK: ConversationState.NAME_COLLECTION,
                Intent.INQUIRE: ConversationState.SERVICE_SELECTION
            },
            ConversationState.CONFIRMATION: {
                Intent.BOOK: ConversationState.COMPLETED,
                Intent.CANCEL: ConversationState.GREETING
            }
        }

    def detect_intent_keyword_based(self, user_message: str) -> Intent:
        """Detect user intent from message using keyword matching."""
        message_lower = user_message.lower()

        # Define keywords for each intent
        intent_keywords = {
            Intent.BOOK: ["book", "need", "wash", "service", "appointment", "schedule", "want", "get"],
            Intent.INQUIRE: ["what", "how", "price", "cost", "which", "service", "information", "tell", "offer"],
            Intent.COMPLAINT: ["problem", "issue", "angry", "upset", "bad", "complaint", "wrong", "disappointed"],
            Intent.CANCEL: ["cancel", "stop", "never", "canceling", "not interested"],
            Intent.RESCHEDULE: ["reschedule", "change", "move", "different time", "other time"],
            Intent.PAYMENT: ["pay", "payment", "money", "cost", "charge", "bill"]
        }

        # Count keyword matches for each intent
        intent_scores = {}
        for intent, keywords in intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
            intent_scores[intent] = score

        # Return the intent with the highest score, default to small_talk
        best_intent = max(intent_scores, key=intent_scores.get)
        if intent_scores[best_intent] == 0:
            return Intent.SMALL_TALK
        return best_intent

    def detect_intent_llm_based(self, conversation_history: dspy.History, user_message: str) -> Intent:
        """Detect user intent using LLM-based classification."""
        try:
            from modules import IntentClassifier
            intent_classifier = IntentClassifier()
            result = intent_classifier(conversation_history=conversation_history, current_message=user_message)
            # Convert the result to our Intent enum
            # If the LLM returns an unexpected intent, default to SMALL_TALK
            intent_value = result.intent_class.upper().replace(' ', '_').replace('-', '_')
            if intent_value in Intent.__members__:
                return Intent(intent_value)
            else:
                # If LLM provided an unknown intent, fall back to keyword detection
                return self.detect_intent_keyword_based(user_message)
        except Exception:
            # If LLM-based classification fails, fall back to keyword detection
            return self.detect_intent_keyword_based(user_message)

    def detect_intent(self, conversation_id: str, user_message: str) -> Intent:
        """Detect user intent from message using both keyword-based and LLM-based approaches."""
        # Try keyword-based detection first (fast)
        keyword_intent = self.detect_intent_keyword_based(user_message)

        # Get conversation history for context
        context = self.conversation_manager.get_or_create(conversation_id)
        # Create dspy.History object with conversation messages
        dspy_history = dspy.History(messages=[])
        for message in context.messages:
            dspy_history.messages.append({
                "role": message.role,
                "content": message.content
            })

        # Check if keyword-based detection confidence is low, or if user seems dissatisfied
        low_keyword_confidence = keyword_intent == Intent.SMALL_TALK
        user_correction = self._needs_llm_validation(user_message)

        # Use LLM-based detection for validation if confidence is low or disagreement detected
        if low_keyword_confidence or user_correction:
            llm_intent = self.detect_intent_llm_based(dspy_history, user_message)
            # If both methods agree, return the result
            if keyword_intent == llm_intent or not low_keyword_confidence:
                return llm_intent
            else:
                # In case of disagreement and low confidence, prefer LLM result
                return llm_intent
        else:
            # Keyword-based detection is confident, return it
            return keyword_intent

    def _needs_llm_validation(self, user_message: str) -> bool:
        """Check if user message suggests correction, dissatisfaction or complex intent."""
        message_lower = user_message.lower()
        # Keywords that suggest user is correcting the bot or expressing confusion/frustration
        correction_indicators = [
            "no", "not", "wrong", "that's not", "i meant", "actually", "but", "however",
            "are you sure", "you don't understand", "let me clarify", "i said",
            "this isn't", "you misunderstood", "what i meant"
        ]
        return any(indicator in message_lower for indicator in correction_indicators)

    def get_next_state(self, current_state: ConversationState, intent: Intent) -> ConversationState:
        """Determine the next state based on current state and detected intent."""
        # First check if there's a specific transition defined
        if current_state in self._state_transition_matrix:
            transitions = self._state_transition_matrix[current_state]
            if intent in transitions:
                return transitions[intent]

        # Default to staying in the same state if no transition is defined
        return current_state

    def simulate_human_behavior(self, response: str, conversation_context) -> str:
        """Add human-like behavior to the response."""
        # Add occasional casual language or fillers based on user's style
        if len(response) < 20 and random.random() < 0.3:  # For shorter messages
            casual_additions = ["Sure, ", "Okay, ", "Yes, ", "Great, ", "Alright, "]
            if random.random() < 0.5:
                response = random.choice(casual_additions) + response

        # Add slight variations to common responses to make them feel more natural
        if response.startswith("Got it!"):
            variations = [
                "Perfect!",
                "Alright!",
                "Great!",
                "Sounds good!",
                "Noted!"
            ]
            if random.random() < 0.3:
                response = random.choice(variations) + response[7:]  # Keep the rest of the message

        return response

    def add_response_delay(self, user_message: str, sentiment: Optional[ValidatedSentimentScores]):
        """Simulate human-like response delay."""
        base_delay = 0.5  # Base delay in seconds

        # Adjust delay based on message complexity
        word_count = len(user_message.split())
        if word_count > 10:  # Longer messages might need more consideration
            base_delay += random.uniform(0.5, 1.5)

        # Adjust based on sentiment - more negative sentiment might require more consideration
        if sentiment and sentiment.anger > 5.0:
            base_delay += random.uniform(0.5, 2.0)  # Take more time to respond to angry customers
        elif sentiment and sentiment.neutral > 7.0:
            base_delay -= 0.2  # Respond a bit faster to neutral messages

        # Add random variation to make it feel more natural
        delay = base_delay + random.uniform(0.1, 0.8)

        # Implement the delay
        time.sleep(min(delay, 3.0))  # Cap delay at 3 seconds for better UX

    def chunk_message(self, message: str) -> list[str]:
        """Split long messages into human-like chunks."""
        # Don't chunk if message is short
        if len(message) < 160:
            return [message]

        # Split by sentences or at reasonable breaks
        sentences = [s.strip() for s in message.split('.') if s.strip()]

        if len(sentences) > 1:
            # If multiple sentences, split into multiple messages
            chunks = []
            current_chunk = ""
            for sentence in sentences:
                if len(current_chunk + sentence + ".") > 160 and current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence + ". "
                else:
                    current_chunk += sentence + ". "

            if current_chunk:
                chunks.append(current_chunk.strip())

            return chunks
        else:
            # If only one long sentence, split by words
            words = message.split()
            chunks = []
            current_chunk = ""
            for word in words:
                if len(current_chunk + " " + word) > 160 and current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = word + " "
                else:
                    current_chunk += word + " "

            if current_chunk:
                chunks.append(current_chunk.strip())

            return chunks

    def process_message(
        self,
        conversation_id: str,
        user_message: str,
        current_state: ConversationState
    ) -> ValidatedChatbotResponse:
        """Process incoming user message with intelligence layer."""

        start_time = time.time()

        # Run intent detection and data extraction in parallel
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Submit intent detection
            intent_future = executor.submit(self.detect_intent, conversation_id, user_message)

            # Submit data extraction - now with conversation_id for history context
            extraction_future = executor.submit(self._extract_data_for_state, current_state, user_message, conversation_id)

            # Get results
            intent = intent_future.result()
            extracted_data = extraction_future.result()

        # Determine next state based on current state and intent
        next_state = self.get_next_state(current_state, intent)

        # Update conversation
        context = self.conversation_manager.add_user_message(
            conversation_id,
            user_message
        )

        # Update state with transition tracking
        reason = f"Intent detected: {intent.value}"
        self.conversation_manager.update_state(conversation_id, next_state, reason)

        # Track message count for sentiment checking
        if conversation_id not in self._message_count:
            self._message_count[conversation_id] = 0
        self._message_count[conversation_id] += 1

        # Analyze sentiment - now check for emotional context and call on every turn if needed
        sentiment = None
        should_proceed = True

        # Check if user expresses emotional language that warrants sentiment analysis
        emotional_indicators = [
            'angry', 'frustrated', 'happy', 'excited', 'sad', 'disappointed',
            'confused', 'annoyed', 'pleased', 'satisfied', 'angry', 'mad',
            'upset', 'stressed', 'worried', 'concerned', 'bored', 'skeptical'
        ]
        has_emotional_indicators = any(indicator in user_message.lower() for indicator in emotional_indicators)

        # Perform sentiment analysis either periodically OR when emotional indicators are present
        if (self._message_count[conversation_id] % config.SENTIMENT_CHECK_INTERVAL == 0) or has_emotional_indicators:
            # Perform sentiment analysis in parallel with other operations
            sentiment = self._analyze_sentiment(context, user_message)
            should_proceed = sentiment.should_proceed()

        # Simulate human-like response delay
        self.add_response_delay(user_message, sentiment)

        # Store extracted data
        if extracted_data:
            for key, value in extracted_data.items():
                self.conversation_manager.store_user_data(
                    conversation_id,
                    key,
                    value
                )

        # Generate suggestions
        suggestions = self._generate_suggestions(
            next_state,
            sentiment,
            extracted_data
        )

        response = self._create_response_message(
            conversation_id,
            next_state,  # Pass the determined next state
            sentiment,
            extracted_data
        )

        # Apply human-like behavior modifications
        response = self.simulate_human_behavior(response, context)

        # Split into chunks if needed
        response_chunks = self.chunk_message(response)

        # For now, return the first chunk; in a real implementation, you might want to handle multiple chunks differently
        final_response = response_chunks[0] if response_chunks else response

        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        # Create validated chatbot response
        validated_response = ValidatedChatbotResponse(
            message=final_response,
            should_proceed=should_proceed,
            extracted_data=extracted_data,
            sentiment=sentiment.to_dict() if sentiment else None,
            suggestions=suggestions,
            processing_time_ms=processing_time,
            confidence_score=0.8  # Default confidence
        )

        return validated_response

    def _analyze_sentiment(
        self,
        context,
        current_message: str
    ) -> ValidatedSentimentScores:
        """Analyze customer sentiment."""
        # Create dspy.History object with conversation messages for proper DSPy history management
        dspy_history = dspy.History(messages=[])
        for message in context.messages:
            dspy_history.messages.append({
                "role": message.role,
                "content": message.content
            })

        return self.sentiment_service.analyze(dspy_history, current_message)

    def _extract_data_for_state(
        self,
        state: ConversationState,
        user_message: str,
        conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Extract relevant data based on current state."""

        # Get conversation context for history
        context = self.conversation_manager.get_or_create(conversation_id)
        # Create dspy.History object with conversation messages
        history = dspy.History(messages=[])
        for message in context.messages:
            history.messages.append({
                "role": message.role,
                "content": message.content
            })

        if state == ConversationState.NAME_COLLECTION:
            name_data = self.data_extractor.extract_name(user_message, conversation_history=history)
            if name_data:
                return {
                    "first_name": name_data.first_name,
                    "last_name": name_data.last_name,
                    "full_name": name_data.full_name
                }

        elif state == ConversationState.VEHICLE_DETAILS:
            vehicle_data = self.data_extractor.extract_vehicle_details(user_message, conversation_history=history)
            if vehicle_data:
                return {
                    "vehicle_brand": vehicle_data.brand,
                    "vehicle_model": vehicle_data.model,
                    "vehicle_plate": vehicle_data.number_plate
                }

        elif state == ConversationState.DATE_SELECTION:
            date_data = self.data_extractor.parse_date(user_message, conversation_history=history)
            if date_data:
                return {"appointment_date": date_data.date_str}
            # Fallback to rule-based
            fallback_date = self.data_extractor.fallback_date_parsing(user_message)
            if fallback_date:
                return {"appointment_date": fallback_date}

        return None

    def _generate_suggestions(
        self,
        state: ConversationState,
        sentiment: Optional[ValidatedSentimentScores],
        extracted_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate suggestions for handling conversation."""
        suggestions = {
            "modify_response_tone": False,
            "add_engagement": False,
            "simplify_flow": False,
            "offer_help": False
        }

        if sentiment:
            if sentiment.should_disengage():
                suggestions["simplify_flow"] = True
                suggestions["offer_help"] = True
            elif sentiment.needs_engagement():
                suggestions["add_engagement"] = True

            if sentiment.boredom > 6.0:
                suggestions["modify_response_tone"] = True

        return suggestions

    def _create_response_message(
        self,
        conversation_id: str,
        state: ConversationState,
        sentiment: Optional[ValidatedSentimentScores],
        extracted_data: Optional[Dict[str, Any]]
    ) -> str:
        """Create contextual response message."""
        if not extracted_data:
            # Use EmpathyResponseGenerator when no data extraction occurs
            context = self.conversation_manager.get_or_create(conversation_id)
            conversation_history = context.get_history_text(max_messages=5)

            # Format sentiment for context if available
            sentiment_context = "No sentiment analysis available" if not sentiment else f"Interest: {sentiment.interest}, Anger: {sentiment.anger}, Disgust: {sentiment.disgust}, Boredom: {sentiment.boredom}, Neutral: {sentiment.neutral}"

            # Prepare user message from the last message in context
            user_message = context.messages[-1].content if context.messages else ""

            # Use empathy generator to create a contextual response
            try:
                empathy_generator = EmpathyResponseGenerator()
                response_result = empathy_generator(
                    conversation_history=conversation_history,
                    current_state=state.value,
                    user_message=user_message,
                    sentiment_context=sentiment_context
                )
                return response_result.response
            except Exception:
                # Check if extracted_data is for greeting/state that doesn't require extraction
                if state == ConversationState.GREETING:
                    # Use a simple greeting response when in greeting state with no extraction
                    greetings = ["Hello!", "Hi there!", "Greetings!", "Nice to meet you!", "How can I help you today?"]
                    import random
                    return random.choice(greetings)
                elif state == ConversationState.SERVICE_SELECTION:
                    return "I'd be happy to tell you about our services. We offer car wash, detailing, and polishing services. What would you like to know more about?"
                elif state == ConversationState.NAME_COLLECTION:
                    return "I'd love to know your name! What should I call you?"
                elif state == ConversationState.VEHICLE_DETAILS:
                    return "Could you please tell me about your vehicle - brand, model, and license plate number?"
                # Fallback for other states if empathy generation fails
                return "I'm not sure I understood that completely. Could you please provide more details?"

        # Acknowledge extraction
        if "full_name" in extracted_data:
            return f"Got it! Nice to meet you, {extracted_data['full_name']}!"
        elif "vehicle_brand" in extracted_data:
            return f"Perfect! I have your {extracted_data['vehicle_brand']} details."
        elif "appointment_date" in extracted_data:
            return f"Great! I've noted {extracted_data['appointment_date']} for your appointment."

        return "Thank you! Let's continue."