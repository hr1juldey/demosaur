"""
Configuration settings for the intelligent chatbot system.
"""
from enum import Enum
from typing import Dict


class SentimentDimension(str, Enum):
    """Sentiment dimensions to track."""
    INTEREST = "interest"
    DISGUST = "disgust"
    ANGER = "anger"
    BOREDOM = "boredom"
    NEUTRAL = "neutral"


class ConversationState(str, Enum):
    """Current state of the conversation flow."""
    GREETING = "greeting"
    NAME_COLLECTION = "name_collection"
    SERVICE_SELECTION = "service_selection"
    TIER_SELECTION = "tier_selection"
    VEHICLE_TYPE = "vehicle_type"
    VEHICLE_DETAILS = "vehicle_details"
    DATE_SELECTION = "date_selection"
    SLOT_SELECTION = "slot_selection"
    ADDRESS_COLLECTION = "address_collection"
    CONFIRMATION = "confirmation"
    COMPLETED = "completed"


class Config:
    """Main configuration class."""
    
    # DSPy/LLM Settings
    OLLAMA_BASE_URL = "http://localhost:11434"
    MODEL_NAME = "gpt-oss:20b"  # 8B parameter model for CPU
    MAX_TOKENS = 4000
    TEMPERATURE = 0.5  # Lower for consistency
    
    # Conversation Settings
    MAX_CHAT_HISTORY = 25
    SENTIMENT_CHECK_INTERVAL = 2  # Check sentiment every N messages
    
    # Sentiment Thresholds
    SENTIMENT_THRESHOLDS: Dict[str, Dict[str, float]] = {
        "proceed": {
            "interest": 5.0,
            "anger": 6.0,
            "disgust": 3.0,
            "boredom": 5.0,
        },
        "engage": {
            "interest": 5.0,
        },
        "disengage": {
            "anger": 8.0,
            "disgust": 8.0,
            "boredom": 9.0,
        }
    }
    
    # Service Information (for LLM context)
    SERVICES = {
        "wash": "Interior and Exterior Car wash",
        "polishing": "Interior and Exterior Car Polish",
        "detailing": "Interior and Exterior Car Detailing"
    }
    
    VEHICLE_TYPES = ["Hatchback", "Sedan", "SUV", "EV", "Luxury"]
    
    # Company Info
    COMPANY_NAME = "Yawlit Car Wash"
    COMPANY_DESCRIPTION = "Premium car care and carwash  services with professional detailing"


# Global config instance
config = Config()
