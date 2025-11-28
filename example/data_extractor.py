"""
Lean data extraction using DSPy with graceful fallbacks.
DSPy-first principle: try LLM extraction first, simple regex fallback only if needed.
NOT validation-blocking: returns None gracefully instead of strict Pydantic validation.
"""
import dspy
import re
import logging
from typing import Optional
from datetime import datetime
from modules import NameExtractor, VehicleDetailsExtractor, PhoneExtractor, DateParser
from dspy_config import ensure_configured
from models import ValidatedName, ValidatedVehicleDetails, ValidatedPhone, ValidatedDate, ExtractionMetadata

# Configure logging for diagnostic purposes
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataExtractionService:
    """Simple, DSPy-first extraction with lightweight fallbacks."""

    def __init__(self):
        ensure_configured()
        self.name_extractor = NameExtractor()
        self.vehicle_extractor = VehicleDetailsExtractor()
        self.phone_extractor = PhoneExtractor()
        self.date_parser = DateParser()

    def extract_name(
        self,
        user_message: str,
        conversation_history: dspy.History = None
    ) -> Optional[ValidatedName]:
        """Extract name: DSPy first, regex fallback only if needed."""

        try:
            # Primary: Try DSPy extraction
            history = conversation_history or dspy.History(messages=[])
            result = self.name_extractor(
                conversation_history=history,
                user_message=user_message
            )

            # SANITIZATION: Strip quotes and clean DSPy output
            # Fixes: DSPy sometimes returns '""' (quoted empty string) which fails Pydantic validation
            first_name = str(result.first_name).strip().strip('"\'')
            last_name = str(result.last_name).strip().strip('"\'') if hasattr(result, 'last_name') else ""

            # Only validate essential data, not everything
            if first_name and first_name.lower() not in ["none", "n/a", "unknown"]:
                return ValidatedName(
                    first_name=first_name,
                    last_name=last_name,
                    full_name=f"{first_name} {last_name}".strip(),
                    metadata=ExtractionMetadata(
                        confidence=0.9,
                        extraction_method="dspy",
                        extraction_source=user_message
                    )
                )
        except Exception as e:
            logger.error(f"DSPy name extraction failed: {type(e).__name__}: {e}")
            logger.error(f"History type: {type(conversation_history)}, Has messages: {hasattr(conversation_history, 'messages')}")
            if hasattr(conversation_history, 'messages'):
                logger.error(f"Message count: {len(conversation_history.messages)}")
            pass

        # Fallback: Simple regex only if DSPy fails
        match = re.search(r"i['\s]*am\s+(\w+)|(my name is\s+)(\w+)", user_message, re.IGNORECASE)
        if match:
            name = match.group(1) or match.group(3)
            if name:
                return ValidatedName(
                    first_name=name.capitalize(),
                    last_name="",
                    full_name=name.capitalize(),
                    metadata=ExtractionMetadata(
                        confidence=0.7,
                        extraction_method="rule_based",
                        extraction_source=user_message
                    )
                )

        return None

    def extract_vehicle_details(
        self,
        user_message: str,
        conversation_history: dspy.History = None
    ) -> Optional[ValidatedVehicleDetails]:
        """Extract vehicle: DSPy first, regex fallback only if needed."""

        try:
            # Primary: Try DSPy extraction
            history = conversation_history or dspy.History(messages=[])
            result = self.vehicle_extractor(
                conversation_history=history,
                user_message=user_message
            )

            brand = str(result.brand).strip() if hasattr(result, 'brand') else ""
            model = str(result.model).strip() if hasattr(result, 'model') else ""
            plate = str(result.number_plate).strip() if hasattr(result, 'number_plate') else ""

            if brand and brand.lower() not in ["none", "n/a", "unknown"]:
                return ValidatedVehicleDetails(
                    brand=brand,
                    model=model,
                    number_plate=plate,
                    metadata=ExtractionMetadata(
                        confidence=0.9,
                        extraction_method="dspy",
                        extraction_source=user_message
                    )
                )
        except Exception as e:
            logger.error(f"DSPy vehicle extraction failed: {type(e).__name__}: {e}")
            logger.error(f"History type: {type(conversation_history)}, Has messages: {hasattr(conversation_history, 'messages')}")
            if hasattr(conversation_history, 'messages'):
                logger.error(f"Message count: {len(conversation_history.messages)}")
            pass

        # Fallback: Simple regex only if DSPy fails
        plate_match = re.search(r"[A-Z]{2}[0-9]{1,2}[A-Z]{1,2}[0-9]{1,4}", user_message.upper())
        if plate_match:
            plate = plate_match.group()
            # Try to find brand from common list
            brands = ["Honda", "Toyota", "Tata", "Maruti", "Mahindra", "Ford", "Hyundai"]
            brand = next((b for b in brands if b.lower() in user_message.lower()), "Unknown")
            return ValidatedVehicleDetails(
                brand=brand,
                model="Unknown",
                number_plate=plate,
                metadata=ExtractionMetadata(
                    confidence=0.8,
                    extraction_method="rule_based",
                    extraction_source=user_message
                )
            )

        return None

    def extract_phone(
        self,
        user_message: str,
        conversation_history: dspy.History = None
    ) -> Optional[ValidatedPhone]:
        """Extract phone number: DSPy first, regex fallback only if needed."""

        try:
            # Primary: Try DSPy extraction
            history = conversation_history or dspy.History(messages=[])
            result = self.phone_extractor(
                conversation_history=history,
                user_message=user_message
            )

            phone_number = str(result.phone_number).strip() if hasattr(result, 'phone_number') else ""

            if phone_number and phone_number.lower() not in ["none", "n/a", "unknown"]:
                return ValidatedPhone(
                    phone_number=phone_number,
                    confidence=0.9,
                    metadata=ExtractionMetadata(
                        confidence=0.9,
                        extraction_method="dspy",
                        extraction_source=user_message
                    )
                )
        except Exception as e:
            logger.error(f"DSPy phone extraction failed: {type(e).__name__}: {e}")
            pass

        # Fallback: Simple regex for 10-digit Indian phone numbers
        phone_match = re.search(r'\b([6-9]\d{9})\b', user_message)
        if phone_match:
            phone_number = phone_match.group(1)
            return ValidatedPhone(
                phone_number=phone_number,
                confidence=0.8,
                metadata=ExtractionMetadata(
                    confidence=0.8,
                    extraction_method="rule_based",
                    extraction_source=user_message
                )
            )

        return None

    def parse_date(
        self,
        user_message: str,
        conversation_history: dspy.History = None
    ) -> Optional[ValidatedDate]:
        """Parse date: DSPy first, regex fallback only if needed."""

        try:
            # Primary: Try DSPy extraction
            history = conversation_history or dspy.History(messages=[])
            current_date = datetime.now().strftime("%Y-%m-%d")
            result = self.date_parser(
                conversation_history=history,
                user_message=user_message,
                current_date=current_date
            )

            date_str = str(result.parsed_date).strip() if hasattr(result, 'parsed_date') else ""

            if date_str and date_str.lower() not in ["none", "unknown"]:
                try:
                    parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    return ValidatedDate(
                        date_str=date_str,
                        parsed_date=parsed_date,
                        confidence=0.9,
                        metadata=ExtractionMetadata(
                            confidence=0.9,
                            extraction_method="dspy",
                            extraction_source=user_message
                        )
                    )
                except ValueError:
                    pass
        except Exception as e:
            logger.error(f"DSPy date parsing failed: {type(e).__name__}: {e}")
            logger.error(f"History type: {type(conversation_history)}, Has messages: {hasattr(conversation_history, 'messages')}")
            if hasattr(conversation_history, 'messages'):
                logger.error(f"Message count: {len(conversation_history.messages)}")
            pass

        # Fallback: Simple regex patterns only if DSPy fails
        date_patterns = [
            r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',  # YYYY-MM-DD
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})',  # DD-MM-YYYY
        ]

        for pattern in date_patterns:
            match = re.search(pattern, user_message)
            if match:
                date_str = match.group(1)
                try:
                    # Normalize separators
                    normalized = date_str.replace('/', '-')
                    parsed_date = datetime.strptime(normalized, "%Y-%m-%d").date()
                    return ValidatedDate(
                        date_str=normalized,
                        parsed_date=parsed_date,
                        confidence=0.8,
                        metadata=ExtractionMetadata(
                            confidence=0.8,
                            extraction_method="rule_based",
                            extraction_source=user_message
                        )
                    )
                except ValueError:
                    continue

        return None