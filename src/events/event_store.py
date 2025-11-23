"""
Event store for persistent event log.

Provides thread-safe append, atomic persistence, and event queries.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import List, Optional

from src.events.event import Event
from src.events.event_types import EventType


class EventStore:
    """
    Thread-safe event store with atomic persistence.

    Passing criteria:
    - append() assigns sequential sequence_numbers (1, 2, 3, ...)
    - Concurrent appends use lock to prevent races
    - save() uses atomic write (temp file + rename)
    - load() recovers from corrupt events (logs warning, continues)
    - get_events() filters correctly by task_id, event_type, etc.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize event store"""
        self._events: List[Event] = []
        self._lock = asyncio.Lock()
        self._storage_path = storage_path
        self._next_sequence = 1

    async def append(self, event: Event) -> Event:
        """Append event with auto-assigned sequence number (thread-safe)"""
        async with self._lock:
            # Reconstruct event with new sequence number (frozen dataclass)
            new_event = Event(
                event_id=event.event_id,
                task_id=event.task_id,
                event_type=event.event_type,
                timestamp=event.timestamp,
                sequence_number=self._next_sequence,
                vector_clock=event.vector_clock.copy(),
                causation_id=event.causation_id,
                correlation_id=event.correlation_id,
                data=event.data.copy(),
                code_version=event.code_version
            )

            self._events.append(new_event)
            self._next_sequence += 1

            return new_event

    async def get_events(
        self,
        task_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        correlation_id: Optional[str] = None
    ) -> List[Event]:
        """Get events with optional filtering"""
        async with self._lock:
            events = self._events.copy()

        if task_id:
            events = [e for e in events if e.task_id == task_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if correlation_id:
            events = [e for e in events if e.correlation_id == correlation_id]

        return events

    async def save(self) -> None:
        """Save events to disk using atomic write (temp + rename)"""
        if not self._storage_path:
            return

        async with self._lock:
            events_data = [e.to_dict() for e in self._events]

        # Atomic write: temp file + rename
        temp_path = self._storage_path.with_suffix('.tmp')

        try:
            temp_path.write_text(json.dumps(events_data, indent=2))
            os.replace(temp_path, self._storage_path)  # Atomic on POSIX
        except IOError as e:
            if temp_path.exists():
                temp_path.unlink()
            raise IOError(f"EventStore save failed: {e}") from e

    async def load(self) -> int:
        """Load events from disk, return count loaded (skips corrupt events)"""
        if not self._storage_path or not self._storage_path.exists():
            return 0

        try:
            data = json.loads(self._storage_path.read_text())
        except json.JSONDecodeError as e:
            raise ValueError(f"EventStore corrupt file: {e}") from e

        loaded = 0
        async with self._lock:
            for event_dict in data:
                try:
                    event = Event(
                        event_id=event_dict['event_id'],
                        task_id=event_dict['task_id'],
                        event_type=EventType(event_dict['event_type']),
                        timestamp=event_dict['timestamp'],
                        sequence_number=event_dict['sequence_number'],
                        vector_clock=event_dict['vector_clock'],
                        causation_id=event_dict.get('causation_id'),
                        correlation_id=event_dict['correlation_id'],
                        data=event_dict['data'],
                        code_version=event_dict['code_version']
                    )
                    self._events.append(event)
                    self._next_sequence = max(self._next_sequence, event.sequence_number + 1)
                    loaded += 1
                except (KeyError, ValueError):
                    continue  # Skip corrupt event

        return loaded
