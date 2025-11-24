"""
Service for extracting structured data from unstructured user messages.
"""
from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from modules import NameExtractor, VehicleDetailsExtractor, DateParser
from dspy_config import ensure_configured


@dataclass
class ExtractedName:
    """Container for extracted name."""
    first_name: str
    last_name: str
    full_name: str
    confidence: str


@dataclass
class ExtractedVehicle:
    """Container for extracted vehicle details."""
    brand: str
    model: str
    number_plate: str


@dataclass
class ExtractedDate:
    """Container for extracted date."""
    date_str: str
    confidence: str


class DataExtractionService:
    """Service for extracting structured data from user messages."""
    
    def __init__(self):
        ensure_configured()
        self.name_extractor = NameExtractor()
        self.vehicle_extractor = VehicleDetailsExtractor()
        self.date_parser = DateParser()
    
    def extract_name(self, user_message: str) -> Optional[ExtractedName]:
        """Extract customer name from message."""
        try:
            result = self.name_extractor(user_message=user_message)
            
            first_name = str(result.first_name).strip()
            last_name = str(result.last_name).strip()
            
            if not first_name or first_name.lower() in ["none", "n/a", "unknown"]:
                return None
            
            # Clean up last name
            if last_name.lower() in ["none", "n/a", "unknown", ""]:
                last_name = ""
            
            full_name = f"{first_name} {last_name}".strip()
            
            return ExtractedName(
                first_name=first_name,
                last_name=last_name,
                full_name=full_name,
                confidence=str(result.confidence)
            )
        except Exception:
            return None
    
    def extract_vehicle_details(self, user_message: str) -> Optional[ExtractedVehicle]:
        """Extract vehicle details from message."""
        try:
            result = self.vehicle_extractor(user_message=user_message)
            
            brand = str(result.brand).strip()
            model = str(result.model).strip()
            plate = str(result.number_plate).strip()
            
            # Validate we got meaningful data
            if not brand or brand.lower() in ["none", "n/a", "unknown"]:
                return None
            
            return ExtractedVehicle(
                brand=brand,
                model=model,
                number_plate=plate
            )
        except Exception:
            return None
    
    def parse_date(self, user_message: str) -> Optional[ExtractedDate]:
        """Parse date from natural language."""
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            result = self.date_parser(
                user_message=user_message,
                current_date=current_date
            )
            
            date_str = str(result.parsed_date).strip()
            
            # Validate date format
            if not date_str or date_str.lower() in ["none", "unknown"]:
                return None
            
            # Try to parse to ensure valid date
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                return None
            
            return ExtractedDate(
                date_str=date_str,
                confidence=str(result.confidence)
            )
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
