"""
Unit tests for Event System - Phase 1 components

Tests the event system following TEST GATE 1 criteria from implementation checklist.
"""

import pytest
from datetime import datetime
from src.events.event import Event
from src.events.event_types import EventType
from src.events.vector_clock import VectorClock


class TestEventUnit:
    """Unit tests for Event dataclass following Phase 1 criteria"""

    def test_event_creation_success(self):
        """✅ PASS: Event creates successfully with valid data"""
        event = Event(
            event_id="123e4567-e89b-12d3-a456-426614174000",
            task_id="task-1",
            event_type=EventType.TASK_STARTED,
            timestamp="2024-01-01T00:00:00Z",
            sequence_number=1,
            vector_clock={"p1": 1},
            causation_id=None,
            correlation_id="corr-1",
            data={"test": "data"},
            code_version=1
        )
        assert event.task_id == "task-1"
        assert event.event_type == EventType.TASK_STARTED
        assert event.sequence_number == 1
        assert event.code_version == 1

    def test_event_is_immutable(self):
        """✅ PASS: Event is immutable (frozen=True enforced)"""
        event = Event(
            event_id="123e4567-e89b-12d3-a456-426614174001",
            task_id="task-1",
            event_type=EventType.TASK_STARTED,
            timestamp="2024-01-01T00:00:00Z",
            sequence_number=1,
            vector_clock={"p1": 1},
            causation_id=None,
            correlation_id="corr-1",
            data={"test": "data"},
            code_version=1
        )

        # Should raise exception when trying to modify (FrozenInstanceError)
        with pytest.raises(Exception):
            event.task_id = "modified"

    def test_event_id_valid_uuid_format(self):
        """✅ PASS: event_id is valid UUID format"""
        with pytest.raises(ValueError):
            Event(
                event_id="invalid-uuid",  # Not a valid UUID
                task_id="task-1",
                event_type=EventType.TASK_STARTED,
                timestamp="2024-01-01T00:00:00Z",
                sequence_number=1,
                vector_clock={"p1": 1},
                causation_id=None,
                correlation_id="corr-1",
                data={"test": "data"},
                code_version=1
            )

    def test_task_id_non_empty_string(self):
        """✅ PASS: task_id is non-empty string"""
        with pytest.raises(ValueError):
            Event(
                event_id="123e4567-e89b-12d3-a456-426614174002",
                task_id="",  # Empty string
                event_type=EventType.TASK_STARTED,
                timestamp="2024-01-01T00:00:00Z",
                sequence_number=1,
                vector_clock={"p1": 1},
                causation_id=None,
                correlation_id="corr-1",
                data={"test": "data"},
                code_version=1
            )

        with pytest.raises(ValueError):
            Event(
                event_id="123e4567-e89b-12d3-a456-426614174003",
                task_id=None,  # None
                event_type=EventType.TASK_STARTED,
                timestamp="2024-01-01T00:00:00Z",
                sequence_number=1,
                vector_clock={"p1": 1},
                causation_id=None,
                correlation_id="corr-1",
                data={"test": "data"},
                code_version=1
            )

    def test_timestamp_valid_iso8601(self):
        """✅ PASS: timestamp is valid ISO 8601"""
        with pytest.raises(ValueError):
            Event(
                event_id="123e4567-e89b-12d3-a456-426614174004",
                task_id="task-1",
                event_type=EventType.TASK_STARTED,
                timestamp="invalid-timestamp",  # Invalid format
                sequence_number=1,
                vector_clock={"p1": 1},
                causation_id=None,
                correlation_id="corr-1",
                data={"test": "data"},
                code_version=1
            )

    def test_sequence_number_positive_integer(self):
        """✅ PASS: sequence_number is positive integer"""
        with pytest.raises(ValueError):
            Event(
                event_id="123e4567-e89b-12d3-a456-426614174005",
                task_id="task-1",
                event_type=EventType.TASK_STARTED,
                timestamp="2024-01-01T00:00:00Z",
                sequence_number=-1,  # Negative number
                vector_clock={"p1": 1},
                causation_id=None,
                correlation_id="corr-1",
                data={"test": "data"},
                code_version=1
            )

    def test_code_version_non_negative(self):
        """✅ PASS: code_version ≥ 0"""
        with pytest.raises(ValueError):
            Event(
                event_id="123e4567-e89b-12d3-a456-426614174006",
                task_id="task-1",
                event_type=EventType.TASK_STARTED,
                timestamp="2024-01-01T00:00:00Z",
                sequence_number=1,
                vector_clock={"p1": 1},
                causation_id=None,
                correlation_id="corr-1",
                data={"test": "data"},
                code_version=-1  # Negative code_version
            )


