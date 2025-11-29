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
    """Unified conversation state machine for all chat flows."""
    # Core booking flow
    GREETING = "greeting"
    NAME_COLLECTION = "name_collection"
    VEHICLE_DETAILS = "vehicle_details"
    DATE_SELECTION = "date_selection"
    CONFIRMATION = "confirmation"
    COMPLETED = "completed"

    # Optional states (unused but kept for future expansion)
    SERVICE_SELECTION = "service_selection"
    TIER_SELECTION = "tier_selection"
    VEHICLE_TYPE = "vehicle_type"
    SLOT_SELECTION = "slot_selection"
    ADDRESS_COLLECTION = "address_collection"

    # Terminal states
    CANCELLED = "cancelled"


class StateTransitionRules:
    """Defines valid state transitions - single source of truth for state machine."""
    VALID_TRANSITIONS = {
        ConversationState.GREETING: [
            ConversationState.NAME_COLLECTION,
            ConversationState.SERVICE_SELECTION,
        ],
        ConversationState.NAME_COLLECTION: [
            ConversationState.VEHICLE_DETAILS,
            ConversationState.SERVICE_SELECTION,
        ],
        ConversationState.SERVICE_SELECTION: [
            ConversationState.NAME_COLLECTION,
            ConversationState.VEHICLE_DETAILS,
        ],
        ConversationState.VEHICLE_DETAILS: [
            ConversationState.DATE_SELECTION,
            ConversationState.NAME_COLLECTION,
            ConversationState.SERVICE_SELECTION,
        ],
        ConversationState.DATE_SELECTION: [
            ConversationState.CONFIRMATION,
            ConversationState.VEHICLE_DETAILS,
        ],
        ConversationState.CONFIRMATION: [
            ConversationState.COMPLETED,
            ConversationState.DATE_SELECTION,  # edit
            ConversationState.CANCELLED,
        ],
        ConversationState.COMPLETED: [
            ConversationState.GREETING,
        ],
        ConversationState.CANCELLED: [
            ConversationState.GREETING,
        ],
        # Future states (not actively used)
        ConversationState.TIER_SELECTION: [
            ConversationState.CONFIRMATION,
        ],
        ConversationState.VEHICLE_TYPE: [
            ConversationState.VEHICLE_DETAILS,
        ],
        ConversationState.SLOT_SELECTION: [
            ConversationState.CONFIRMATION,
        ],
        ConversationState.ADDRESS_COLLECTION: [
            ConversationState.CONFIRMATION,
        ],
    }


class Config:
    """Main configuration class."""
    
    # DSPy/LLM Settings
    OLLAMA_BASE_URL = "http://localhost:11434"
    MODEL_NAME = "qwen3:8b"  # 8B parameter model for CPU
    MAX_TOKENS = 4000
    TEMPERATURE = 0.3  # Lower for consistency
    
    # Conversation Settings
    MAX_CHAT_HISTORY = 25
    SENTIMENT_CHECK_INTERVAL = 2  # Check sentiment every N messages
    RETROACTIVE_SCAN_LIMIT = 3  # Number of recent messages to scan in retroactive validator (prevents timeout)

    # Name Extraction Stopwords - Reject greetings/common responses as customer names
    # Fixes: Prevent "Haan" (Hindi yes), "Hello", "Hi" etc. from being extracted as first_name
    GREETING_STOPWORDS = {
        # Hindi/Urdu
        "haan", "haji", "han", "haa", "Ji" , "Haanji" , "Hello ji" , "Nomoshkar", "ji"
        # English
        "hello", "hi", "hey", "yes", "yeah", "yep", "ok", "okay", "sure", "fine",
        # Casual responses
        "ok", "okey", "yo", "yup",
        # Thanking words
        "Shukriya" , "Shukriya Ji", "Yaar" , "Dost" , "Sirji"
    }
    
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
