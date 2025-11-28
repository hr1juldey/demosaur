"""
Retroactive Data Validator - Scans conversation history for missing prerequisite data.

Uses DSPy conversation history to fill gaps in extracted data by searching earlier turns.
Runs synchronously to validate and complete data collection.

Not limited to vehicle details - works for ANY missing required data.
"""

import dspy
import logging
from typing import Dict, Any, Optional, List
from config import Config
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

    def _is_vehicle_brand(self, text: str) -> bool:
        """
        Check if text matches any known vehicle brand from VehicleBrandEnum.

        Prevents extracting vehicle brands as customer names in retroactive scans.

        Args:
            text: Text to check (e.g., first_name, last_name)

        Returns:
            True if text matches a vehicle brand, False otherwise
        """
        from models import VehicleBrandEnum

        if not text or not text.strip():
            return False

        text_lower = text.lower().strip()

        return any(
            brand.value.lower() in text_lower or text_lower in brand.value.lower()
            for brand in VehicleBrandEnum
        )

    def scan_for_name(self, history: dspy.History) -> Optional[ValidatedName]:
        """
        Retroactively scan history for name mentions.

        Returns the most recent name mentioned in conversation.
        """
        if not history or not hasattr(history, 'messages'):
            logger.debug("🔍 scan_for_name: No history or no messages attribute")
            return None

        try:
            from config import config

            # PERFORMANCE FIX: Only scan recent messages to prevent timeout
            # Use centralized config to control scan limit
            scan_limit = config.RETROACTIVE_SCAN_LIMIT
            recent_messages = history.messages[-scan_limit:] if len(history.messages) > scan_limit else history.messages

            # Get user messages from recent history only
            user_messages = [
                msg.get('content', '')
                for msg in recent_messages
                if msg.get('role') == 'user'
            ]

            logger.debug(f"🔍 scan_for_name: Scanning {len(user_messages)} recent user messages (limited to last {scan_limit})")
            if not user_messages:
                logger.debug("🔍 scan_for_name: No user messages found in recent history")
                return None

            # Try to extract name from most recent user message first
            for idx, message in enumerate(reversed(user_messages)):
                try:
                    logger.debug(f"🔍 scan_for_name: Attempting extraction from message: {message[:50]}...")
                    result = self.name_extractor(
                        conversation_history=history,
                        user_message=message
                    )

                    logger.debug(f"🔍 scan_for_name: Extraction result - first_name={result.first_name}, last_name={getattr(result, 'last_name', 'N/A')}")

                    # SANITIZATION: Strip quotes and clean DSPy output
                    # Fixes: DSPy sometimes returns '""' (quoted empty string) which fails Pydantic validation
                    first_name = str(result.first_name).strip().strip('"\'')
                    last_name = str(result.last_name).strip().strip('"\'') if hasattr(result, 'last_name') else ""

                    # VALIDATION: Reject if extracted name is actually a vehicle brand
                    # Fixes ISSUE_NAME_VEHICLE_CONFUSION
                    if self._is_vehicle_brand(first_name) or self._is_vehicle_brand(last_name):
                        logger.warning(f"❌ Retroactive scan rejected: '{first_name} {last_name}' matches vehicle brand")
                        continue  # Skip to next message

                    # VALIDATION: Reject if extracted name is a greeting stopword
                    # Fixes: Prevent "Haan" (Hindi yes), "Hello", "Hi" etc. from being extracted as first_name
                    if first_name and first_name.lower() in Config.GREETING_STOPWORDS:
                        logger.warning(f"❌ Retroactive scan rejected: '{first_name}' is a greeting stopword")
                        continue  # Skip to next message

                    if first_name and first_name.lower() not in ["none", "n/a", "unknown"]:
                        logger.info(f"✅ scan_for_name: Successfully extracted '{first_name}'")
                        return ValidatedName(
                            first_name=first_name,
                            last_name=last_name,
                            full_name=f"{first_name} {last_name}".strip(),
                            metadata=ExtractionMetadata(
                                confidence=0.8,
                                extraction_method="dspy",
                                extraction_source=message
                            )
                        )
                    else:
                        logger.debug(f"🔍 scan_for_name: Extracted name '{first_name}' is invalid (None/Unknown)")
                except Exception as e:
                    logger.debug(f"🔍 scan_for_name: Exception on message {idx}: {type(e).__name__}: {e}")
                    continue

            logger.debug("🔍 scan_for_name: No valid name found in any message")
            return None

        except Exception as e:
            logger.error(f"❌ Retroactive name scan failed: {type(e).__name__}: {e}")
            return None

    def scan_for_vehicle_details(self, history: dspy.History) -> Optional[ValidatedVehicleDetails]:
        """
        Retroactively scan history for vehicle mentions.

        Searches for both brand/model AND plate number, combining them if found separately.
        """
        if not history or not hasattr(history, 'messages'):
            logger.debug("🔍 scan_for_vehicle: No history or no messages attribute")
            return None

        try:
            from config import config

            # PERFORMANCE FIX: Only scan recent messages to prevent timeout
            scan_limit = config.RETROACTIVE_SCAN_LIMIT
            recent_messages = history.messages[-scan_limit:] if len(history.messages) > scan_limit else history.messages

            # Get user messages from recent history only
            user_messages = [
                msg.get('content', '')
                for msg in recent_messages
                if msg.get('role') == 'user'
            ]

            if not user_messages:
                logger.debug("🔍 scan_for_vehicle: No user messages found in recent history")
                return None

            logger.debug(f"🔍 scan_for_vehicle: Scanning {len(user_messages)} recent user messages (limited to last {scan_limit})")
            # Combine recent messages to create context (e.g., "I have Honda City with plate MH12AB1234")
            combined_context = " ".join(user_messages)
            logger.debug(f"🔍 scan_for_vehicle: Combined context: '{combined_context[:100]}...'")

            # Try extraction on combined context
            try:
                logger.debug("🔍 scan_for_vehicle: Calling vehicle extractor...")
                result = self.vehicle_extractor(
                    conversation_history=history,
                    user_message=combined_context
                )

                logger.debug(f"🔍 scan_for_vehicle: Raw extraction result - brand={result.brand}, model={result.model}, plate={result.number_plate}")

                brand = str(result.brand).strip() if result.brand else None
                model = str(result.model).strip() if result.model else None
                plate = str(result.number_plate).strip() if result.number_plate else None

                logger.debug(f"🔍 scan_for_vehicle: After processing - brand='{brand}', model='{model}', plate='{plate}'")

                # Only return if we have at least some data
                if brand or model or plate:
                    if brand and brand.lower() not in ["unknown", "none"]:
                        logger.info(f"✅ scan_for_vehicle: Found brand '{brand}', model '{model}'")
                        return ValidatedVehicleDetails(
                            brand=brand,
                            model=model or "Unknown",
                            number_plate=plate or "Unknown",
                            metadata=ExtractionMetadata(
                                confidence=0.75,
                                extraction_method="dspy",
                                extraction_source=combined_context
                            )
                        )
                    elif plate and plate.lower() not in ["unknown", "none"]:
                        logger.info(f"✅ scan_for_vehicle: Found plate '{plate}' (brand/model missing)")
                        return ValidatedVehicleDetails(
                            brand=brand or "Unknown",
                            model=model or "Unknown",
                            number_plate=plate,
                            metadata=ExtractionMetadata(
                                confidence=0.75,
                                extraction_method="dspy",
                                extraction_source=combined_context
                            )
                        )
                    else:
                        logger.debug("🔍 scan_for_vehicle: Extracted data invalid (brand/model/plate all None/Unknown)")

            except Exception as e:
                logger.debug(f"🔍 scan_for_vehicle: Exception during extraction: {type(e).__name__}: {e}")
                pass

            logger.debug("🔍 scan_for_vehicle: No valid vehicle data found")
            return None

        except Exception as e:
            logger.error(f"❌ Retroactive vehicle scan failed: {type(e).__name__}: {e}")
            return None

    def scan_for_date(self, history: dspy.History) -> Optional[ValidatedDate]:
        """
        Retroactively scan history for date mentions.

        Searches all user messages for date references.
        """
        if not history or not hasattr(history, 'messages'):
            logger.debug("🔍 scan_for_date: No history or no messages attribute")
            return None

        try:
            from config import config

            # PERFORMANCE FIX: Only scan recent messages to prevent timeout
            scan_limit = config.RETROACTIVE_SCAN_LIMIT
            recent_messages = history.messages[-scan_limit:] if len(history.messages) > scan_limit else history.messages

            # Get user messages from recent history only
            user_messages = [
                msg.get('content', '')
                for msg in recent_messages
                if msg.get('role') == 'user'
            ]

            logger.debug(f"🔍 scan_for_date: Scanning {len(user_messages)} recent user messages (limited to last {scan_limit})")
            if not user_messages:
                logger.debug("🔍 scan_for_date: No user messages found in recent history")
                return None

            # Try most recent date-like message first
            for idx, message in enumerate(reversed(user_messages)):
                try:
                    logger.debug(f"🔍 scan_for_date: Attempting extraction from message {idx}: {message[:50]}...")
                    result = self.date_parser(
                        user_message=message,
                        conversation_history=history
                    )

                    logger.debug(f"🔍 scan_for_date: Extraction result - date_str={result.date_str}")

                    date_str = str(result.date_str).strip() if result.date_str else None
                    if date_str and date_str.lower() not in ["none", "unknown"]:
                        logger.info(f"✅ scan_for_date: Successfully extracted '{date_str}'")
                        return ValidatedDate(
                            date_str=date_str,
                            confidence=0.8,
                            metadata=ExtractionMetadata(
                                confidence=0.8,
                                extraction_method="dspy",
                                extraction_source=message
                            )
                        )
                    else:
                        logger.debug(f"🔍 scan_for_date: Extracted date '{date_str}' is invalid (None/Unknown)")
                except Exception as e:
                    logger.debug(f"🔍 scan_for_date: Exception on message {idx}: {type(e).__name__}: {e}")
                    continue

            logger.debug("🔍 scan_for_date: No valid date found in any message")
            return None

        except Exception as e:
            logger.error(f"❌ Retroactive date scan failed: {type(e).__name__}: {e}")
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

        # OPTIMIZATION: Skip retroactive scan if data already extracted in current turn
        # Only scan history if it's truly missing (prevents redundant DSPy calls)
        if "first_name" in missing_fields or "last_name" in missing_fields or "full_name" in missing_fields:
            # Skip scan if we already have name data in current extraction
            if not any(k in extracted_data for k in ["first_name", "last_name", "full_name"]):
                name_data = self.scanner.scan_for_name(history)
                if name_data:
                    updated_data.update({
                        "first_name": name_data.first_name,
                        "last_name": name_data.last_name,
                        "full_name": name_data.full_name
                    })
                    logger.info(f"Retroactively filled name: {name_data.full_name}")
            else:
                logger.debug("🔄 validate_and_complete: Name already in extracted_data, skipping retroactive scan")

        if any(field in missing_fields for field in ["vehicle_brand", "vehicle_model", "vehicle_plate"]):
            # Skip scan if we already have vehicle data in current extraction
            if not any(k in extracted_data for k in ["vehicle_brand", "vehicle_model", "vehicle_plate"]):
                vehicle_data = self.scanner.scan_for_vehicle_details(history)
                logger.debug(f"🔄 validate_and_complete: vehicle_data result = {vehicle_data}")
                if vehicle_data:
                    logger.debug(f"🔄 validate_and_complete: Updating vehicle data: brand={vehicle_data.brand}, model={vehicle_data.model}, plate={vehicle_data.number_plate}")
                    updated_data.update({
                        "vehicle_brand": vehicle_data.brand,
                        "vehicle_model": vehicle_data.model,
                        "vehicle_plate": vehicle_data.number_plate
                    })
                    logger.info(f"Retroactively filled vehicle: {vehicle_data.brand} {vehicle_data.model}")
                    logger.debug(f"🔄 validate_and_complete: After update, updated_data={updated_data}")
                else:
                    logger.debug("🔄 validate_and_complete: vehicle_data is None/falsy, not updating")
            else:
                logger.debug("🔄 validate_and_complete: Vehicle data already in extracted_data, skipping retroactive scan")

        if "appointment_date" in missing_fields:
            # Skip scan if we already have date in current extraction
            if "appointment_date" not in extracted_data:
                date_data = self.scanner.scan_for_date(history)
                if date_data:
                    updated_data["appointment_date"] = date_data.date_str
                    logger.info(f"Retroactively filled date: {date_data.date_str}")
            else:
                logger.debug("🔄 validate_and_complete: appointment_date already in extracted_data, skipping retroactive scan")

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