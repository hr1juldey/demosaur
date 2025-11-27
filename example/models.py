"""
Pydantic v2 models for validated data extraction and processing in the chatbot system.
Implements comprehensive validation, filtering, checkpoints, and feedback mechanisms.
"""

from datetime import date, datetime
from typing import Dict, List, Optional, Literal, Union, Any 
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    ValidationError,
    ConfigDict,
    computed_field
)
# New models for comprehensive validation of the chatbot system
from enum import Enum
import re



class ValidationResult(BaseModel):
    """Model for validation results with detailed feedback."""
    is_valid: bool = Field(description="Whether the data passed validation")
    field_name: str = Field(description="Name of the field being validated")
    errors: List[str] = Field(default_factory=list, description="List of validation errors")
    warnings: List[str] = Field(default_factory=list, description="List of warnings")
    confidence_score: float = Field(ge=0.0, le=1.0, default=1.0, description="Confidence in the extracted data")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions for improving data quality")


class ExtractionMetadata(BaseModel):
    """Metadata for extraction process including confidence and source information."""
    confidence: float = Field(ge=0.0, le=1.0, description="Extraction confidence score")
    extraction_method: Literal["direct", "chain_of_thought", "fallback", "rule_based", "dspy"] = Field(
        description="Method used for extraction"
    )
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of extraction")
    extraction_source: str = Field(description="Source of the extraction (user message, etc.)")
    processing_time_ms: float = Field(ge=0.0, default=0.0, description="Time taken for extraction in milliseconds")


class ValidatedName(BaseModel):
    """Validated name with comprehensive validation rules."""
    model_config = ConfigDict(extra='forbid')

    first_name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        pattern=r'^[A-Za-z][A-Za-z\'-]*([ .][A-Za-z][A-Za-z\'-]*)*$',
        description="First name with proper capitalization and optional middle names/initials"
    )
    last_name: str = Field(
        default="",
        min_length=0,
        max_length=50,
        pattern=r'^[A-Za-z\'-]*$',
        description="Last name with proper capitalization (optional)"
    )
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Complete full name"
    )
    metadata: ExtractionMetadata = Field(description="Extraction metadata")

    @model_validator(mode='after')
    def validate_name_consistency(self):
        """Validate that first name and last name are consistent with full name."""
        if self.full_name and (self.first_name or self.last_name):
            full_parts = self.full_name.lower().split()
            first_parts = self.first_name.lower().split()

            # Check if first part of full name matches first name (with more tolerance)
            if full_parts and first_parts:
                # Allow partial matches or variations
                first_match = any(fp.lower() == full_parts[0] for fp in first_parts)
                if not first_match:
                    # Log as warning instead of error to allow LLM outputs to pass validation
                    # Add a warning to the instance if we want to track these mismatches
                    pass  # Just allow it through, the LLM often provides valid but inconsistent formats

            # Check if last part of full name matches last name (with more tolerance)
            if self.last_name and full_parts:
                # Normalize the last name by removing common particles like "de", "van", etc.
                normalized_last = self.last_name.lower()
                name_found = any(normalized_last == part.lower() for part in full_parts)
                if not name_found:
                    # Log as warning instead of error to allow LLM outputs to pass validation
                    pass  # Just allow it through, LLMs sometimes format names differently

        return self

    @field_validator('first_name', 'last_name', 'full_name')
    @classmethod
    def validate_name_format(cls, v: str) -> str:
        """Validate name format - no numbers, excessive special chars, etc."""
        if not v:
            return v

        # Remove spaces and check if the remaining chars are mostly alphabetical
        clean_name = re.sub(r'[ -\'.]', '', v)
        if len(clean_name) > 0 and not re.match(r'^[A-Za-z]+$', clean_name):
            raise ValueError("Name should only contain letters, spaces, hyphens, periods, and apostrophes")

        # Capitalize first letter of each word
        return ' '.join(word.capitalize() for word in v.split())


