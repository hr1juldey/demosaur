"""
Retroactive Data Validator - Scans conversation history for missing prerequisite data.

Uses DSPy conversation history to fill gaps in extracted data by searching earlier turns.
Runs synchronously to validate and complete data collection.

Not limited to vehicle details - works for ANY missing required data.
"""

import dspy
import logging
from typing import Dict, Any, Optional, List
from models import ValidatedName, ValidatedVehicleDetails, ValidatedDate, ExtractionMetadata
from modules import NameExtractor, VehicleDetailsExtractor, DateParser
from dspy_config import ensure_configured

logger = logging.getLogger(__name__)


class DataRequirements:
    """Define what data is required at each conversation state."""

    REQUIREMENTS = {
        "greeting": [],
        "name_collection": ["first_name", "last_name", "full_name"],
        "service_selection": ["first_name"],  # Must have name before service
        "vehicle_details": ["first_name", "vehicle_brand", "vehicle_model", "vehicle_plate"],
        "date_selection": ["first_name", "vehicle_brand", "vehicle_model", "vehicle_plate", "appointment_date"],
        "confirmation": ["first_name", "vehicle_brand", "vehicle_model", "vehicle_plate", "appointment_date"],
        "completed": ["first_name", "vehicle_brand", "vehicle_model", "vehicle_plate", "appointment_date"]
    }

    @classmethod
    def get_missing_fields(cls, current_state: str, extracted_data: Dict[str, Any]) -> List[str]:
        """
        Get list of missing required fields for current state.

        Args:
            current_state: Current conversation state (e.g., "vehicle_details")
            extracted_data: Dict of already extracted data

        Returns:
            List of field names that are missing but required
        """
        required = cls.REQUIREMENTS.get(current_state, [])
        missing = [
            field for field in required
            if field not in extracted_data
            or extracted_data[field] is None
            or str(extracted_data[field]).lower() in ["unknown", "none", ""]
        ]
        return missing


class RetroactiveScanner:
    """
    Scans conversation history to find and extract missing prerequisite data.

    Example:
        - State: confirmation
        - Missing: vehicle_brand, vehicle_model
        - Scan history for "I have a Honda City"
        - Extract retroactively using DSPy
    """

    def __init__(self):
        ensure_configured()
        
        self.name_extractor = NameExtractor()
        self.vehicle_extractor = VehicleDetailsExtractor()
        self.date_parser = DateParser()

    def scan_for_name(self, history: dspy.History) -> Optional[ValidatedName]:
        """
        Retroactively scan history for name mentions.

        Returns the most recent name mentioned in conversation.
        """
        if not history or not hasattr(history, 'messages'):
            return None

        try:
            # Get all user messages from history
            user_messages = [
                msg.get('content', '')
                for msg in history.messages
                if msg.get('role') == 'user'
            ]

            if not user_messages:
                return None

            # Try to extract name from most recent user message first
            for message in reversed(user_messages):
                try:
                    result = self.name_extractor(
                        conversation_history=history,
                        user_message=message
                    )

                    first_name = str(result.first_name).strip()
                    if first_name and first_name.lower() not in ["none", "n/a", "unknown"]:
                        return ValidatedName(
                            first_name=first_name,
                            last_name=str(result.last_name).strip() if hasattr(result, 'last_name') else "",
                            full_name=f"{first_name} {getattr(result, 'last_name', '')}".strip(),
                            metadata=ExtractionMetadata(
                                confidence=0.8,
                                extraction_method="retroactive_dspy",
                                extraction_source=message
                            )
                        )
                except Exception:
                    continue

            return None

        except Exception as e:
            logger.error(f"Retroactive name scan failed: {type(e).__name__}: {e}")
            return None

    def scan_for_vehicle_details(self, history: dspy.History) -> Optional[ValidatedVehicleDetails]:
        """
        Retroactively scan history for vehicle mentions.

        Searches for both brand/model AND plate number, combining them if found separately.
        """
        if not history or not hasattr(history, 'messages'):
            logger.debug("No history or no messages attribute")
            return None

        try:
            # Get all user messages
            user_messages = [
                msg.get('content', '')
                for msg in history.messages
                if msg.get('role') == 'user'
            ]

            if not user_messages:
                logger.debug("No user messages found in history")
                return None

            logger.debug(f"Found {len(user_messages)} user messages, combining last 3...")
            # Combine recent messages to create context (e.g., "I have Honda City with plate MH12AB1234")
            combined_context = " ".join(user_messages[-3:])  # Last 3 messages
            logger.debug(f"Combined context: '{combined_context[:100]}...'")

            # Try extraction on combined context
            try:
                result = self.vehicle_extractor(
                    conversation_history=history,
                    user_message=combined_context
                )

                brand = str(result.brand).strip() if result.brand else None
                model = str(result.model).strip() if result.model else None
                plate = str(result.number_plate).strip() if result.number_plate else None

                # Only return if we have at least some data
                if brand or model or plate:
                    if brand and brand.lower() not in ["unknown", "none"]:
                        return ValidatedVehicleDetails(
                            brand=brand,
                            model=model or "Unknown",
                            number_plate=plate or "Unknown",
                            metadata=ExtractionMetadata(
                                confidence=0.75,
                                extraction_method="retroactive_combined",
                                extraction_source=combined_context
                            )
                        )
                    elif plate and plate.lower() not in ["unknown", "none"]:
                        return ValidatedVehicleDetails(
                            brand=brand or "Unknown",
                            model=model or "Unknown",
                            number_plate=plate,
                            metadata=ExtractionMetadata(
                                confidence=0.75,
                                extraction_method="retroactive_combined",
                                extraction_source=combined_context
                            )
                        )

            except Exception:
                pass

            return None

        except Exception as e:
            logger.error(f"Retroactive vehicle scan failed: {type(e).__name__}: {e}")
            return None

    def scan_for_date(self, history: dspy.History) -> Optional[ValidatedDate]:
        """
        Retroactively scan history for date mentions.

        Searches all user messages for date references.
        """
        if not history or not hasattr(history, 'messages'):
            return None

        try:
            user_messages = [
                msg.get('content', '')
                for msg in history.messages
                if msg.get('role') == 'user'
            ]

            if not user_messages:
                return None

            # Try most recent date-like message first
            for message in reversed(user_messages):
                try:
                    result = self.date_parser(
                        user_message=message,
                        conversation_history=history
                    )

                    date_str = str(result.date_str).strip() if result.date_str else None
                    if date_str and date_str.lower() not in ["none", "unknown"]:
                        return ValidatedDate(
                            date_str=date_str,
                            confidence=0.8,
                            metadata=ExtractionMetadata(
                                confidence=0.8,
                                extraction_method="retroactive_dspy",
                                extraction_source=message
                            )
                        )
                except Exception:
                    continue

            return None

        except Exception as e:
            logger.error(f"Retroactive date scan failed: {type(e).__name__}: {e}")
            return None


