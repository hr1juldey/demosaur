"""
Service for extracting structured data from unstructured user messages.
"""
from typing import Optional
from datetime import datetime, timedelta
from functools import lru_cache
import hashlib
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

        # Add cache for recent extraction results
        self._name_cache = {}
        self._vehicle_cache = {}
        self._date_cache = {}
        # Cache timeout in seconds (30 minutes)
        self._cache_timeout = 30 * 60

    def _get_cache_key(self, user_message: str) -> str:
        """Generate a cache key for the user message."""
        return hashlib.md5(user_message.encode()).hexdigest()

    def _is_cache_valid(self, cached_time: float) -> bool:
        """Check if cached result is still valid."""
        return (datetime.now().timestamp() - cached_time) < self._cache_timeout

    def extract_name(self, user_message: str) -> Optional[ValidatedName]:
        """Extract customer name from message with validation."""
        # Check cache first
        cache_key = self._get_cache_key(user_message)
        if cache_key in self._name_cache:
            cached_result, timestamp = self._name_cache[cache_key]
            if self._is_cache_valid(timestamp):
                return cached_result

        try:
            # First, try DSPy extraction (primary method)
            result = self.name_extractor(user_message=user_message)

            first_name = str(result.first_name).strip()
            last_name = str(result.last_name).strip()
            confidence_str = str(result.confidence).lower()

            # Check if DSPy extraction was successful
            if first_name and first_name.lower() not in ["none", "n/a", "unknown"]:
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
                    extraction_source=user_message,
                    processing_time_ms=0.0
                )

                # Create validated name object
                try:
                    validated_name = ValidatedName(
                        first_name=first_name,
                        last_name=last_name,
                        full_name=full_name,
                        metadata=metadata
                    )
                    # Cache the result
                    self._name_cache[cache_key] = (validated_name, datetime.now().timestamp())
                    return validated_name
                except Exception:
                    # If validation fails, try regex fallback
                    pass

            # If DSPy extraction failed or validation blocked it, try regex-based extraction as fallback
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
                    extraction_source=user_message,
                    processing_time_ms=0.0
                )

                # Create validated name object with normalized format
                try:
                    validated_name = ValidatedName(
                        first_name=first_name,
                        last_name="",
                        full_name=first_name,  # Use first name as full name
                        metadata=metadata
                    )
                    # Cache the result
                    self._name_cache[cache_key] = (validated_name, datetime.now().timestamp())
                    return validated_name
                except Exception:
                    # If both DSPy and regex methods fail with validation, return None
                    pass

        except Exception:
            # If DSPy extraction fails completely, try regex fallback
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
                    extraction_source=user_message,
                    processing_time_ms=0.0
                )

                # Create validated name object with normalized format
                try:
                    validated_name = ValidatedName(
                        first_name=first_name,
                        last_name="",
                        full_name=first_name,  # Use first name as full name
                        metadata=metadata
                    )
                    # Cache the result
                    self._name_cache[cache_key] = (validated_name, datetime.now().timestamp())
                    return validated_name
                except Exception:
                    pass

        return None

    def extract_vehicle_details(self, user_message: str) -> Optional[ValidatedVehicleDetails]:
        """Extract vehicle details from message with validation."""
        # Check cache first
        cache_key = self._get_cache_key(user_message)
        if cache_key in self._vehicle_cache:
            cached_result, timestamp = self._vehicle_cache[cache_key]
            if self._is_cache_valid(timestamp):
                return cached_result

        try:
            # First, try DSPy extraction (primary method)
            result = self.vehicle_extractor(user_message=user_message)

            brand = str(result.brand).strip()
            model = str(result.model).strip()
            plate = str(result.number_plate).strip()

            # Check if DSPy extraction was successful
            if brand and brand.lower() not in ["none", "n/a", "unknown"]:
                # Create extraction metadata
                metadata = ExtractionMetadata(
                    confidence=0.7,  # Default confidence for LLM extraction
                    extraction_method="chain_of_thought",
                    extraction_source=user_message,
                    processing_time_ms=0.0
                )

                # Create validated vehicle object
                try:
                    validated_vehicle = ValidatedVehicleDetails(
                        brand=brand,
                        model=model,
                        number_plate=plate,
                        metadata=metadata
                    )
                    # Cache the result
                    self._vehicle_cache[cache_key] = (validated_vehicle, datetime.now().timestamp())
                    return validated_vehicle
                except Exception:
                    # If validation fails, try regex fallback
                    pass

            # If DSPy extraction failed or validation blocked it, try regex-based extraction as fallback
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
                        extraction_source=user_message,
                        processing_time_ms=0.0
                    )

                    # Create validated vehicle object
                    try:
                        validated_vehicle = ValidatedVehicleDetails(
                            brand=brand_match or "Unknown",
                            model=model_match or "Unknown",
                            number_plate=plate_number,
                            metadata=metadata
                        )
                        # Cache the result
                        self._vehicle_cache[cache_key] = (validated_vehicle, datetime.now().timestamp())
                        return validated_vehicle
                    except Exception:
                        # If both DSPy and regex methods fail with validation, continue to general exception
                        pass

        except Exception:
            # If DSPy extraction fails completely, try regex fallback
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
                        extraction_source=user_message,
                        processing_time_ms=0.0
                    )

                    # Create validated vehicle object
                    try:
                        validated_vehicle = ValidatedVehicleDetails(
                            brand=brand_match or "Unknown",
                            model=model_match or "Unknown",
                            number_plate=plate_number,
                            metadata=metadata
                        )
                        # Cache the result
                        self._vehicle_cache[cache_key] = (validated_vehicle, datetime.now().timestamp())
                        return validated_vehicle
                    except Exception:
                        # If both DSPy and regex methods fail with validation, return None
                        pass

        return None

    def parse_date(self, user_message: str) -> Optional[ValidatedDate]:
        """Parse date from natural language with validation."""
        # Check cache first
        cache_key = self._get_cache_key(user_message)
        if cache_key in self._date_cache:
            cached_result, timestamp = self._date_cache[cache_key]
            if self._is_cache_valid(timestamp):
                return cached_result

        try:
            # First, try DSPy extraction (primary method)
            current_date = datetime.now().strftime("%Y-%m-%d")
            result = self.date_parser(
                user_message=user_message,
                current_date=current_date
            )

            date_str = str(result.parsed_date).strip()
            confidence_str = str(result.confidence).lower()

            # Check if DSPy extraction was successful
            if date_str and date_str.lower() not in ["none", "unknown"]:
                # Try to parse to ensure valid date
                try:
                    parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()

                    # Determine confidence
                    confidence_map = {"low": 0.3, "medium": 0.6, "high": 0.9}
                    confidence = confidence_map.get(confidence_str, 0.6)

                    # Create extraction metadata
                    metadata = ExtractionMetadata(
                        confidence=confidence,
                        extraction_method="chain_of_thought",
                        extraction_source=user_message,
                        processing_time_ms=0.0
                    )

                    # Create validated date object
                    try:
                        validated_date = ValidatedDate(
                            date_str=date_str,
                            parsed_date=parsed_date,
                            confidence=confidence,
                            metadata=metadata
                        )
                        # Cache the result
                        self._date_cache[cache_key] = (validated_date, datetime.now().timestamp())
                        return validated_date
                    except Exception:
                        # If validation fails, try regex fallback
                        pass
                except ValueError:
                    # If date parsing fails, try regex fallback
                    pass

            # If DSPy extraction failed or validation blocked it, try simple date pattern extraction as fallback
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
                            extraction_source=user_message,
                            processing_time_ms=0.0
                        )

                        # Create validated date object
                        try:
                            validated_date = ValidatedDate(
                                date_str=date_str,
                                parsed_date=parsed_date,
                                confidence=0.9,
                                metadata=metadata
                            )
                            # Cache the result
                            self._date_cache[cache_key] = (validated_date, datetime.now().timestamp())
                            return validated_date
                        except Exception:
                            # If both DSPy and regex methods fail with validation, continue to general exception
                            continue
                    except ValueError:
                        continue  # Try next pattern

        except Exception:
            # If DSPy extraction fails completely, try regex fallback
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
                            extraction_source=user_message,
                            processing_time_ms=0.0
                        )

                        # Create validated date object
                        try:
                            validated_date = ValidatedDate(
                                date_str=date_str,
                                parsed_date=parsed_date,
                                confidence=0.9,
                                metadata=metadata
                            )
                            # Cache the result
                            self._date_cache[cache_key] = (validated_date, datetime.now().timestamp())
                            return validated_date
                        except Exception:
                            # If both DSPy and regex methods fail with validation, return None
                            continue
                    except ValueError:
                        continue  # Try next pattern

        return None

    def normalize_name_result(self, first_name: str, last_name: str, full_name: str) -> tuple:
        """Normalize LLM name output for validation compatibility."""
        # Properly capitalize names
        first_name = ' '.join(word.capitalize() for word in first_name.split())
        last_name = ' '.join(word.capitalize() for word in last_name.split()) if last_name else ""
        full_name = ' '.join(word.capitalize() for word in full_name.split()) if full_name else ""

        # Ensure first name and full name consistency
        if not full_name and first_name:
            full_name = first_name
        elif full_name and first_name and not full_name.startswith(first_name):
            # If full name doesn't start with first name, try to adjust
            parts = full_name.split()
            if parts and not any(part.lower() == first_name.lower() for part in parts):
                # Add first name to full name if missing
                full_name = f"{first_name} {full_name}".strip()

        return first_name, last_name, full_name

    def normalize_vehicle_result(self, brand: str, model: str, number_plate: str) -> tuple:
        """Normalize LLM vehicle output for validation compatibility."""
        # Normalize number plate format
        number_plate = re.sub(r'\s+', ' ', number_plate.strip().upper())

        # Standardize brand name format
        if len(brand) < 1:
            brand = "Unknown"

        # Validate model name format
        if len(model) < 1:
            model = "Unknown"

        return brand, model, number_plate

    def normalize_date_result(self, date_str: str, parsed_date, confidence: float) -> tuple:
        """Normalize LLM date output for validation compatibility."""
        # Ensure proper date format
        if not date_str:
            date_str = parsed_date.strftime("%Y-%m-%d") if parsed_date else ""

        # Validate date reasonableness
        if parsed_date is None:
            try:
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                parsed_date = datetime.now().date()  # fallback to today if parsing fails

        # Standardize confidence values
        if confidence is None:
            confidence = 0.6

        return date_str, parsed_date, confidence

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