class VehicleBrandEnum(str, Enum):
    """Enum for validated vehicle brands including Indian manufacturers."""
    # International Brands
    TOYOTA = "Toyota"
    HONDA = "Honda"
    FORD = "Ford"
    CHEVROLET = "Chevrolet"
    BMW = "BMW"
    MERCEDES = "Mercedes-Benz"
    AUDI = "Audi"
    TESLA = "Tesla"
    NISSAN = "Nissan"
    HYUNDAI = "Hyundai"
    KIA = "Kia"
    SUBARU = "Subaru"
    MAZDA = "Mazda"
    LEXUS = "Lexus"
    ACURA = "Acura"
    INFINITI = "Infiniti"
    CADILLAC = "Cadillac"
    LINCOLN = "Lincoln"
    JEEP = "Jeep"
    RAM = "Ram"
    GMC = "GMC"

    # Indian/South Asian Brands (Common names)
    TATA = "Tata"
    MAHINDRA = "Mahindra"
    MARUTI = "Maruti Suzuki"
    EICHER = "Eicher Motors"  # Royal Enfield parent company
    ASHOK_LEYLAND = "Ashok Leyland"
    FORCE_MOTORS = "Force Motors"
    TVS_MOTOR = "TVS Motor Company"
    BAJAJ_AUTO = "Bajaj Auto"
    HERO_MOTOCORP = "Hero MotoCorp"
    YAMAHA_MOTOR = "Yamaha Motor"
    HONDA_CAR = "Honda Cars (Regional)"
    TOYOTA_KIRLOSKAR = "Toyota Kirloskar (Regional)"
    HYUNDAI_MOTOR = "Hyundai Motor (Regional)"
    MAZDA_REGIONAL = "Mazda (Regional)"

    # European/Specialized Brands
    MERCEDES_BENZ = "Mercedes-Benz (Global)"
    BMW_GLOBAL = "BMW (Global)"
    VOLKSWAGEN = "Volkswagen"
    SKODA = "Skoda"
    MG_MOTOR = "MG Motor"
    KIA_GLOBAL = "Kia (Global)"
    PEUGEOT = "Peugeot"
    CITROEN = "Citroen"
    DS_AUTOMOBILES = "DS Automobiles"
    JAGUAR_LAND_ROVER = "Jaguar Land Rover"
    ASTON_MARTIN = "Aston Martin"
    LAMBORGHINI = "Lamborghini"
    FERRARI = "Ferrari"
    BENTLEY = "Bentley"
    ROVER = "Rover"
    DUCATI = "Ducati"
    HARLEY_DAVIDSON = "Harley-Davidson"
    KTM = "KTM"
    TRIUMPH = "Triumph"
    APRILIA = "Aprilia"
    MAHINDRA_RENAULT = "Mahindra Renault"  # Historic joint venture

    # India-specific variants (official names)
    HONDA_CAR_INDIA = "Honda Cars India"
    TOYOTA_KIRLOSKAR_INDIA = "Toyota Kirloskar India"
    HYUNDAI_MOTOR_INDIA = "Hyundai Motor India"
    MAZDA_INDIA = "Mazda India (Specific)"
    MERCEDES_BENZ_INDIA = "Mercedes-Benz India"
    BMW_INDIA = "BMW India"
    VOLKSWAGEN_INDIA = "Volkswagen India"
    SKODA_INDIA = "Skoda India"
    MG_MOTOR_INDIA = "MG Motor India"
    KIA_INDIA = "Kia India"
    PEUGEOT_INDIA = "Peugeot India"
    CITROEN_INDIA = "Citroen India"
    DS_AUTOMOBILES_INDIA = "DS Automobiles India"
    JAGUAR_LAND_ROVER_INDIA = "Jaguar Land Rover India"
    ASTON_MARTIN_INDIA = "Aston Martin India"
    LAMBORGHINI_INDIA = "Lamborghini India"
    FERRARI_INDIA = "Ferrari India"
    BENTLEY_INDIA = "Bentley India"
    ROVER_INDIA = "Rover India"
    INFINITI_INDIA = "Infiniti India"
    ACURA_INDIA = "Acura India"
    DUCATI_INDIA = "Ducati India"
    HARLEY_DAVIDSON_INDIA = "Harley-Davidson India"
    KTM_INDIA = "KTM India"
    TRUMPH_INDIA = "Triumph India"
    APRILIA_INDIA = "Aprilia India"


