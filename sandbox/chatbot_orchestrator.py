"""
Main chatbot orchestrator that coordinates all components.
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
from config import config, ConversationState
from conversation_manager import ConversationManager
from sentiment_analyzer import SentimentAnalysisService, SentimentScores
from data_extractor import DataExtractionService


@dataclass
class ChatbotResponse:
    """Response from chatbot with metadata."""
    message: str
    should_proceed: bool
    extracted_data: Optional[Dict[str, Any]] = None
    sentiment: Optional[Dict[str, float]] = None
    suggestions: Optional[Dict[str, Any]] = None


class ChatbotOrchestrator:
    """Main orchestrator for intelligent chatbot."""
    
    def __init__(self):
        self.conversation_manager = ConversationManager()
        self.sentiment_service = SentimentAnalysisService()
        self.data_extractor = DataExtractionService()
        self._message_count: Dict[str, int] = {}
    
    def process_message(
        self,
        conversation_id: str,
        user_message: str,
        current_state: ConversationState
    ) -> ChatbotResponse:
        """Process incoming user message with intelligence layer."""
        
        # Update conversation
        context = self.conversation_manager.add_user_message(
            conversation_id,
            user_message
        )
        context.state = current_state
        
        # Track message count for sentiment checking
        if conversation_id not in self._message_count:
            self._message_count[conversation_id] = 0
        self._message_count[conversation_id] += 1
        
        # Analyze sentiment periodically
        sentiment = None
        should_proceed = True
        
        if self._message_count[conversation_id] % config.SENTIMENT_CHECK_INTERVAL == 0:
            sentiment = self._analyze_sentiment(context, user_message)
            should_proceed = sentiment.should_proceed()
        
        # Extract data based on current state
        extracted_data = self._extract_data_for_state(
            current_state,
            user_message
        )
        
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
            current_state,
            sentiment,
            extracted_data
        )
        
        return ChatbotResponse(
            message=self._create_response_message(
                current_state,
                sentiment,
                extracted_data
            ),
            should_proceed=should_proceed,
            extracted_data=extracted_data,
            sentiment=sentiment.to_dict() if sentiment else None,
            suggestions=suggestions
        )
    
    def _analyze_sentiment(
        self,
        context,
        current_message: str
    ) -> SentimentScores:
        """Analyze customer sentiment."""
        history = context.get_history_text(max_messages=10)
        return self.sentiment_service.analyze(history, current_message)
    
    def _extract_data_for_state(
        self,
        state: ConversationState,
        user_message: str
    ) -> Optional[Dict[str, Any]]:
        """Extract relevant data based on current state."""
        
        if state == ConversationState.NAME_COLLECTION:
            name_data = self.data_extractor.extract_name(user_message)
            if name_data:
                return {
                    "first_name": name_data.first_name,
                    "last_name": name_data.last_name,
                    "full_name": name_data.full_name
                }
        
        elif state == ConversationState.VEHICLE_DETAILS:
            vehicle_data = self.data_extractor.extract_vehicle_details(user_message)
            if vehicle_data:
                return {
                    "vehicle_brand": vehicle_data.brand,
                    "vehicle_model": vehicle_data.model,
                    "vehicle_plate": vehicle_data.number_plate
                }
        
        elif state == ConversationState.DATE_SELECTION:
            date_data = self.data_extractor.parse_date(user_message)
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
        sentiment: Optional[SentimentScores],
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
        state: ConversationState,
        sentiment: Optional[SentimentScores],
        extracted_data: Optional[Dict[str, Any]]
    ) -> str:
        """Create contextual response message."""
        if not extracted_data:
            return "I didn't quite catch that. Could you please try again?"
        
        # Acknowledge extraction
        if "full_name" in extracted_data:
            return f"Got it! Nice to meet you, {extracted_data['full_name']}!"
        elif "vehicle_brand" in extracted_data:
            return f"Perfect! I have your {extracted_data['vehicle_brand']} details."
        elif "appointment_date" in extracted_data:
            return f"Great! I've noted {extracted_data['appointment_date']} for your appointment."
        
        return "Thank you! Let's continue."
