"""
Extraction Coordinator - Coordinates data extraction process.

Single Responsibility: Coordinate extraction of user data (name, phone, vehicle, date, intent, typos).
Reason to change: Extraction coordination logic changes.
"""
import dspy
import logging
from typing import Dict, Any, Optional
from config import ConversationState
from data_extractor import DataExtractionService
from models import ValidatedIntent, ExtractionMetadata
from dspy_config import ensure_configured

logger = logging.getLogger(__name__)


class ExtractionCoordinator:
    """
    Coordinates data extraction from user messages.

    Follows Single Responsibility Principle (SRP):
    - Only handles coordination of extraction services
    - Does NOT handle state management, response generation, or scratchpad updates
    """

    def __init__(self):
        """Initialize extraction coordinator with data extractor."""
        self.data_extractor = DataExtractionService()

    def _is_vehicle_brand(self, text: str) -> bool:
        """
        Check if text matches any known vehicle brand from VehicleBrandEnum.

        Uses centralized vehicle brand list from models.py to prevent
        extracting vehicle brands as customer names.

        Example: "Mahindra" or "Honda City" should return True

        Args:
            text: Text to check (e.g., first_name, last_name)

        Returns:
            True if text matches a vehicle brand, False otherwise
        """
        from models import VehicleBrandEnum

        if not text or not text.strip():
            return False

        text_lower = text.lower().strip()

        # Check if text matches any vehicle brand (case-insensitive)
        return any(
            brand.value.lower() in text_lower or text_lower in brand.value.lower()
            for brand in VehicleBrandEnum
        )

    def extract_for_state(
        self,
        state: ConversationState,
        user_message: str,
        history: dspy.History
    ) -> Optional[Dict[str, Any]]:
        """
        Extract relevant data based on current conversation state.

        PHASE 1 BEHAVIOR: Extraction happens in ALL states (not just specific ones).
        This allows the retroactive validator and state machine to work properly.

        Args:
            state: Current conversation state
            user_message: User's raw message
            history: Conversation history

        Returns:
            Dictionary of extracted data or None
        """
        extracted = {}

        # Try extracting NAME in any state (Phase 1 behavior)
        try:
            name_data = self.data_extractor.extract_name(user_message, history)
            if name_data:
                first_name = str(name_data.first_name).strip()
                last_name = str(name_data.last_name).strip() if hasattr(name_data, 'last_name') else ""

                # VALIDATION: Reject if extracted name is actually a vehicle brand
                # Fixes ISSUE_NAME_VEHICLE_CONFUSION (e.g., "Mahindra Scorpio" extracted as name)
                if self._is_vehicle_brand(first_name) or self._is_vehicle_brand(last_name):
                    logger.warning(f"❌ Rejected name extraction: '{first_name} {last_name}' matches vehicle brand")
                elif first_name and first_name.lower() not in ["none", "n/a", "unknown"]:
                    extracted["first_name"] = first_name
                    extracted["last_name"] = last_name
                    extracted["full_name"] = f"{first_name} {last_name}".strip()
                    logger.debug(f"✅ Extracted valid name: {extracted['full_name']}")
        except Exception as e:
            logger.debug(f"Name extraction failed: {e}")

        # Try extracting PHONE in any state (Phase 1 behavior)
        # IMPORTANT: Extract phone BEFORE vehicle to avoid confusion with plate numbers
        try:
            phone_data = self.data_extractor.extract_phone(user_message, history)
            if phone_data:
                phone_number = str(phone_data.phone_number).strip() if phone_data.phone_number else None
                if phone_number and phone_number.lower() not in ["none", "unknown", "n/a"]:
                    extracted["phone"] = phone_number
        except Exception as e:
            logger.debug(f"Phone extraction failed: {e}")

        # Try extracting VEHICLE in any state (Phase 1 behavior)
        try:
            vehicle_data = self.data_extractor.extract_vehicle_details(user_message, history)
            if vehicle_data:
                brand = str(vehicle_data.brand).strip() if vehicle_data.brand else None
                if brand and brand.lower() not in ["none", "unknown"]:
                    extracted["vehicle_brand"] = brand
                    extracted["vehicle_model"] = str(vehicle_data.model).strip() if vehicle_data.model else "Unknown"
                    extracted["vehicle_plate"] = str(vehicle_data.number_plate).strip() if vehicle_data.number_plate else "Unknown"
        except Exception as e:
            logger.debug(f"Vehicle extraction failed: {e}")

        # Try extracting DATE in any state (Phase 1 behavior)
        try:
            date_data = self.data_extractor.parse_date(user_message, history)
            if date_data:
                date_str = str(date_data.date_str).strip() if date_data.date_str else None
                if date_str and date_str.lower() not in ["none", "unknown"]:
                    extracted["appointment_date"] = date_str
        except Exception as e:
            logger.debug(f"Date extraction failed: {e}")

        # Return extracted data if any, otherwise None
        return extracted if extracted else None

    def classify_intent(self, history: dspy.History, user_message: str) -> ValidatedIntent:
        """
        Classify customer intent (pricing, booking, complaint, etc.).

        Args:
            history: Conversation history
            user_message: User's raw message

        Returns:
            Validated intent with confidence score
        """
        from modules import IntentClassifier

        ensure_configured()
        try:
            classifier = IntentClassifier()
            result = classifier(
                conversation_history=history,
                current_message=user_message
            )
            intent_class = str(result.intent_class).strip().lower()
            return ValidatedIntent(
                intent_class=intent_class,
                confidence=0.8,
                reasoning=str(result.reasoning),
                metadata=ExtractionMetadata(
                    confidence=0.8,
                    extraction_method="dspy",
                    extraction_source=user_message
                )
            )
        except Exception as e:
            logger.warning(f"Intent classification failed: {type(e).__name__}: {e}, defaulting to inquire")
            return ValidatedIntent(
                intent_class="inquire",
                confidence=0.0,
                reasoning="Failed to classify intent, using default",
                metadata=ExtractionMetadata(
                    confidence=0.0,
                    extraction_method="fallback",
                    extraction_source=user_message
                )
            )

    def detect_typos_in_confirmation(
        self,
        extracted_data: Dict[str, Any],
        user_message: str,
        history: dspy.History
    ) -> Optional[Dict[str, str]]:
        """
        Detect typos in extracted data using DSPy TypoDetector module.

        Args:
            extracted_data: Data extracted from user message
            user_message: User's raw message
            history: Conversation history

        Returns:
            Dictionary of field_name -> correction or None
        """
        from modules import TypoDetector

        ensure_configured()
        try:
            typo_detector = TypoDetector()
            corrections = {}

            # Check each extracted field for typos
            for field_name, value in extracted_data.items():
                if isinstance(value, str) and len(value.strip()) > 0:
                    result = typo_detector(
                        input_text=value,
                        conversation_history=history,
                        field_name=field_name
                    )
                    if result and hasattr(result, 'has_typo') and result.has_typo:
                        if hasattr(result, 'correction') and result.correction:
                            corrections[field_name] = result.correction

            return corrections if corrections else None
        except Exception as e:
            logger.debug(f"Typo detection failed: {e}")
            return None