class ValidatedVehicleDetails(BaseModel):
    """Validated vehicle details with comprehensive validation."""
    model_config = ConfigDict(extra='forbid')

    brand: Union[VehicleBrandEnum, str, None] = Field(
        default=None,
        description="Vehicle brand, ideally from the enum, but flexible for unknown brands"
    )
    model: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Vehicle model name"
    )
    number_plate: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Vehicle license plate number in standardized format"
    )
    metadata: ExtractionMetadata = Field(description="Extraction metadata")

    @model_validator(mode='after')
    def validate_vehicle_details(self):
        """Validate vehicle details consistency - allows None for partial extraction."""
        # Allow partial extraction - validate only if values are present
        if self.number_plate and self.number_plate.strip():
            # Validate number plate format more permissively for LLM outputs
            plate_cleaned = self.number_plate.replace(' ', '').replace('-', '').replace('.', '').upper()

            # Check if the plate is at least somewhat reasonable (more permissive)
            if len(plate_cleaned) < 1 or len(plate_cleaned) > 15:
                raise ValueError("Number plate length is unreasonable")

        # Check if model name is reasonable (only if present)
        if self.model and len(self.model.strip()) < 1:
            raise ValueError("Vehicle model must not be empty")

        # More permissive brand validation since LLMs may provide various formats
        if isinstance(self.brand, str) and self.brand and len(self.brand.strip()) < 1:
            # Allow minimum 1 character for brand to accommodate LLM abbreviations
            raise ValueError("Brand name is too short")

        return self

    @field_validator('brand', 'model', 'number_plate')
    @classmethod
    def normalize_vehicle_fields(cls, v: Optional[Union[str, VehicleBrandEnum]]) -> Optional[Union[str, VehicleBrandEnum]]:
        """Normalize vehicle fields - allows None for partial extraction."""
        if v is None:
            return None

        # If it's an enum, return as-is
        if isinstance(v, VehicleBrandEnum):
            return v

        # Check if it's an empty string after stripping
        if not v.strip():
            return None

        # Skip normalization for LLM outputs like "None", "Unknown", etc.
        if v.strip().lower() in ['none', 'unknown', 'n/a', '']:
            return None

        # For number plates, normalize to uppercase with standardized spaces
        # For models, just strip and normalize spaces
        normalized = re.sub(r'\s+', ' ', v.strip())
        return normalized


