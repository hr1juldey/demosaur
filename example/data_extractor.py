"""
Service for extracting structured data from unstructured user messages.
"""
from typing import Optional
from datetime import datetime, timedelta
from modules import NameExtractor, VehicleDetailsExtractor, DateParser
from dspy_config import ensure_configured
from models import ValidatedName, ValidatedVehicleDetails, ValidatedDate, ExtractionMetadata
from models import validate_indian_vehicle_number, validate_date_string


class DataExtractionService:
    """Service for extracting structured data from user messages."""

    def __init__(self):
        ensure_configured()
        self.name_extractor = NameExtractor()
        self.vehicle_extractor = VehicleDetailsExtractor()
        self.date_parser = DateParser()

    def extract_name(self, user_message: str) -> Optional[ValidatedName]:
        """Extract customer name from message with validation."""
        try:
            # First, try a simple regex-based extraction for high confidence cases (faster)
            import re
            # Look for common name patterns
            name_match = re.search(r"i['\s]*am\s+(\w+)", user_message, re.IGNORECASE)
            if not name_match:
                name_match = re.search(r"my name is\s+(\w+)", user_message, re.IGNORECASE)
            if not name_match:
                name_match = re.search(r"call me\s+(\w+)", user_message, re.IGNORECASE)
            if not name_match:
                name_match = re.search(r"(\w+)\s+here", user_message, re.IGNORECASE)

            if name_match:
                first_name = name_match.group(1).strip().capitalize()
                full_name = first_name  # For now, just using first name as full name

                # Create extraction metadata
                metadata = ExtractionMetadata(
                    confidence=0.8,  # High confidence for simple regex match
                    extraction_method="rule_based",
                    extraction_source=user_message
                )

                # Create validated name object
                validated_name = ValidatedName(
                    first_name=first_name,
                    last_name="",
                    full_name=full_name,
                    metadata=metadata
                )
                return validated_name

            # If simple extraction didn't work, try LLM extraction (slower but more accurate)
            result = self.name_extractor(user_message=user_message)

            first_name = str(result.first_name).strip()
            last_name = str(result.last_name).strip()
            confidence_str = str(result.confidence).lower()

            if not first_name or first_name.lower() in ["none", "n/a", "unknown"]:
                return None

            # Clean up last name
            if last_name.lower() in ["none", "n/a", "unknown", ""]:
                last_name = ""

            full_name = f"{first_name} {last_name}".strip()

            # Determine confidence based on LLM response
            confidence_map = {"low": 0.3, "medium": 0.6, "high": 0.9}
            confidence = confidence_map.get(confidence_str, 0.6)

            # Create extraction metadata
            metadata = ExtractionMetadata(
                confidence=confidence,
                extraction_method="chain_of_thought",
                extraction_source=user_message
            )

            # Create validated name object
            validated_name = ValidatedName(
                first_name=first_name,
                last_name=last_name,
                full_name=full_name,
                metadata=metadata
            )

            return validated_name
        except Exception:
            return None

    def extract_vehicle_details(self, user_message: str) -> Optional[ValidatedVehicleDetails]:
        """Extract vehicle details from message with validation."""
        try:
            # First, try simple regex-based extraction for high confidence cases (faster)
            import re

            # Look for number plate patterns (Indian format)
            plate_match = re.search(r"[A-Z]{2}[0-9]{1,2}[A-Z]{1,2}[0-9]{1,4}", user_message.upper())
            if plate_match:
                plate_number = plate_match.group()

                # Look for common brand names
                brand_match = None
                for brand in ["Toyota", "Honda", "Ford", "Tata", "Maruti", "Mahindra", "Hyundai", "Kia", "BMW", "Audi", "Mercedes", "Nissan"]:
                    if brand.lower() in user_message.lower():
                        brand_match = brand
                        break

                # Look for model names
                model_match = None
                # This is a simplified model extraction - in real implementation, you'd need more comprehensive logic
                words = user_message.split()
                for i, word in enumerate(words):
                    if word.lower() in ["corolla", "civic", "city", "swift", "alto", "scorpio", "creta", "santro", "dzire", "nexon", "harrier", "xuv"]:
                        model_match = word
                        break

                if plate_number:
                    # Create extraction metadata
                    metadata = ExtractionMetadata(
                        confidence=0.8,  # High confidence for pattern matching
                        extraction_method="rule_based",
                        extraction_source=user_message
                    )

                    # Create validated vehicle object
                    validated_vehicle = ValidatedVehicleDetails(
                        brand=brand_match or "Unknown",
                        model=model_match or "Unknown",
                        number_plate=plate_number,
                        metadata=metadata
                    )
                    return validated_vehicle

            # If simple extraction didn't work, try LLM extraction (slower but more accurate)
            result = self.vehicle_extractor(user_message=user_message)

            brand = str(result.brand).strip()
            model = str(result.model).strip()
            plate = str(result.number_plate).strip()

            # Validate we got meaningful data
            if not brand or brand.lower() in ["none", "n/a", "unknown"]:
                return None

            # Create extraction metadata
            metadata = ExtractionMetadata(
                confidence=0.7,  # Default confidence for LLM extraction
                extraction_method="chain_of_thought",
                extraction_source=user_message
            )

            # Create validated vehicle object
            validated_vehicle = ValidatedVehicleDetails(
                brand=brand,
                model=model,
                number_plate=plate,
                metadata=metadata
            )

            return validated_vehicle
        except Exception:
            return None

    def parse_date(self, user_message: str) -> Optional[ValidatedDate]:
        """Parse date from natural language with validation."""
        try:
            # First, try simple date pattern extraction (faster)
            import re
            from datetime import datetime, date

            # Look for common date formats
            date_patterns = [
                r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',  # DD/MM/YYYY or DD-MM-YYYY
                r'(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})',  # YYYY/MM/DD or YYYY-MM-DD
                r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2})',  # DD/MM/YY or DD-MM-YY
            ]

            for pattern in date_patterns:
                match = re.search(pattern, user_message)
                if match:
                    date_str = match.group(1)
                    # Normalize separators to hyphens
                    normalized_date = date_str.replace('/', '-')

                    # Try to parse the date
                    try:
                        parsed_date = datetime.strptime(normalized_date, "%Y-%m-%d").date()

                        # Create extraction metadata
                        metadata = ExtractionMetadata(
                            confidence=0.9,  # High confidence for explicit date format
                            extraction_method="rule_based",
                            extraction_source=user_message
                        )

                        # Create validated date object
                        validated_date = ValidatedDate(
                            date_str=date_str,
                            parsed_date=parsed_date,
                            confidence=0.9,
                            metadata=metadata
                        )
                        return validated_date
                    except ValueError:
                        continue  # Try next pattern

            # If basic extraction didn't work, try LLM extraction (slower but handles natural language better)
            current_date = datetime.now().strftime("%Y-%m-%d")
            result = self.date_parser(
                user_message=user_message,
                current_date=current_date
            )

            date_str = str(result.parsed_date).strip()
            confidence_str = str(result.confidence).lower()

            # Validate date format
            if not date_str or date_str.lower() in ["none", "unknown"]:
                return None

            # Try to parse to ensure valid date
            try:
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return None

            # Determine confidence
            confidence_map = {"low": 0.3, "medium": 0.6, "high": 0.9}
            confidence = confidence_map.get(confidence_str, 0.6)

            # Create extraction metadata
            metadata = ExtractionMetadata(
                confidence=confidence,
                extraction_method="chain_of_thought",
                extraction_source=user_message
            )

            # Create validated date object
            validated_date = ValidatedDate(
                date_str=date_str,
                parsed_date=parsed_date,
                confidence=confidence,
                metadata=metadata
            )

            return validated_date
        except Exception:
            return None

    def fallback_date_parsing(self, user_message: str) -> Optional[str]:
        """Simple rule-based date parsing as fallback."""
        message_lower = user_message.lower()
        today = datetime.now()

        # Common patterns
        if "today" in message_lower:
            return today.strftime("%Y-%m-%d")
        if "tomorrow" in message_lower:
            return (today + timedelta(days=1)).strftime("%Y-%m-%d")

        # Day of week
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for i, day in enumerate(weekdays):
            if day in message_lower:
                days_ahead = (i - today.weekday()) % 7
                if days_ahead == 0 and "next" in message_lower:
                    days_ahead = 7
                target = today + timedelta(days=days_ahead)
                return target.strftime("%Y-%m-%d")

        return None
