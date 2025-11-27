"""ScratchpadManager: Single source of truth for collected booking data."""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict
import json
from uuid import uuid4


class FieldEntry(BaseModel):
    """Single scraped field with metadata."""
    value: Optional[Any] = None
    source: Optional[str] = None
    turn: Optional[int] = None
    confidence: Optional[float] = None
    extraction_method: Optional[str] = None
    timestamp: Optional[datetime] = None


class ScratchpadForm(BaseModel):
    """Three-section scratchpad for booking data."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    customer: Dict[str, FieldEntry] = Field(default_factory=dict)
    vehicle: Dict[str, FieldEntry] = Field(default_factory=dict)
    appointment: Dict[str, FieldEntry] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScratchpadManager:
    """CRUD + completeness tracking for scratchpad."""

    def __init__(self, conversation_id: Optional[str] = None):
        self.form = ScratchpadForm()
        self.conversation_id = conversation_id or str(uuid4())
        self.created_at = datetime.now()
        self.form.metadata = {
            "conversation_id": self.conversation_id,
            "created_at": self.created_at.isoformat(),
            "data_completeness": 0.0
        }

    def add_field(self, section: str, field_name: str, value: Any, source: str,
                  turn: int, confidence: float = 1.0, extraction_method: str = "user") -> bool:
        """Add field with metadata."""
        if section not in ["customer", "vehicle", "appointment"]:
            return False
        getattr(self.form, section)[field_name] = FieldEntry(
            value=value, source=source, turn=turn, confidence=confidence,
            extraction_method=extraction_method, timestamp=datetime.now()
        )
        self._update_completeness()
        return True

    def get_field(self, section: str, field_name: str) -> Optional[FieldEntry]:
        """Get field entry with metadata."""
        if section not in ["customer", "vehicle", "appointment"]:
            return None
        return getattr(self.form, section).get(field_name)

    def get_section(self, section: str) -> Dict[str, FieldEntry]:
        """Get entire section."""
        if section not in ["customer", "vehicle", "appointment"]:
            return {}
        return getattr(self.form, section)

    def get_all_fields(self) -> Dict:
        """Get all fields with metadata."""
        return {
            "customer": dict(self.form.customer),
            "vehicle": dict(self.form.vehicle),
            "appointment": dict(self.form.appointment),
            "metadata": self.form.metadata
        }

    def update_field(self, section: str, field_name: str, new_value: Any) -> bool:
        """Update field value."""
        if not self.get_field(section, field_name):
            return False
        getattr(self.form, section)[field_name].value = new_value
        self._update_completeness()
        return True

    def delete_field(self, section: str, field_name: str) -> bool:
        """Remove field."""
        section_dict = getattr(self.form, section, {})
        if field_name in section_dict:
            del section_dict[field_name]
            self._update_completeness()
            return True
        return False

    def clear_all(self) -> None:
        """Clear scratchpad."""
        self.form.customer.clear()
        self.form.vehicle.clear()
        self.form.appointment.clear()
        self.form.metadata["data_completeness"] = 0.0

    def _update_completeness(self) -> None:
        """Recalculate completeness %."""
        total = 13
        filled = sum(len([v for v in getattr(self.form, s).values() if v.value])
                     for s in ["customer", "vehicle", "appointment"])
        self.form.metadata["data_completeness"] = round((filled / total) * 100, 1)

    def get_completeness(self) -> float:
        """Get completeness percentage."""
        return self.form.metadata.get("data_completeness", 0.0)

    def is_complete(self, required: Optional[Dict[str, list]] = None) -> bool:
        """Check if required fields present."""
        if not required:
            required = {"customer": ["first_name", "phone"],
                       "vehicle": ["brand", "model"],
                       "appointment": ["date", "service_type"]}
        for section, fields in required.items():
            for field in fields:
                if field not in getattr(self.form, section) or \
                   getattr(self.form, section)[field].value is None:
                    return False
        return True

    def export_json(self) -> str:
        """Export as JSON."""
        return json.dumps({
            "conversation_id": self.conversation_id,
            "created_at": self.created_at.isoformat(),
            "metadata": self.form.metadata,
            "customer": {k: v.model_dump() for k, v in self.form.customer.items()},
            "vehicle": {k: v.model_dump() for k, v in self.form.vehicle.items()},
            "appointment": {k: v.model_dump() for k, v in self.form.appointment.items()}
        }, default=str)

    def __repr__(self) -> str:
        return f"ScratchpadManager(id={self.conversation_id[:8]}..., {self.get_completeness()}%)"