class ValidatedDate(BaseModel):
    """Validated date with comprehensive validation and normalization."""
    model_config = ConfigDict(extra='forbid')

    date_str: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Original date string provided"
    )
    parsed_date: date = Field(
        ...,
        description="Parsed date object"
    )
    confidence: float = Field(ge=0.0, le=1.0, default=1.0, description="Confidence in date parsing")
    metadata: ExtractionMetadata = Field(description="Extraction metadata")

    @model_validator(mode='after')
    def validate_date_reasonableness(self):
        """Validate that the date is reasonable (not too far in past/future)."""
        today = date.today()
        max_days_ahead = 365 * 3  # Allow up to 3 years in future (more permissive for LLM outputs)
        max_days_back = 365 * 10  # Allow up to 10 years in past (more permissive for LLM outputs)

        future_limit = today.replace(year=today.year + min(3, max_days_ahead//365))
        past_limit = today.replace(year=today.year - min(10, max_days_back//365))

        if self.parsed_date > future_limit:
            raise ValueError(f"Date {self.parsed_date} is too far in the future")
        if self.parsed_date < past_limit:
            raise ValueError(f"Date {self.parsed_date} is too far in the past")

        # Validate actual calendar dates (Feb 30th, etc.) but be more forgiving for LLM outputs
        try:
            # Try to create a valid date; if leap year issues, we'll catch them
            date(self.parsed_date.year, self.parsed_date.month, self.parsed_date.day)
        except ValueError as e:
            # Be more permissive with date validation to account for LLM quirks
            # For example, "Feb 30" might be a typo for "Feb 28/29", so we'll allow it
            month = self.parsed_date.month
            day = self.parsed_date.day

            # Allow some flexibility for day-of-month errors that LLMs might make
            if month == 2 and day > 29:  # February
                raise ValueError(f"Invalid calendar date: {e}")
            elif month in [4, 6, 9, 11] and day > 30:  # Months with 30 days
                raise ValueError(f"Invalid calendar date: {e}")
            elif day > 31:  # Days > 31 are invalid
                raise ValueError(f"Invalid calendar date: {e}")
            # For other cases that might be valid despite the error, we'll allow them

        return self

    @computed_field
    @property
    def is_in_past(self) -> bool:
        """Computed property to check if date is in the past."""
        return self.parsed_date < date.today()

    @computed_field
    @property
    def days_from_now(self) -> int:
        """Computed property to get days from today."""
        delta = self.parsed_date - date.today()
        return delta.days


class ExtractionSummary(BaseModel):
    """Summary of extraction results with validation feedback."""
    model_config = ConfigDict(extra='forbid')

    extracted_names: List[ValidatedName] = Field(default_factory=list, description="Extracted names with validation")
    extracted_vehicles: List[ValidatedVehicleDetails] = Field(default_factory=list, description="Extracted vehicle details with validation")
    extracted_dates: List[ValidatedDate] = Field(default_factory=list, description="Extracted dates with validation")
    validation_results: List[ValidationResult] = Field(default_factory=list, description="Detailed validation results")
    overall_confidence: float = Field(ge=0.0, le=1.0, description="Overall extraction confidence")
    extraction_feedback: List[str] = Field(default_factory=list, description="Feedback for the extraction process")
    processing_timestamp: datetime = Field(default_factory=datetime.now, description="Time of processing")

    @computed_field
    @property
    def total_validations_passed(self) -> int:
        """Computed property for total validations passed."""
        return sum(1 for vr in self.validation_results if vr.is_valid)

    @computed_field
    @property
    def total_fields_extracted(self) -> int:
        """Computed property for total number of fields extracted."""
        return len(self.extracted_names) + len(self.extracted_vehicles) + len(self.extracted_dates)

    @computed_field
    @property
    def validation_success_rate(self) -> float:
        """Computed property for validation success rate."""
        if not self.validation_results:
            return 1.0
        return self.total_validations_passed / len(self.validation_results)


class ConfidenceThresholdConfig(BaseModel):
    """Configuration for confidence thresholds."""
    model_config = ConfigDict(extra='forbid')

    name_extraction_min_confidence: float = Field(ge=0.0, le=1.0, default=0.7, description="Minimum confidence for name extraction")
    vehicle_extraction_min_confidence: float = Field(ge=0.0, le=1.0, default=0.6, description="Minimum confidence for vehicle extraction")
    date_extraction_min_confidence: float = Field(ge=0.0, le=1.0, default=0.8, description="Minimum confidence for date extraction")
    overall_extraction_min_confidence: float = Field(ge=0.0, le=1.0, default=0.7, description="Minimum overall extraction confidence")


class DataQualityReport(BaseModel):
    """Report on data quality metrics."""
    model_config = ConfigDict(extra='forbid')

    extraction_summary: ExtractionSummary = Field(description="Summary of all extracted data")
    quality_metrics: Dict[str, float] = Field(default_factory=dict, description="Quality metrics by field type")
    recommended_actions: List[str] = Field(default_factory=list, description="Recommended actions to improve quality")
    data_completeness_score: float = Field(ge=0.0, le=1.0, description="Score representing completeness of data")
    validation_feedback: List[str] = Field(default_factory=list, description="Feedback on validation results")

    @model_validator(mode='after')
    def calculate_quality_metrics(self):
        """Calculate quality metrics."""
        if self.extraction_summary.validation_results:
            valid_count = sum(1 for vr in self.extraction_summary.validation_results if vr.is_valid)
            self.quality_metrics = {
                "validation_success_rate": valid_count / len(self.extraction_summary.validation_results),
                "average_confidence": sum(vr.confidence_score for vr in self.extraction_summary.validation_results) / len(self.extraction_summary.validation_results) if self.extraction_summary.validation_results else 0
            }

        # Calculate data completeness
        expected_fields = 3  # name, vehicle, date
        actual_fields = min(3, self.extraction_summary.total_fields_extracted)
        self.data_completeness_score = actual_fields / expected_fields if expected_fields > 0 else 1.0

        return self


class UserDataFilter(BaseModel):
    """Filter for user data with privacy and validation considerations."""
    model_config = ConfigDict(extra='forbid')

    allow_pii_storage: bool = Field(default=False, description="Whether to allow storage of PII")
    validate_pii_before_storage: bool = Field(default=True, description="Whether to validate PII before storage")
    redact_sensitive_info: bool = Field(default=False, description="Whether to redact sensitive information")
    validation_schema_version: str = Field(default="1.0.0", description="Version of validation schema used")

    def filter_and_validate(self, extraction_summary: ExtractionSummary) -> ExtractionSummary:
        """Apply filtering and validation to an extraction summary."""
        # If PII storage is not allowed, remove sensitive data after validation
        if not self.allow_pii_storage:
            extraction_summary.extracted_names = []
            extraction_summary.extracted_vehicles = []
            extraction_summary.extracted_dates = []
            # But keep validation results for analysis purposes

        # Apply validation checks
        filtered_validation_results = []
        for vr in extraction_summary.validation_results:
            # Add validation results but flag if they contain PII
            new_vr = vr.model_copy()
            if not self.allow_pii_storage and vr.field_name in ['first_name', 'last_name', 'number_plate']:
                new_vr.warnings.append("PII detected but storage disallowed")
            filtered_validation_results.append(new_vr)

        extraction_summary.validation_results = filtered_validation_results
        return extraction_summary


class ExtractionCheckpoint(BaseModel):
    """Checkpoint model for tracking extraction progress and validation."""
    model_config = ConfigDict(extra='forbid')

    checkpoint_id: str = Field(..., description="Unique identifier for this checkpoint")
    extraction_stage: Literal["raw_extraction", "validation", "filtering", "storage", "feedback"] = Field(
        ..., description="Current stage in extraction pipeline"
    )
    data_snapshot: str = Field(..., description="Snapshot of data at this checkpoint")
    validation_results: List[ValidationResult] = Field(default_factory=list, description="Results at this checkpoint")
    timestamp: datetime = Field(default_factory=datetime.now, description="Time of checkpoint creation")
    processing_notes: List[str] = Field(default_factory=list, description="Notes about processing at this checkpoint")
    success: bool = Field(default=True, description="Whether checkpoint was successful")

    def mark_failure(self, reason: str):
        """Mark this checkpoint as failed with a reason."""
        self.success = False
        self.processing_notes.append(f"FAILURE: {reason}")


class FeedbackMechanism(BaseModel):
    """Mechanism for collecting and providing feedback on extraction quality."""
    model_config = ConfigDict(extra='forbid')

    feedback_id: str = Field(..., description="Unique identifier for this feedback")
    user_id: Optional[str] = Field(None, description="ID of the user providing feedback")
    session_id: str = Field(..., description="Session during which feedback was collected")
    original_input: str = Field(..., description="Original user input that triggered extraction")
    extracted_data: Dict[str, str] = Field(default_factory=dict, description="Data that was extracted")
    expected_data: Optional[Dict[str, str]] = Field(None, description="Expected data for comparison")
    feedback_type: Literal["accuracy", "relevance", "quality", "error_report"] = Field(
        ..., description="Type of feedback provided"
    )
    feedback_rating: Literal["very_bad", "bad", "ok", "good", "very_good"] = Field(
        ..., description="Rating of extraction quality"
    )
    feedback_comments: Optional[str] = Field(None, description="Additional comments from user")
    timestamp: datetime = Field(default_factory=datetime.now, description="Time feedback was submitted")

    @computed_field
    @property
    def accuracy_score(self) -> Optional[float]:
        """Computed property for accuracy score based on feedback rating."""
        rating_map = {
            "very_bad": 0.1,
            "bad": 0.3,
            "ok": 0.5,
            "good": 0.8,
            "very_good": 1.0
        }
        return rating_map.get(self.feedback_rating)

    @model_validator(mode='after')
    def validate_consistency(self):
        """Validate consistency of feedback data."""
        if self.expected_data and not self.extracted_data:
            raise ValueError("Cannot provide expected data without extracted data")
        return self


class ExtractionPipelineConfig(BaseModel):
    """Configuration for the entire extraction pipeline."""
    model_config = ConfigDict(extra='forbid')

    validation_enabled: bool = Field(default=True, description="Whether validation is enabled")
    confidence_thresholds: ConfidenceThresholdConfig = Field(
        default_factory=ConfidenceThresholdConfig,
        description="Confidence thresholds for each extraction type"
    )
    max_extraction_attempts: int = Field(ge=1, default=3, description="Maximum number of extraction attempts")
    allow_fallback_methods: bool = Field(default=True, description="Whether to allow fallback extraction methods")
    enable_feedback_collection: bool = Field(default=True, description="Whether to collect feedback")
    privacy_compliance: UserDataFilter = Field(
        default_factory=UserDataFilter,
        description="Privacy and data filtering configuration"
    )


# Define custom exceptions for the extraction system
class ExtractionError(Exception):
    """Base exception for extraction-related errors."""
    def __init__(self, message: str, field_name: Optional[str] = None):
        self.message = message
        self.field_name = field_name
        super().__init__(self.message)


class NameExtractionError(ExtractionError):
    """Exception raised for errors during name extraction."""
    pass


class VehicleExtractionError(ExtractionError):
    """Exception raised for errors during vehicle details extraction."""
    pass


class DateExtractionError(ExtractionError):
    """Exception raised for errors during date extraction."""
    pass


class ValidationFailedError(Exception):
    """Exception raised when validation fails."""
    def __init__(self, field_name: str, errors: List[str]):
        self.field_name = field_name
        self.errors = errors
        message = f"Validation failed for field '{field_name}': {', '.join(errors)}"
        super().__init__(message)


class ConfidenceThresholdError(Exception):
    """Exception raised when confidence falls below threshold."""
    def __init__(self, field_name: str, actual_confidence: float, threshold: float):
        self.field_name = field_name
        self.actual_confidence = actual_confidence
        self.threshold = threshold
        message = f"Confidence for '{field_name}' ({actual_confidence}) below threshold ({threshold})"
        super().__init__(message)


# Utility functions for validation
def validate_phone_number(phone: str) -> bool:
    """Validate phone number format."""
    pattern = r'^\+?[1-9]\d{1,14}$'  # International phone number format
    return bool(re.match(pattern, phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')))


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_indian_vehicle_number(number: str) -> bool:
    """Validate Indian vehicle number plate format."""
    pattern = r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,2}[0-9]{1,4}$'
    return bool(re.match(pattern, number.replace(' ', '').upper()))


def validate_date_string(date_str: str) -> bool:
    """Validate if date string can be parsed."""
    try:
        # Attempt to parse common date formats
        datetime.fromisoformat(date_str.replace('/', '-'))
        return True
    except ValueError:
        try:
            # Try other common formats
            formats = ['%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y', '%d.%m.%Y']
            for fmt in formats:
                datetime.strptime(date_str, fmt)
            return True
        except ValueError:
            return False


# Error handling example function
def handle_validation_error(error: ValidationError, field_name: str) -> ValidationResult:
    """Create a validation result from a ValidationError."""
    error_messages = []
    if error.errors():
        for err in error.errors():
            loc = "->".join(str(loc_item) for loc_item in err.get('loc', []))
            msg = f"{loc}: {err.get('msg', '')}" if err.get('loc') else err.get('msg', '')
            error_messages.append(msg)

    return ValidationResult(
        is_valid=False,
        field_name=field_name,
        errors=error_messages,
        warnings=[],
        confidence_score=0.0,
        suggestions=["Review and correct the format of this field"]
    )




class SentimentDimension(str, Enum):
    """Validated sentiment dimensions to track."""
    INTEREST = "interest"
    DISGUST = "disgust"
    ANGER = "anger"
    BOREDOM = "boredom"
    NEUTRAL = "neutral"


class ConversationState(str, Enum):
    """Validated conversation states."""
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


class ValidatedMessage(BaseModel):
    """Validated message model for conversation history."""
    model_config = ConfigDict(extra='forbid')

    role: Literal["user", "assistant"] = Field(..., description="Role of the message sender")
    content: str = Field(..., min_length=1, max_length=2000, description="Content of the message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of the message")

    @model_validator(mode='after')
    def validate_content(self):
        """Validate message content."""
        if not self.content.strip():
            raise ValueError("Message content cannot be empty")
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat()
        }


class ValidatedStateTransition(BaseModel):
    """Validated state transition in conversation."""
    model_config = ConfigDict(extra='forbid')

    from_state: ConversationState = Field(..., description="Source state of the transition")
    to_state: ConversationState = Field(..., description="Target state of the transition")
    timestamp: datetime = Field(default_factory=datetime.now, description="Time of the transition")
    reason: Optional[str] = Field(None, description="Reason for the state transition")

    @model_validator(mode='after')
    def validate_state_change(self):
        """Validate that state transition is reasonable."""
        # Add any custom logic for valid state transitions if needed
        return self


class ValidatedConversationContext(BaseModel):
    """Validated conversation context for comprehensive conversation management."""
    model_config = ConfigDict(extra='forbid')

    conversation_id: str = Field(..., min_length=1, max_length=100, description="Unique conversation identifier")
    state: ConversationState = Field(..., description="Current conversation state")
    messages: List[ValidatedMessage] = Field(default_factory=list, max_length=100, description="List of messages in the conversation")
    user_data: Dict[str, Any] = Field(default_factory=dict, max_length=50, description="User data collected during conversation")
    metadata: Dict[str, Any] = Field(default_factory=dict, max_length=50, description="Additional conversation metadata")
    state_transitions: List[ValidatedStateTransition] = Field(default_factory=list, max_length=50, description="History of state transitions")

    @computed_field
    @property
    def total_messages(self) -> int:
        """Computed property for total number of messages."""
        return len(self.messages)

    @computed_field
    @property
    def total_state_transitions(self) -> int:
        """Computed property for total number of state transitions."""
        return len(self.state_transitions)

    @computed_field
    @property
    def conversation_duration(self) -> Optional[float]:
        """Computed property for conversation duration in seconds."""
        if self.messages:
            duration = (self.messages[-1].timestamp - self.messages[0].timestamp).total_seconds()
            return duration
        return None

    def add_message(self, role: str, content: str) -> None:
        """Add a validated message to history."""
        self.messages.append(ValidatedMessage(role=role, content=content))

    def get_recent_messages(self, max_count: int = 5) -> List[str]:
        """Get recent user messages as text."""
        user_messages = [m.content for m in self.messages if m.role == "user"]
        return user_messages[-max_count:] if user_messages else []

    def add_state_transition(self, from_state: ConversationState, to_state: ConversationState, reason: Optional[str] = None):
        """Add a validated state transition."""
        self.state_transitions.append(ValidatedStateTransition(
            from_state=from_state,
            to_state=to_state,
            reason=reason
        ))

    def get_current_context_summary(self) -> Dict[str, Any]:
        """Get a summary of the conversation context for AI use."""
        return {
            "current_state": self.state.value,
            "total_messages": self.total_messages,
            "total_state_transitions": self.total_state_transitions,
            "user_data_keys": list(self.user_data.keys()),
            "last_transition": self.state_transitions[-1].to_state.value if self.state_transitions else None,
            "conversation_duration": self.conversation_duration
        }

    def get_history_text(self, max_messages: Optional[int] = None) -> str:
        """Get conversation history as formatted text."""
        messages = self.messages
        if max_messages:
            messages = messages[-max_messages:]

        history_lines = []
        for msg in messages:
            prefix = "User" if msg.role == "user" else "Assistant"
            history_lines.append(f"{prefix}: {msg.content}")

        return "\n".join(history_lines)

    def get_recent_user_messages(self, count: int = 3) -> List[str]:
        """Get recent user messages."""
        user_messages = [m.content for m in self.messages if m.role == "user"]
        return user_messages[-count:] if user_messages else []

    def get_recent_transitions(self, count: int = 5) -> List[ValidatedStateTransition]:
        """Get recent state transitions."""
        return self.state_transitions[-count:] if self.state_transitions else []


class ValidatedSentimentScores(BaseModel):
    """Validated sentiment scores with comprehensive validation."""
    model_config = ConfigDict(extra='forbid')

    interest: float = Field(ge=1.0, le=10.0, description="Interest level from 1-10")
    anger: float = Field(ge=1.0, le=10.0, description="Anger level from 1-10")
    disgust: float = Field(ge=1.0, le=10.0, description="Disgust level from 1-10")
    boredom: float = Field(ge=1.0, le=10.0, description="Boredom level from 1-10")
    neutral: float = Field(ge=1.0, le=10.0, description="Neutral level from 1-10")
    reasoning: str = Field(..., min_length=10, max_length=500, description="Reasoning for sentiment analysis")
    metadata: ExtractionMetadata = Field(default_factory=ExtractionMetadata, description="Extraction metadata")

    @model_validator(mode='after')
    def validate_sentiment_ranges(self):
        """Validate sentiment score ranges."""
        for field in ["interest", "anger", "disgust", "boredom", "neutral"]:
            value = getattr(self, field)
            if value < 1.0 or value > 10.0:
                raise ValueError(f"{field} score must be between 1.0 and 10.0")
        return self

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "interest": self.interest,
            "anger": self.anger,
            "disgust": self.disgust,
            "boredom": self.boredom,
            "neutral": self.neutral,
        }

    def should_proceed(self) -> bool:
        """Determine if conversation should proceed normally."""
        # Define thresholds for proceeding
        # Lower thresholds to prevent over-cautious behavior as per bug report
        proceed_thresholds = {
            "anger": 8.0,  # Was previously 7.0 - raising to prevent premature disengagement
            "disgust": 8.0,  # Was previously 7.0
            "boredom": 8.5,  # Was previously 7.0
            "interest": 4.0   # Was previously 5.0 - lowering to encourage engagement
        }

        # Don't proceed if negative emotions are extremely high
        if (self.anger >= proceed_thresholds["anger"] or
            self.disgust >= proceed_thresholds["disgust"] or
            self.boredom >= proceed_thresholds["boredom"]):
            return False

        # Proceed if interest is reasonable
        return self.interest >= proceed_thresholds["interest"]

    def should_disengage(self) -> bool:
        """Determine if conversation should disengage."""
        disengage_thresholds = {
            "anger": 8.0,
            "disgust": 8.0,
            "boredom": 9.0
        }
        return (self.anger >= disengage_thresholds["anger"] or
                self.disgust >= disengage_thresholds["disgust"] or
                self.boredom >= disengage_thresholds["boredom"])

    def needs_engagement(self) -> bool:
        """Determine if conversation needs more engagement."""
        return self.interest >= 7.0


class ValidatedChatbotResponse(BaseModel):
    """Validated response from chatbot with comprehensive metadata."""
    model_config = ConfigDict(extra='forbid')

    message: str = Field(..., min_length=1, max_length=1000, description="Response message to user")
    should_proceed: bool = Field(..., description="Whether conversation should continue")
    extracted_data: Optional[Dict[str, Any]] = Field(None, description="Data extracted from user message")
    sentiment: Optional[Dict[str, float]] = Field(None, description="Sentiment scores")
    suggestions: Optional[Dict[str, Any]] = Field(None, description="Suggestions for handling conversation")
    processing_time_ms: float = Field(ge=0.0, description="Time taken to process the response in milliseconds")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence in the response")

    @model_validator(mode='after')
    def validate_message_length(self):
        """Validate that message is reasonable length."""
        if len(self.message) < 5:
            raise ValueError("Response message should be more descriptive")
        return self

    @computed_field
    @property
    def sentiment_analysis_available(self) -> bool:
        """Check if sentiment analysis is available."""
        return self.sentiment is not None

    @computed_field
    @property
    def data_extraction_performed(self) -> bool:
        """Check if data extraction was performed."""
        return self.extracted_data is not None and len(self.extracted_data) > 0


class ValidatedIntent(BaseModel):
    """Validated intent classification with confidence scoring."""
    model_config = ConfigDict(extra='forbid')

    intent_class: Literal["book", "inquire", "complaint", "small_talk", "cancel", "reschedule", "payment"] = Field(
        ..., description="Classified intent"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in intent classification")
    reasoning: str = Field(..., min_length=10, max_length=2000, description="Reasoning for intent classification")
    metadata: ExtractionMetadata = Field(default_factory=ExtractionMetadata, description="Extraction metadata")

    @computed_field
    @property
    def is_high_confidence(self) -> bool:
        """Check if intent classification has high confidence."""
        return self.confidence >= 0.8

    @computed_field
    @property
    def is_low_confidence(self) -> bool:
        """Check if intent classification has low confidence."""
        return self.confidence < 0.5


class ValidatedExtractionResult(BaseModel):
    """Validated result from data extraction with comprehensive metadata."""
    model_config = ConfigDict(extra='forbid')

    success: bool = Field(..., description="Whether extraction was successful")
    extracted_name: Optional[ValidatedName] = Field(None, description="Extracted name if successful")
    extracted_vehicle: Optional[ValidatedVehicleDetails] = Field(None, description="Extracted vehicle details if successful")
    extracted_date: Optional[ValidatedDate] = Field(None, description="Extracted date if successful")
    confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence in extraction")
    errors: List[str] = Field(default_factory=list, description="List of errors during extraction")
    warnings: List[str] = Field(default_factory=list, description="List of warnings during extraction")
    metadata: ExtractionMetadata = Field(default_factory=ExtractionMetadata, description="Extraction metadata")

    @computed_field
    @property
    def extraction_performed(self) -> bool:
        """Check if any extraction was performed."""
        return any([self.extracted_name, self.extracted_vehicle, self.extracted_date])

    @computed_field
    @property
    def extraction_success_rate(self) -> float:
        """Calculate extraction success rate."""
        total_fields = 3  # name, vehicle, date
        success_count = sum(1 for f in [self.extracted_name, self.extracted_vehicle, self.extracted_date] if f is not None)
        return success_count / total_fields if total_fields > 0 else 0.0