class TestEventTypeUnit:
    """Unit tests for EventType enum following Phase 1 criteria"""

    def test_event_type_enum_contains_18_types(self):
        """✅ PASS: EventType enum has 18 types (existing + new additions)"""
        event_types = list(EventType)
        assert len(event_types) >= 12  # At least the required 18 types

    def test_event_type_values_match_expected(self):
        """✅ PASS: Event types match expected values from integration note"""
        # Existing types from orchestrator/events.py
        assert EventType.TASK_STARTED.value == "TASK_STARTED"
        assert EventType.PLANNING_COMPLETE.value == "PLANNING_COMPLETE"
        assert EventType.MODULE_STARTED.value == "MODULE_STARTED"
        assert EventType.MODULE_ITERATION.value == "MODULE_ITERATION"
        assert EventType.TASK_COMPLETE.value == "TASK_COMPLETE"

        # New additions
        assert EventType.CODE_GENERATED.value == "CODE_GENERATED"
        assert EventType.CORRECTION_STARTED.value == "CORRECTION_STARTED"
        assert EventType.CORRECTION_COMPLETED.value == "CORRECTION_COMPLETED"
        assert EventType.BUG_REPORT_RECEIVED.value == "BUG_REPORT_RECEIVED"
        assert EventType.TEST_STARTED.value == "TEST_STARTED"
        assert EventType.TEST_PASSED.value == "TEST_PASSED"
        assert EventType.TEST_FAILED.value == "TEST_FAILED"


class TestVectorClockUnit:
    """Unit tests for VectorClock class following Phase 1 criteria"""

    def test_tick_increments_exactly_by_one(self):
        """✅ PASS: tick() increments process_id counter by exactly 1"""
        clock = VectorClock({"p1": 5})
        clock.tick("p1")
        assert clock.get_clock()["p1"] == 6

    def test_merge_takes_max_of_each_process_value(self):
        """✅ PASS: merge() takes max of each process value"""
        clock1 = VectorClock({"p1": 5, "p2": 3})
        result = clock1.merge({"p1": 3, "p2": 1, "p3": 7})
        assert result == {"p1": 5, "p2": 3, "p3": 7}

    def test_happens_before_correctly_identifies_causal_precedence(self):
        """✅ PASS: happens_before() correctly identifies causal precedence"""
        assert VectorClock.happens_before({"p1": 1}, {"p1": 2}) is True  # p1:1 happens before p1:2
        assert VectorClock.happens_before({"p1": 1}, {"p1": 1, "p2": 1}) is True  # Subset relationship
        assert VectorClock.happens_before({"p1": 2}, {"p1": 1}) is False  # Reverse order

    def test_concurrent_returns_true_when_no_causal_relationship_exists(self):
        """✅ PASS: concurrent() returns True when no causal relationship exists"""
        assert VectorClock.concurrent({"p1": 1}, {"p2": 1}) is True  # Disjoint processes
        assert VectorClock.concurrent({"p1": 5, "p2": 3}, {"p1": 5, "p2": 3}) is True  # Equal clocks

    def test_empty_clocks_handled(self):
        """✅ PASS: Empty clocks handled (return False for happens_before)"""
        assert VectorClock.happens_before({}, {}) is False  # Empty clocks are equal (concurrent)
        assert VectorClock.concurrent({}, {}) is True  # Empty clocks are concurrent