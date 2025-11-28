"""
Message Processor - Main orchestrator coordinating all chatbot components.

Single Responsibility: Coordinate high-level message processing flow.
Reason to change: Overall message processing flow changes.

This is the ONLY class that should coordinate between components.
All other logic is delegated to specialized coordinators.
"""
import dspy
import logging
from typing import Dict, Any, Optional
from config import ConversationState
from conversation_manager import ConversationManager
from sentiment_analyzer import SentimentAnalysisService
from response_composer import ResponseComposer
from template_manager import TemplateManager
from models import ValidatedChatbotResponse
from retroactive_validator import final_validation_sweep

# Import coordinators (SRP-compliant modules)
from .state_coordinator import StateCoordinator
from .extraction_coordinator import ExtractionCoordinator
from .scratchpad_coordinator import ScratchpadCoordinator

logger = logging.getLogger(__name__)


class MessageProcessor:
    """
    Main orchestrator coordinating message processing flow.

    Follows Single Responsibility Principle (SRP):
    - Only coordinates high-level flow
    - Delegates to specialized coordinators for specific tasks
    - Does NOT contain extraction, state transition, or scratchpad logic
    """

    def __init__(self):
        """Initialize message processor with all required services and coordinators."""
        # Core services
        self.conversation_manager = ConversationManager()
        self.sentiment_service = SentimentAnalysisService()
        self.response_composer = ResponseComposer()
        self.template_manager = TemplateManager()

        # SRP-compliant coordinators
        self.state_coordinator = StateCoordinator()
        self.extraction_coordinator = ExtractionCoordinator()
        self.scratchpad_coordinator = ScratchpadCoordinator()

    def process_message(
        self,
        conversation_id: str,
        user_message: str
    ) -> ValidatedChatbotResponse:
        """
        Process incoming user message with intelligent sentiment + template-aware decisions.

        Flow:
        1. Store message in conversation
        2. Get current state from conversation context
        3. Analyze sentiment (multi-dimensional)
        4. Classify intent
        5. Determine response mode (template, LLM, or both)
        6. Extract structured data
        7. Compose final response
        8. Update state based on intent/context
        9. Update scratchpad

        State is managed internally - NOT provided by client.

        Args:
            conversation_id: Unique conversation identifier
            user_message: User's raw message

        Returns:
            ValidatedChatbotResponse with message, extracted data, state, etc.
        """
        # 1. Store user message and get conversation context
        context = self.conversation_manager.add_user_message(conversation_id, user_message)
        history = self.conversation_manager.get_dspy_history(conversation_id)

        # 2. Get current state from stored conversation context
        current_state = context.state

        # 2a. Classify user intent (delegated to ExtractionCoordinator)
        intent = self.extraction_coordinator.classify_intent(history, user_message)

        # 2b. Analyze sentiment (interest, anger, disgust, boredom, neutral)
        sentiment = self.sentiment_service.analyze(history, user_message)

        # 2c. Convert sentiment values to float (handle JSON string deserialization)
        if sentiment:
            try:
                sentiment.interest = float(sentiment.interest)
                sentiment.anger = float(sentiment.anger)
                sentiment.disgust = float(sentiment.disgust)
                sentiment.boredom = float(sentiment.boredom)
            except (ValueError, TypeError):
                # Fallback to defaults if conversion fails
                sentiment.interest = 5.0
                sentiment.anger = 1.0
                sentiment.disgust = 1.0
                sentiment.boredom = 1.0

        # 3. Decide response mode based on INTENT + SENTIMENT
        # Intent OVERRIDES sentiment (e.g., pricing inquiry always shows pricing template)
        response_mode, template_key = self.template_manager.decide_response_mode(
            user_message=user_message,
            intent=intent.intent_class,
            sentiment_interest=sentiment.interest if sentiment else 5.0,
            sentiment_anger=sentiment.anger if sentiment else 1.0,
            sentiment_disgust=sentiment.disgust if sentiment else 1.0,
            sentiment_boredom=sentiment.boredom if sentiment else 1.0,
            current_state=current_state.value
        )

        # 4. Extract structured data (delegated to ExtractionCoordinator)
        extracted_data = self.extraction_coordinator.extract_for_state(
            current_state, user_message, history
        )

        # 5. Generate LLM response if needed (empathetic conversation)
        llm_response = ""
        if self.template_manager.should_send_llm_response(response_mode):
            llm_response = self._generate_empathetic_response(
                history, user_message, current_state, sentiment, extracted_data
            )

        # 6. Compose final response (combines LLM + template intelligently)
        response = self.response_composer.compose_response(
            user_message=user_message,
            llm_response=llm_response,
            intent=intent.intent_class,
            sentiment_interest=sentiment.interest if sentiment else 5.0,
            sentiment_anger=sentiment.anger if sentiment else 1.0,
            sentiment_disgust=sentiment.disgust if sentiment else 1.0,
            sentiment_boredom=sentiment.boredom if sentiment else 1.0,
            current_state=current_state.value,
            template_variables=self._get_template_variables(extracted_data)
        )

        # 6.5. Run typo detection ONLY in CONFIRMATION state with extracted data
        # (delegated to ExtractionCoordinator)
        typo_corrections = None
        if current_state == ConversationState.CONFIRMATION and extracted_data:
            typo_corrections = self.extraction_coordinator.detect_typos_in_confirmation(
                extracted_data, user_message, history
            )

        # 7. Store extracted data in conversation context
        if extracted_data:
            for key, value in extracted_data.items():
                self.conversation_manager.store_user_data(conversation_id, key, value)

        # 7.5. Retroactively validate and complete missing prerequisite data
        try:
            logger.warning(f"🔄 RETROACTIVE: Starting sweep. State={current_state.value}, Extracted={extracted_data}")
            retroactive_data = final_validation_sweep(
                current_state=current_state.value,
                extracted_data=extracted_data if extracted_data else {},
                history=history
            )
            logger.warning(f"🔄 RETROACTIVE: Result={retroactive_data}")

            # Merge retroactively filled data with existing extracted data
            if retroactive_data:
                if not extracted_data:
                    extracted_data = {}
                # Track what changed (including improvements to "Unknown" values)
                improved_fields = []
                for key, value in retroactive_data.items():
                    old_value = extracted_data.get(key)
                    if old_value != value:
                        if str(old_value).lower() == "unknown" and str(value).lower() != "unknown":
                            improved_fields.append(f"{key}: {old_value}→{value}")
                        elif key not in extracted_data or old_value is None:
                            improved_fields.append(key)
                    extracted_data[key] = value
                if improved_fields:
                    logger.warning(f"⚡ RETROACTIVE IMPROVEMENTS: {improved_fields}")
                # Store retroactively filled data
                for key, value in retroactive_data.items():
                    self.conversation_manager.store_user_data(conversation_id, key, value)
        except Exception as e:
            logger.error(f"❌ Retroactive validation ERROR: {type(e).__name__}: {e}", exc_info=True)

        # 8. Determine next state (delegated to StateCoordinator)
        next_state = self.state_coordinator.determine_next_state(
            current_state, sentiment, extracted_data, user_message
        )
        if next_state != current_state:
            reason = self.state_coordinator.determine_state_change_reason(
                user_message, sentiment, extracted_data
            )
            self.conversation_manager.update_state(conversation_id, next_state, reason)

        # 9. Update scratchpad AFTER state transition (delegated to ScratchpadCoordinator)
        scratchpad = self.scratchpad_coordinator.get_or_create(conversation_id)
        if extracted_data:
            for key, value in extracted_data.items():
                # Use next_state here so scratchpad updates correctly
                self.scratchpad_coordinator.update_from_extraction(
                    scratchpad, next_state, key, value
                )

        # 10. Create validated response
        # Confirmation should only happen when ALL required fields are present
        # CONFIRMATION state requires: first_name, vehicle_brand, vehicle_model, vehicle_plate, appointment_date
        from retroactive_validator import DataRequirements
        required_fields = set(DataRequirements.REQUIREMENTS.get(ConversationState.CONFIRMATION.value, []))
        extracted_fields = set(extracted_data.keys()) if extracted_data else set()

        # Check if ALL required fields are present in extracted data (from current turn + retroactive scans)
        has_all_required = required_fields.issubset(extracted_fields)

        should_confirm = (
            next_state == ConversationState.CONFIRMATION and
            has_all_required
        )

        data_extracted_this_turn = extracted_data is not None and len(extracted_data) > 0
        scratchpad_completeness = scratchpad.get_completeness()

        return ValidatedChatbotResponse(
            message=response["response"],
            should_proceed=True,
            extracted_data=extracted_data,
            sentiment=sentiment.to_dict() if sentiment else None,
            suggestions={},
            processing_time_ms=0,
            confidence_score=0.85,
            should_confirm=should_confirm,
            scratchpad_completeness=scratchpad_completeness,
            state=next_state.value,
            data_extracted=data_extracted_this_turn,
            typo_corrections=typo_corrections
        )

    def _generate_empathetic_response(
        self,
        history: dspy.History,
        user_message: str,
        current_state: ConversationState,
        sentiment,
        extracted_data: Optional[Dict[str, Any]]
    ) -> str:
        """Generate empathetic LLM response based on context and sentiment using DSPy pipeline."""
        from modules import SentimentToneAnalyzer, ToneAwareResponseGenerator

        try:
            # Step 1: Analyze sentiment and determine appropriate tone + brevity
            tone_analyzer = SentimentToneAnalyzer()
            tone_result = tone_analyzer(
                interest_score=sentiment.interest if sentiment else 5.0,
                anger_score=sentiment.anger if sentiment else 1.0,
                disgust_score=sentiment.disgust if sentiment else 1.0,
                boredom_score=sentiment.boredom if sentiment else 1.0,
                neutral_score=sentiment.neutral if sentiment else 1.0
            )

            tone_directive = tone_result.tone_directive if tone_result else "be helpful"
            max_sentences = tone_result.max_sentences if tone_result else "3"

            # Step 2: Generate response with tone and brevity constraints
            response_generator = ToneAwareResponseGenerator()
            result = response_generator(
                conversation_history=history,
                user_message=user_message,
                tone_directive=tone_directive,
                max_sentences=max_sentences,
                current_state=current_state.value
            )

            response = result.response if result else ""

            # Log the tone decision for debugging
            logger.debug(f"🎯 TONE ANALYSIS: tone='{tone_directive}' max_sentences={max_sentences}")

            # Ensure we never return empty string
            if not response or not response.strip():
                return "I understand. How can I help?"
            return response
        except Exception as e:
            logger.warning(f"Tone-aware generation failed: {e}, using fallback")
            return "I understand. How can I help?"

    def _get_template_variables(self, extracted_data: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """Extract variables needed for template rendering."""
        if not extracted_data:
            return {}
        return {k: str(v) for k, v in extracted_data.items()}