class ConversationValidator:
    """
    Final validation sweep - checks for missing prerequisite data and fills gaps retroactively.
    """

    def __init__(self):
        self.scanner = RetroactiveScanner()

    def validate_and_complete(
        self,
        current_state: str,
        extracted_data: Dict[str, Any],
        history: dspy.History
    ) -> Dict[str, Any]:
        """
        Validate state requirements and retroactively fill missing data.

        SYNCHRONOUS VERSION - runs directly without async/await.

        Args:
            current_state: Current conversation state
            extracted_data: Already extracted data
            history: Conversation history

        Returns:
            Updated extracted_data with retroactively filled fields
        """
        missing_fields = DataRequirements.get_missing_fields(current_state, extracted_data)

        if not missing_fields:
            return extracted_data  # All required data present

        logger.info(f"Missing fields in {current_state}: {missing_fields}")

        # Retroactively scan for missing data
        updated_data = extracted_data.copy()

        if "first_name" in missing_fields or "last_name" in missing_fields or "full_name" in missing_fields:
            name_data = self.scanner.scan_for_name(history)
            if name_data:
                updated_data.update({
                    "first_name": name_data.first_name,
                    "last_name": name_data.last_name,
                    "full_name": name_data.full_name
                })
                logger.info(f"Retroactively filled name: {name_data.full_name}")

        if any(field in missing_fields for field in ["vehicle_brand", "vehicle_model", "vehicle_plate"]):
            vehicle_data = self.scanner.scan_for_vehicle_details(history)
            if vehicle_data:
                updated_data.update({
                    "vehicle_brand": vehicle_data.brand,
                    "vehicle_model": vehicle_data.model,
                    "vehicle_plate": vehicle_data.number_plate
                })
                logger.info(f"Retroactively filled vehicle: {vehicle_data.brand} {vehicle_data.model}")

        if "appointment_date" in missing_fields:
            date_data = self.scanner.scan_for_date(history)
            if date_data:
                updated_data["appointment_date"] = date_data.date_str
                logger.info(f"Retroactively filled date: {date_data.date_str}")

        return updated_data


# Example usage in orchestrator
def final_validation_sweep(
    current_state: str,
    extracted_data: Dict[str, Any],
    history: dspy.History
) -> Dict[str, Any]:
    """
    Run final validation sweep synchronously.

    Can be called before confirmation state to ensure all required data is present.
    """
    validator = ConversationValidator()
    return validator.validate_and_complete(current_state, extracted_data, history)