"""
ScratchpadManager: Single source of truth for collected booking data.

Tracks customer, vehicle, and appointment details with full metadata:
- Value, source, turn number, confidence, extraction method, timestamp
- Supports CRUD operations
- Calculates data completeness
"""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import json
from uuid import uuid4


class FieldEntry(BaseModel):
    """Single scraped field with metadata."""
    value: Optional[Any] = None
    source: Optional[str] = None  # "direct_extraction", "retroactive_extraction", "user_input", "inferred"
    turn: Optional[int] = None
    confidence: Optional[float] = None  # 0.0-1.0
    extraction_method: Optional[str] = None  # "dspy", "regex", "keyword", "user_provided"
    timestamp: Optional[datetime] = None


class ScratchpadForm(BaseModel):
    """Three-section scratchpad for booking data."""
    customer: Dict[str, FieldEntry] = Field(default_factory=dict)
    vehicle: Dict[str, FieldEntry] = Field(default_factory=dict)
    appointment: Dict[str, FieldEntry] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class ScratchpadManager:
    """CRUD operations + validation for scratchpad."""

    def __init__(self, conversation_id: Optional[str] = None):
        self.form = ScratchpadForm()
        self.conversation_id = conversation_id or str(uuid4())
        self.created_at = datetime.now()
        self._update_metadata()

    def add_field(
        self,
        section: str,
        field_name: str,
        value: Any,
        source: str,
        turn: int,
        confidence: float = 1.0,
        extraction_method: str = "user_provided"
    ) -> bool:
        """Add or update field in scratchpad with full metadata."""
        if section not in ["customer", "vehicle", "appointment"]:
            return False

        section_dict = getattr(self.form, section)
        section_dict[field_name] = FieldEntry(
            value=value,
            source=source,
            turn=turn,
            confidence=confidence,
            extraction_method=extraction_method,
            timestamp=datetime.now()
        )
        self._update_completeness()
        return True

    def get_field(self, section: str, field_name: str) -> Optional[FieldEntry]:
        """Get field entry with metadata."""
        if section not in ["customer", "vehicle", "appointment"]:
            return None
        section_dict = getattr(self.form, section)
        return section_dict.get(field_name)

    def get_section(self, section: str) -> Dict[str, FieldEntry]:
        """Get entire section (customer/vehicle/appointment)."""
        if section not in ["customer", "vehicle", "appointment"]:
            return {}
        return getattr(self.form, section)

    def get_all_fields(self) -> Dict:
        """Get all fields across all sections."""
        return {
            "customer": dict(self.form.customer),
            "vehicle": dict(self.form.vehicle),
            "appointment": dict(self.form.appointment),
            "metadata": self.form.metadata
        }

    def update_field(self, section: str, field_name: str, new_value: Any) -> bool:
        """Update existing field value (keeps original metadata)."""
        existing = self.get_field(section, field_name)
        if not existing:
            return False

        section_dict = getattr(self.form, section)
        section_dict[field_name].value = new_value
        section_dict[field_name].timestamp = datetime.now()
        self._update_completeness()
        return True

    def delete_field(self, section: str, field_name: str) -> bool:
        """Remove field from scratchpad."""
        if section not in ["customer", "vehicle", "appointment"]:
            return False
        section_dict = getattr(self.form, section)
        if field_name in section_dict:
            del section_dict[field_name]
            self._update_completeness()
            return True
        return False

    def clear_section(self, section: str) -> bool:
        """Clear all fields in a section."""
        if section not in ["customer", "vehicle", "appointment"]:
            return False
        getattr(self.form, section).clear()
        self._update_completeness()
        return True

    def clear_all(self) -> None:
        """Clear entire scratchpad."""
        self.form.customer.clear()
        self.form.vehicle.clear()
        self.form.appointment.clear()
        self._update_metadata()

    def _update_metadata(self) -> None:
        """Update metadata (conversation_id, timestamps, etc.)."""
        self.form.metadata = {
            "conversation_id": self.conversation_id,
            "created_at": self.created_at.isoformat(),
            "last_updated": datetime.now().isoformat(),
            "data_completeness": self._calculate_completeness()
        }

    def _update_completeness(self) -> None:
        """Recalculate and update data completeness percentage."""
        self.form.metadata["data_completeness"] = self._calculate_completeness()
        self.form.metadata["last_updated"] = datetime.now().isoformat()

    def _calculate_completeness(self) -> float:
        """Calculate % of fields filled (total possible: 13)."""
        total_fields = 13  # 4 customer + 5 vehicle + 4 appointment
        filled = sum(
            len([v for v in getattr(self.form, section).values() if v.value is not None])
            for section in ["customer", "vehicle", "appointment"]
        )
        return round((filled / total_fields) * 100, 1)

    def get_completeness(self) -> float:
        """Get current data completeness percentage."""
        return self.form.metadata.get("data_completeness", 0.0)

    def is_complete(self, required_fields: Optional[Dict[str, list]] = None) -> bool:
        """Check if required fields are present."""
        if not required_fields:
            required_fields = {
                "customer": ["first_name", "phone"],
                "vehicle": ["brand", "model"],
                "appointment": ["date", "service_type"]
            }

        for section, fields in required_fields.items():
            section_dict = getattr(self.form, section)
            for field in fields:
                if field not in section_dict or section_dict[field].value is None:
                    return False
        return True

    def export_json(self) -> str:
        """Export scratchpad as JSON."""
        data = {
            "conversation_id": self.conversation_id,
            "created_at": self.created_at.isoformat(),
            "metadata": self.form.metadata,
            "customer": {k: v.model_dump() for k, v in self.form.customer.items()},
            "vehicle": {k: v.model_dump() for k, v in self.form.vehicle.items()},
            "appointment": {k: v.model_dump() for k, v in self.form.appointment.items()}
        }
        return json.dumps(data, default=str)

    def __repr__(self) -> str:
        completeness = self.get_completeness()
        return f"ScratchpadManager(conversation_id={self.conversation_id}, completeness={completeness}%)"