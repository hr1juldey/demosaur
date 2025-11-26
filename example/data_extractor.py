"""
Service for extracting structured data from unstructured user messages.
"""
import dspy
import re
from typing import Optional
from datetime import datetime, timedelta
from functools import lru_cache
import hashlib
import threading
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

        # Add locks for thread safety when accessing shared cache dictionaries
        self._name_cache_lock = threading.Lock()
        self._vehicle_cache_lock = threading.Lock()
        self._date_cache_lock = threading.Lock()

    def _get_cache_key(self, user_message: str, context: str = "") -> str:
        """Generate a cache key for the user message."""
        combined = user_message + context
        return hashlib.md5(combined.encode()).hexdigest()

    def _is_cache_valid(self, cached_time: float) -> bool:
        """Check if cached result is still valid."""
        return (datetime.now().timestamp() - cached_time) < self._cache_timeout

    def extract_name(self, user_message: str, conversation_history: dspy.History = None) -> Optional[ValidatedName]:
        """Extract customer name from message with validation."""
        # Preprocess the input to handle very long or very short text
        processed_message = self._preprocess_input(user_message)

        # Check cache first
        cache_key = self._get_cache_key(processed_message, "name")
        with self._name_cache_lock:
            if cache_key in self._name_cache:
                cached_result, timestamp = self._name_cache[cache_key]
                if self._is_cache_valid(timestamp):
                    return cached_result

        try:
            # First, try DSPy extraction with history context (primary method)
            # Create history object if not provided
            history = dspy.History(messages=[]) if conversation_history is None else conversation_history
            result = self.name_extractor(
                conversation_history=history,
                user_message=processed_message
            )

            # Normalize LLM output to handle unexpected formats
            first_name, last_name, confidence_str = self._normalize_llm_name_output(result)

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
                    extraction_source=processed_message,
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
                    with self._name_cache_lock:
                        self._name_cache[cache_key] = (validated_name, datetime.now().timestamp())
                    return validated_name
                except Exception:
                    # If validation fails, try regex fallback
                    pass

            # If DSPy extraction failed or validation blocked it, try regex-based extraction as fallback
            import re
            # Look for common name patterns
            name_match = re.search(r"i['\s]*am\s+(\w+)", processed_message, re.IGNORECASE)
            if not name_match:
                name_match = re.search(r"my name is\s+(\w+)", processed_message, re.IGNORECASE)
            if not name_match:
                name_match = re.search(r"call me\s+(\w+)", processed_message, re.IGNORECASE)
            if not name_match:
                name_match = re.search(r"(\w+)\s+here", processed_message, re.IGNORECASE)

            if name_match:
                first_name = name_match.group(1).strip().capitalize()
                full_name = first_name  # For now, just using first name as full name

                # Create extraction metadata
                metadata = ExtractionMetadata(
                    confidence=0.8,  # High confidence for simple regex match
                    extraction_method="rule_based",
                    extraction_source=processed_message,
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
                    with self._name_cache_lock:
                        self._name_cache[cache_key] = (validated_name, datetime.now().timestamp())
                    return validated_name
                except Exception:
                    # If both DSPy and regex methods fail with validation, return None
                    pass

        except Exception:
            # If DSPy extraction fails completely, try regex fallback
            import re
            # Look for common name patterns
            name_match = re.search(r"i['\s]*am\s+(\w+)", processed_message, re.IGNORECASE)
            if not name_match:
                name_match = re.search(r"my name is\s+(\w+)", processed_message, re.IGNORECASE)
            if not name_match:
                name_match = re.search(r"call me\s+(\w+)", processed_message, re.IGNORECASE)
            if not name_match:
                name_match = re.search(r"(\w+)\s+here", processed_message, re.IGNORECASE)

            if name_match:
                first_name = name_match.group(1).strip().capitalize()
                full_name = first_name  # For now, just using first name as full name

                # Create extraction metadata
                metadata = ExtractionMetadata(
                    confidence=0.8,  # High confidence for simple regex match
                    extraction_method="rule_based",
                    extraction_source=processed_message,
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
                    with self._name_cache_lock:
                        self._name_cache[cache_key] = (validated_name, datetime.now().timestamp())
                    return validated_name
                except Exception:
                    pass

        return None

    def _normalize_llm_name_output(self, result):
        """Handle unexpected LLM output formats for names including partial results."""
        try:
            # Handle LLM outputs with unexpected structure (nested objects, etc.)
            if hasattr(result, 'first_name'):
                first_name = str(result.first_name).strip()
            else:
                first_name = str(getattr(result, 'first_name', '')).strip()

            if hasattr(result, 'last_name'):
                last_name = str(result.last_name).strip()
            else:
                last_name = str(getattr(result, 'last_name', '')).strip()

            if hasattr(result, 'confidence'):
                confidence_str = str(result.confidence).lower()
            else:
                confidence_str = str(getattr(result, 'confidence', 'medium')).lower()

            # Handle partial results - if first_name is empty but last_name exists, swap them
            if not first_name and last_name:
                first_name = last_name
                last_name = ""

            # Sanitize unexpected formats
            # If first_name contains multiple words and last_name is empty, try to split
            if ' ' in first_name and not last_name:
                parts = first_name.split(' ', 1)
                if len(parts) > 1:
                    first_name, last_name = parts[0], parts[1]

            # Handle cases where first_name might contain the full name
            if ' ' in first_name and not last_name:
                name_parts = first_name.split()
                if len(name_parts) > 2:  # Multiple names, take first as first_name, rest as last_name
                    first_name = name_parts[0]
                    last_name = ' '.join(name_parts[1:])
                elif len(name_parts) == 2:  # Two names, assume first and last
                    first_name, last_name = name_parts[0], name_parts[1]

            # If result is in JSON string format, parse it
            import json
            if first_name.startswith('{') and first_name.endswith('}'):
                try:
                    parsed = json.loads(first_name)
                    first_name = str(parsed.get('first_name', ''))
                    last_name = str(parsed.get('last_name', ''))
                    confidence_str = str(parsed.get('confidence', 'medium'))
                except json.JSONDecodeError:
                    pass  # Not a JSON string, continue with original values
            elif isinstance(result, str) and result.startswith('{') and result.endswith('}'):
                # Handle case where entire result is a JSON string
                try:
                    parsed = json.loads(result)
                    first_name = str(parsed.get('first_name', ''))
                    last_name = str(parsed.get('last_name', ''))
                    confidence_str = str(parsed.get('confidence', 'medium'))
                except json.JSONDecodeError:
                    pass  # Not a JSON string, continue with original values

            # Sanitize special characters and normalize format
            import re
            # Keep only valid name characters
            first_name = re.sub(r'[^\w\s\'-]', '', first_name).strip()
            last_name = re.sub(r'[^\w\s\'-]', '', last_name).strip()

            # Handle empty values by providing reasonable defaults
            if not first_name:
                first_name = ""
            if not last_name:
                last_name = ""

            return first_name, last_name, confidence_str

        except Exception:
            # If normalization fails, return safe defaults
            return "", "", "low"

    def extract_vehicle_details(self, user_message: str, conversation_history: dspy.History = None) -> Optional[ValidatedVehicleDetails]:
        """Extract vehicle details from message with validation."""
        # Preprocess the input to handle very long or very short text
        processed_message = self._preprocess_input(user_message)

        # Check cache first
        cache_key = self._get_cache_key(processed_message, "vehicle")
        with self._vehicle_cache_lock:
            if cache_key in self._vehicle_cache:
                cached_result, timestamp = self._vehicle_cache[cache_key]
                if self._is_cache_valid(timestamp):
                    return cached_result

        try:
            # First, try DSPy extraction with history context (primary method)
            # Create history object if not provided
            history = dspy.History(messages=[]) if conversation_history is None else conversation_history
            result = self.vehicle_extractor(
                conversation_history=history,
                user_message=processed_message
            )

            # Normalize LLM output to handle unexpected formats
            brand, model, plate = self._normalize_llm_vehicle_output(result)

            # Check if DSPy extraction was successful
            if brand and brand.lower() not in ["none", "n/a", "unknown"]:
                # Create extraction metadata
                metadata = ExtractionMetadata(
                    confidence=0.7,  # Default confidence for LLM extraction
                    extraction_method="chain_of_thought",
                    extraction_source=processed_message,
                    processing_time_ms=0.0
                )

                # Validate vehicle number plate using the imported function
                is_valid_plate = validate_indian_vehicle_number(plate) if plate else True

                if is_valid_plate:
                    # Create validated vehicle object
                    try:
                        validated_vehicle = ValidatedVehicleDetails(
                            brand=brand,
                            model=model,
                            number_plate=plate,
                            metadata=metadata
                        )
                        # Cache the result
                        with self._vehicle_cache_lock:
                            self._vehicle_cache[cache_key] = (validated_vehicle, datetime.now().timestamp())
                        return validated_vehicle
                    except Exception:
                        # If validation fails, try regex fallback
                        pass
                else:
                    # Vehicle plate number is invalid, try regex fallback
                    pass

            # If DSPy extraction failed or validation blocked it, try regex-based extraction as fallback
            import re

            # Look for number plate patterns (Indian format)
            plate_match = re.search(r"[A-Z]{2}[0-9]{1,2}[A-Z]{1,2}[0-9]{1,4}", processed_message.upper())
            if plate_match:
                plate_number = plate_match.group()

                # Look for common brand names
                brand_match = None
                for brand in ["Toyota", "Honda", "Ford", "Tata", "Maruti", "Mahindra", "Hyundai", "Kia", "BMW", "Audi", "Mercedes", "Nissan"]:
                    if brand.lower() in processed_message.lower():
                        brand_match = brand
                        break

                # Look for model names
                model_match = None
                # This is a simplified model extraction - in real implementation, you'd need more comprehensive logic
                words = processed_message.split()
                for i, word in enumerate(words):
                    if word.lower() in ["corolla", "civic", "city", "swift", "alto", "scorpio", "creta", "santro", "dzire", "nexon", "harrier", "xuv"]:
                        model_match = word
                        break

                if plate_number:
                    # Create extraction metadata
                    metadata = ExtractionMetadata(
                        confidence=0.8,  # High confidence for pattern matching
                        extraction_method="rule_based",
                        extraction_source=processed_message,
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
                        with self._vehicle_cache_lock:
                            self._vehicle_cache[cache_key] = (validated_vehicle, datetime.now().timestamp())
                        return validated_vehicle
                    except Exception:
                        # If both DSPy and regex methods fail with validation, continue to general exception
                        pass

        except Exception:
            # If DSPy extraction fails completely, try regex fallback
            import re

            # Look for number plate patterns (Indian format)
            plate_match = re.search(r"[A-Z]{2}[0-9]{1,2}[A-Z]{1,2}[0-9]{1,4}", processed_message.upper())
            if plate_match:
                plate_number = plate_match.group()

                # Look for common brand names
                brand_match = None
                for brand in ["Toyota", "Honda", "Ford", "Tata", "Maruti", "Mahindra", "Hyundai", "Kia", "BMW", "Audi", "Mercedes", "Nissan"]:
                    if brand.lower() in processed_message.lower():
                        brand_match = brand
                        break

                # Look for model names
                model_match = None
                # This is a simplified model extraction - in real implementation, you'd need more comprehensive logic
                words = processed_message.split()
                for i, word in enumerate(words):
                    if word.lower() in ["corolla", "civic", "city", "swift", "alto", "scorpio", "creta", "santro", "dzire", "nexon", "harrier", "xuv"]:
                        model_match = word
                        break

                if plate_number:
                    # Create extraction metadata
                    metadata = ExtractionMetadata(
                        confidence=0.8,  # High confidence for pattern matching
                        extraction_method="rule_based",
                        extraction_source=processed_message,
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
                        with self._vehicle_cache_lock:
                            self._vehicle_cache[cache_key] = (validated_vehicle, datetime.now().timestamp())
                        return validated_vehicle
                    except Exception:
                        # If both DSPy and regex methods fail with validation, return None
                        pass

        return None

    def _normalize_llm_vehicle_output(self, result):
        """Handle unexpected LLM output formats for vehicles including partial results."""
        try:
            # Handle LLM outputs with unexpected structure (nested objects, etc.)
            if hasattr(result, 'brand'):
                brand = str(result.brand).strip()
            else:
                brand = str(getattr(result, 'brand', '')).strip()

            if hasattr(result, 'model'):
                model = str(result.model).strip()
            else:
                model = str(getattr(result, 'model', '')).strip()

            if hasattr(result, 'number_plate'):
                plate = str(result.number_plate).strip()
            else:
                plate = str(getattr(result, 'number_plate', '')).strip()

            # Handle partial results
            # If no brand but model exists, try to extract brand from model if possible
            if not brand and model:
                # Some models contain brand information
                words = model.split()
                for word in words:
                    if word.lower() in ["honda", "toyota", "ford", "tata", "maruti", "mahindra", "hyundai", "kia", "bmw", "audi", "mercedes", "nissan"]:
                        brand = word
                        # Remove brand from model
                        model = ' '.join([w for w in words if w.lower() != word.lower()])
                        break

            # If only plate is provided, try to extract brand/model from user message context
            if not brand and not model and plate:
                # In this case, we can't extract from plate alone, so we leave as is
                pass

            # Sanitize unexpected formats
            # If brand contains multiple fields, try to parse them
            if ' ' in brand and not model and not plate:
                # Could be "brand model" or "brand plate" format
                parts = brand.split(' ', 2)
                if len(parts) >= 2:
                    brand, model = parts[0], ' '.join(parts[1:])
            elif not brand and not plate and ' ' in model:
                # Model might contain both brand and model
                parts = model.split(' ', 1)
                if len(parts) == 2:
                    brand, model = parts[0], parts[1]

            # If result is in JSON string format, parse it
            import json
            if brand.startswith('{') and brand.endswith('}'):
                try:
                    parsed = json.loads(brand)
                    brand = str(parsed.get('brand', ''))
                    model = str(parsed.get('model', ''))
                    plate = str(parsed.get('number_plate', ''))
                except json.JSONDecodeError:
                    pass  # Not a JSON string, continue with original values
            elif isinstance(result, str) and result.startswith('{') and result.endswith('}'):
                # Handle case where entire result is a JSON string
                try:
                    parsed = json.loads(result)
                    brand = str(parsed.get('brand', ''))
                    model = str(parsed.get('model', ''))
                    plate = str(parsed.get('number_plate', ''))
                except json.JSONDecodeError:
                    pass  # Not a JSON string, continue with original values

            # Sanitize special characters and normalize format
            import re
            # Keep only valid characters for each field
            brand = re.sub(r'[^\w\s\'-]', '', brand).strip()
            model = re.sub(r'[^\w\s\'-]', '', model).strip()
            plate = re.sub(r'[^A-Z0-9\s-]', '', plate.upper()).strip()

            # Handle empty values by providing reasonable defaults
            if not brand:
                brand = ""
            if not model:
                model = ""
            if not plate:
                plate = ""

            return brand, model, plate

        except Exception:
            # If normalization fails, return safe defaults
            return "", "", ""

    def parse_date(self, user_message: str, conversation_history: dspy.History = None) -> Optional[ValidatedDate]:
        """Parse date from natural language with validation."""
        # Preprocess the input to handle very long or very short text
        processed_message = self._preprocess_input(user_message)

        # Check cache first
        cache_key = self._get_cache_key(processed_message, "date")
        with self._date_cache_lock:
            if cache_key in self._date_cache:
                cached_result, timestamp = self._date_cache[cache_key]
                if self._is_cache_valid(timestamp):
                    return cached_result

        try:
            # First, try DSPy extraction with history context (primary method)
            # Create history object if not provided
            history = dspy.History(messages=[]) if conversation_history is None else conversation_history
            current_date = datetime.now().strftime("%Y-%m-%d")
            result = self.date_parser(
                conversation_history=history,
                user_message=processed_message,
                current_date=current_date
            )

            # Normalize LLM output to handle unexpected formats
            date_str, confidence_str = self._normalize_llm_date_output(result)

            # Check if DSPy extraction was successful
            if date_str and date_str.lower() not in ["none", "unknown"]:
                # Try to parse to ensure valid date
                try:
                    parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()

                    # Determine confidence if not already determined
                    if confidence_str and confidence_str not in ["low", "medium", "high"]:
                        confidence_map = {"low": 0.3, "medium": 0.6, "high": 0.9}
                        confidence = confidence_map.get(confidence_str.lower(), 0.6)
                    else:
                        confidence = 0.6

                    # Validate date string using the imported function
                    is_valid_date = validate_date_string(date_str) if date_str else True

                    if is_valid_date:
                        # Create extraction metadata
                        metadata = ExtractionMetadata(
                            confidence=confidence,
                            extraction_method="chain_of_thought",
                            extraction_source=processed_message,
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
                            with self._date_cache_lock:
                                self._date_cache[cache_key] = (validated_date, datetime.now().timestamp())
                            return validated_date
                        except Exception:
                            # If validation fails, try regex fallback
                            pass
                    else:
                        # Date string is invalid, continue to regex fallback
                        pass
                except ValueError:
                    # If date parsing fails, try regex fallback
                    pass

            # If DSPy extraction failed or validation blocked it, try simple date pattern extraction as fallback
           

            # Look for common date formats
            date_patterns = [
                r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',  # DD/MM/YYYY or DD-MM-YYYY
                r'(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})',  # YYYY/MM/DD or YYYY-MM-DD
                r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2})',  # DD/MM/YY or DD-MM-YY
            ]

            for pattern in date_patterns:
                match = re.search(pattern, processed_message)
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
                            extraction_source=processed_message,
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
                            with self._date_cache_lock:
                                self._date_cache[cache_key] = (validated_date, datetime.now().timestamp())
                            return validated_date
                        except Exception:
                            # If both DSPy and regex methods fail with validation, continue to general exception
                            continue
                    except ValueError:
                        continue  # Try next pattern

        except Exception:
            # If DSPy extraction fails completely, try regex fallback
          
            

            # Look for common date formats
            date_patterns = [
                r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',  # DD/MM/YYYY or DD-MM-YYYY
                r'(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})',  # YYYY/MM/DD or YYYY-MM-DD
                r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2})',  # DD/MM/YY or DD-MM-YY
            ]

            for pattern in date_patterns:
                match = re.search(pattern, processed_message)
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
                            extraction_source=processed_message,
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
                            with self._date_cache_lock:
                                self._date_cache[cache_key] = (validated_date, datetime.now().timestamp())
                            return validated_date
                        except Exception:
                            # If both DSPy and regex methods fail with validation, return None
                            continue
                    except ValueError:
                        continue  # Try next pattern

        return None

    def _normalize_llm_date_output(self, result):
        """Handle unexpected LLM output formats for dates including partial results."""
        try:
            # Handle LLM outputs with unexpected structure (nested objects, etc.)
            if hasattr(result, 'parsed_date'):
                date_str = str(result.parsed_date).strip()
            else:
                date_str = str(getattr(result, 'parsed_date', '')).strip()

            if hasattr(result, 'confidence'):
                confidence_str = str(result.confidence).lower()
            else:
                confidence_str = str(getattr(result, 'confidence', 'medium')).lower()

            # Handle partial results
            # If date_str is empty, try to extract from user message context or use reasonable defaults
            if not date_str:
                # This would be handled at a higher level with the fallback methods
                pass

            # Sanitize unexpected formats
            # If result is in JSON string format, parse it
            import json
            if date_str.startswith('{') and date_str.endswith('}'):
                try:
                    parsed = json.loads(date_str)
                    date_str = str(parsed.get('parsed_date', ''))
                    confidence_str = str(parsed.get('confidence', 'medium'))
                except json.JSONDecodeError:
                    pass  # Not a JSON string, continue with original values
            elif isinstance(result, str) and result.startswith('{') and result.endswith('}'):
                # Handle case where entire result is a JSON string
                try:
                    parsed = json.loads(result)
                    date_str = str(parsed.get('parsed_date', ''))
                    confidence_str = str(parsed.get('confidence', 'medium'))
                except json.JSONDecodeError:
                    pass  # Not a JSON string, continue with original values

            # Sanitize special characters and normalize format
            import re
            # Allow only valid date characters (numbers, separators, spaces)
            date_str = re.sub(r'[^0-9/\-\.]', ' ', date_str).strip()

            # Handle common LLM response formats where the date is embedded in text
            # e.g. "The date is 2023-12-25" or "2023-12-25 please"
            date_pattern = r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{2})\b'
            match = re.search(date_pattern, date_str)
            if match:
                date_str = match.group(1)

            # Handle cases where LLM provides relative dates like "tomorrow", "next week"
            if date_str.lower() in ['today', 'now']:
                date_str = datetime.now().strftime("%Y-%m-%d")
            elif date_str.lower() == 'tomorrow':
                date_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            elif date_str.lower() == 'yesterday':
                date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

            # Handle empty values by providing reasonable defaults
            if not date_str:
                date_str = ""

            return date_str, confidence_str

        except Exception:
            # If normalization fails, return safe defaults
            return "", "low"

    def _preprocess_input(self, text: str) -> str:
        """Preprocess text input to handle edge cases with very long or very short text, special chars and Unicode."""
        # Handle very short text (1-3 characters) - might be missing information but still processable
        if len(text.strip()) < 4:
            # For very short text, we just sanitize it minimally
            return self._sanitize_special_characters(text.strip())

        # Handle very long text by truncating if necessary (e.g., over 1000 characters)
        # Truncate to a reasonable length while preserving the relevant information
        if len(text) > 500:
            # Try to preserve the beginning and end of the text
            # or truncate from the middle if it's too long
            if len(text) > 1000:
                # For very long text, we'll preserve first and last 400 characters with an indicator
                first_part = text[:400]
                last_part = text[-400:]
                truncated_text = first_part + " ... [TEXT TRUNCATED FOR PROCESSING] ... " + last_part
                text = truncated_text
            else:
                # For moderately long text, just truncate to 500 chars
                text = text[:500]

        # Sanitize the text by handling special characters and Unicode appropriately
        sanitized_text = self._sanitize_special_characters(text)

        # Clean up multiple consecutive spaces that might result from character removal
        import re
        cleaned_text = re.sub(r'\s+', ' ', sanitized_text).strip()

        return cleaned_text

    def _sanitize_special_characters(self, text: str) -> str:
        """Handle special characters and Unicode in input text.

        - Normalize unicode and compatibility forms.
        - Convert smart quotes and dashes to ASCII equivalents.
        - Strip diacritics (é -> e) while keeping letters/numbers and a small set of preserved punctuation.
        - Replace other unusual characters with a single space and collapse whitespace.
        """
        import unicodedata
        import re

        if not text:
            return ""

        # 1) Normalize compatibility to a canonical form
        text = unicodedata.normalize("NFKC", text)

        # 2) Convert common smart/directional quotes and dashes to ASCII
        # Double quotes variants -> "
        double_quote_variants = [
            "\u201C", "\u201D", "\u00AB", "\u00BB", "\u201E", "\u201F", "\u2033"
        ]
        for ch in double_quote_variants:
            text = text.replace(ch, '"')

        # Single quote / apostrophe variants -> '
        single_quote_variants = [
            "\u2018", "\u2019", "\u201A", "\u201B", "\u02BC", "\uFF07", "\u2032"
        ]
        for ch in single_quote_variants:
            text = text.replace(ch, "'")

        # Common dash variants -> -
        dash_variants = ["\u2013", "\u2014", "\u2212"]  # en-dash, em-dash, minus sign
        for ch in dash_variants:
            text = text.replace(ch, "-")

        # NBSP -> regular space
        text = text.replace("\u00A0", " ")

        # 3) Remove diacritic marks (é -> e) by decomposing and stripping combining marks
        text = "".join(
            ch for ch in unicodedata.normalize("NFKD", text)
            if not unicodedata.combining(ch)
        )

        # 4) Preserve a small set of punctuation that is important in names/dates/vehicles
        preserved_chars = set(["-", "'", "/", " ", "(", ")", ".", "&", "@"])

        # 5) Build the cleaned result
        result_chars = []
        for ch in text:
            # ASCII printable characters: keep as-is
            if ord(ch) < 128:
                result_chars.append(ch)
                continue

            cat = unicodedata.category(ch)  # e.g. 'Ll', 'Lu', 'Nd', 'Po', etc.

            # Keep letters from other scripts
            if cat.startswith("L"):
                result_chars.append(ch)
            # Keep numbers (any numeric category)
            elif cat.startswith("N"):
                result_chars.append(ch)
            # If the character itself is in preserved_chars (some may be non-ascii), keep it
            elif ch in preserved_chars:
                result_chars.append(ch)
            else:
                # Replace everything else with a space to preserve word boundaries
                result_chars.append(" ")

        processed_text = "".join(result_chars)

        # Collapse multiple whitespace into a single space and trim
        processed_text = re.sub(r"\s+", " ", processed_text).strip()

        return processed_text


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
