"""
Immutable event dataclass.

Source of truth for all system state changes.
"""

import uuid
import re
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from src.events.event_types import EventType


def _validate_task_id(task_id: str) -> str:
    """Validate and sanitize task_id"""
    if not task_id or not isinstance(task_id, str):
        raise ValueError("task_id must be non-empty string")

    # Sanitize special characters
    sanitized = re.sub(r'[^\w\-]', '_', task_id)

    if len(sanitized) > 255:
        raise ValueError("task_id too long (max 255 chars)")

    return sanitized


def _validate_timestamp(ts: str) -> None:
    """Validate ISO 8601 timestamp"""
    try:
        parsed = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        # Reject future timestamps (with 1 minute tolerance)
        now = datetime.now(timezone.utc)
        if parsed > now:
            if (parsed - now).total_seconds() > 60:
                raise ValueError("Timestamp is in the future")
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid ISO 8601 timestamp: {e}")


@dataclass(frozen=True)
class Event:
    """
    Immutable event - single source of truth.

    Passing criteria:
    - Event is immutable (frozen=True)
    - event_id is valid UUID format
    - task_id is non-empty string
    - timestamp is valid ISO 8601
    - sequence_number >= 0
    - code_version >= 0
    """

    event_id: str
    task_id: str
    event_type: EventType
    timestamp: str
    sequence_number: int
    vector_clock: Dict[str, int]
    causation_id: Optional[str]
    correlation_id: str
    data: Dict[str, Any]
    code_version: int

    def __post_init__(self):
        """Validate event fields"""
        # Validate event_id is UUID format
        try:
            uuid.UUID(self.event_id)
        except (ValueError, AttributeError):
            raise ValueError(f"event_id must be valid UUID, got: {self.event_id}")

        # Validate and sanitize task_id
        sanitized = _validate_task_id(self.task_id)
        if sanitized != self.task_id:
            # Use object.__setattr__ since dataclass is frozen
            object.__setattr__(self, 'task_id', sanitized)

        # Validate timestamp
        _validate_timestamp(self.timestamp)

        # Validate sequence_number
        if not isinstance(self.sequence_number, int) or self.sequence_number < 0:
            raise ValueError(f"sequence_number must be >= 0, got: {self.sequence_number}")

        # Validate vector_clock
        if not isinstance(self.vector_clock, dict):
            raise ValueError("vector_clock must be Dict[str, int]")

        for k, v in self.vector_clock.items():
            if not isinstance(k, str) or not isinstance(v, int):
                raise ValueError("vector_clock must be Dict[str, int]")

        # Validate code_version
        if not isinstance(self.code_version, int) or self.code_version < 0:
            raise ValueError(f"code_version must be >= 0, got: {self.code_version}")

        # Validate data is serializable (basic check)
        if not isinstance(self.data, dict):
            raise ValueError("data must be dict")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        result['event_type'] = self.event_type.value
        return result

    @classmethod
    def create(
        cls,
        task_id: str,
        event_type: EventType,
        data: Dict[str, Any],
        code_version: int,
        vector_clock: Dict[str, int],
        causation_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> 'Event':
        """Factory method to create event with auto-generated fields"""
        return cls(
            event_id=str(uuid.uuid4()),
            task_id=task_id,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            sequence_number=0,  # Will be set by EventStore
            vector_clock=vector_clock.copy(),
            causation_id=causation_id,
            correlation_id=correlation_id or str(uuid.uuid4()),
            data=data.copy(),
            code_version=code_version
        )
