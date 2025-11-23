"""
Event sourcing system for Code Intern.

Provides event store, vector clocks, and state projections.
"""

from src.events.event import Event
from src.events.event_types import EventType
from src.events.vector_clock import VectorClock
from src.events.event_store import EventStore
from src.events.projections import StateProjection
from src.events.ordering import EventOrdering

__all__ = [
    "Event",
    "EventType",
    "VectorClock",
    "EventStore",
    "StateProjection",
    "EventOrdering",
]
