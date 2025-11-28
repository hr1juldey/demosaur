"""
State Coordinator - Manages conversation state transitions.

Single Responsibility: Determine next state based on extracted data, sentiment, and user input.
Reason to change: State machine logic changes.
"""
import logging
from typing import Dict, Any, Optional
from config import ConversationState
from models import ValidatedSentimentScores

logger = logging.getLogger(__name__)


class StateCoordinator:
    """
    Coordinates state transitions in the conversation flow.

    Follows Single Responsibility Principle (SRP):
    - Only handles state transition logic
    - Does NOT handle data extraction, sentiment analysis, or response generation
    """

    def determine_next_state(
        self,
        current_state: ConversationState,
        sentiment: Optional[ValidatedSentimentScores],
        extracted_data: Optional[Dict[str, Any]],
        user_message: str
    ) -> ConversationState:
        """
        Determine next state based on sentiment, extracted data, and context.

        Args:
            current_state: Current conversation state
            sentiment: Validated sentiment scores
            extracted_data: Data extracted from user message
            user_message: Raw user message

        Returns:
            Next conversation state
        """
        # If angry/upset, offer help instead of pushing forward
        if sentiment and sentiment.anger > 6.0:
            return ConversationState.SERVICE_SELECTION

        # If user confirms at confirmation state, move to COMPLETED
        if current_state == ConversationState.CONFIRMATION:
            confirm_keywords = ["yes", "confirm", "confirmed", "correct", "proceed", "ok", "go", "book", "let's", "lets"]
            if any(kw in user_message.lower() for kw in confirm_keywords):
                return ConversationState.COMPLETED

        # If data extracted, advance state based on data type
        if extracted_data:
            # Name extraction - move to NAME_COLLECTION
            if any(k in extracted_data for k in ["first_name", "full_name"]):
                if current_state in [ConversationState.GREETING, ConversationState.SERVICE_SELECTION]:
                    return ConversationState.NAME_COLLECTION

            # Phone extraction - advance from NAME_COLLECTION
            if "phone" in extracted_data:
                if current_state == ConversationState.NAME_COLLECTION:
                    return ConversationState.VEHICLE_DETAILS

            # Vehicle extraction - move to VEHICLE_DETAILS
            if any(k in extracted_data for k in ["vehicle_brand", "vehicle_model", "vehicle_plate"]):
                if current_state in [ConversationState.NAME_COLLECTION, ConversationState.SERVICE_SELECTION]:
                    return ConversationState.VEHICLE_DETAILS
                elif current_state == ConversationState.VEHICLE_DETAILS:
                    # Stay in VEHICLE_DETAILS if already there
                    return ConversationState.DATE_SELECTION

            # Date extraction - move to DATE_SELECTION
            if "appointment_date" in extracted_data:
                if current_state in [ConversationState.VEHICLE_DETAILS, ConversationState.SERVICE_SELECTION]:
                    return ConversationState.DATE_SELECTION
                elif current_state == ConversationState.DATE_SELECTION:
                    # Date confirmed, move to confirmation
                    return ConversationState.CONFIRMATION

            # General progression from NAME_COLLECTION
            if current_state == ConversationState.NAME_COLLECTION:
                return ConversationState.VEHICLE_DETAILS
            elif current_state == ConversationState.VEHICLE_DETAILS:
                return ConversationState.DATE_SELECTION
            elif current_state == ConversationState.DATE_SELECTION:
                return ConversationState.CONFIRMATION

        # If user asks about services/pricing, go to service selection (but allow escape)
        service_keywords = ["service", "price", "cost", "offer", "plan", "what do you"]
        if any(kw in user_message.lower() for kw in service_keywords):
            # Only transition TO service_selection from GREETING, not from other states
            if current_state == ConversationState.GREETING:
                return ConversationState.SERVICE_SELECTION

        # Otherwise stay in current state
        return current_state

    def determine_state_change_reason(
        self,
        user_message: str,
        sentiment: Optional[ValidatedSentimentScores],
        extracted_data: Optional[Dict[str, Any]]
    ) -> str:
        """
        Determine human-readable reason for state change.

        Args:
            user_message: Raw user message
            sentiment: Validated sentiment scores
            extracted_data: Data extracted from user message

        Returns:
            Human-readable reason string
        """
        if extracted_data:
            data_type = list(extracted_data.keys())[0]
            return f"Extracted {data_type} from message"
        if sentiment and sentiment.anger > 6.0:
            return "Customer upset - offering service selection"
        return "User interest detected"