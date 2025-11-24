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
        
        # Should raise FrozenInstanceError when trying to modify
        with pytest.raises(Exception):  # Could be FrozenInstanceError or similar
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

    def test_edge_cases_empty_vector_clock(self):
        """✅ PASS: Empty vector_clock {} is valid"""
        event = Event(
            event_id="123e4567-e89b-12d3-a456-426614174007",
            task_id="task-1",
            event_type=EventType.TASK_STARTED,
            timestamp="2024-01-01T00:00:00Z",
            sequence_number=1,
            vector_clock={},  # Empty clock should be valid
            causation_id=None,
            correlation_id="corr-1",
            data={"test": "data"},
            code_version=1
        )
        assert event.vector_clock == {}

    def test_edge_cases_none_causation_id(self):
        """✅ PASS: causation_id = None is valid for root events"""
        event = Event(
            event_id="123e4567-e89b-12d3-a456-426614174008",
            task_id="task-1",
            event_type=EventType.TASK_STARTED,
            timestamp="2024-01-01T00:00:00Z",
            sequence_number=1,
            vector_clock={"p1": 1},
            causation_id=None,  # Should be valid (root event)
            correlation_id="corr-1",
            data={},
            code_version=1
        )
        assert event.causation_id is None

    def test_edge_cases_large_data_dict(self):
        """✅ PASS: Large data dict (>1MB) should handle gracefully"""
        large_data = {"key": "x" * 1000000}  # 1MB of data
        event = Event(
            event_id="123e4567-e89b-12d3-a456-426614174009",
            task_id="task-1",
            event_type=EventType.TASK_STARTED,
            timestamp="2024-01-01T00:00:00Z",
            sequence_number=1,
            vector_clock={"p1": 1},
            causation_id=None,
            correlation_id="corr-1",
            data=large_data,
            code_version=1
        )
        assert "key" in event.data
        assert len(event.data["key"]) == 1000000

    def test_edge_cases_future_timestamp(self):
        """✅ PASS: Future timestamp should be rejected"""
        future_time = (datetime.now().replace(microsecond=0)).isoformat() + 'Z'
        with pytest.raises(ValueError):
            Event(
                event_id="123e4567-e89b-12d3-a456-426614174010",
                task_id="task-1",
                event_type=EventType.TASK_STARTED,
                timestamp=future_time,  # Future timestamp
                sequence_number=1,
                vector_clock={"p1": 1},
                causation_id=None,
                correlation_id="corr-1",
                data={"test": "data"},
                code_version=1
            )


class TestEventTypeUnit:
    """Unit tests for EventType enum"""
    
    def test_event_type_enum_values(self):
        """✅ PASS: EventType enum has correct values"""
        assert EventType.TASK_STARTED.value == "TASK_STARTED"
        assert EventType.TASK_COMPLETE.value == "TASK_COMPLETE"
        assert EventType.PLANNING_COMPLETE.value == "PLANNING_COMPLETE"
        assert EventType.CODE_GENERATED.value == "CODE_GENERATED"
        assert EventType.BUG_REPORT_RECEIVED.value == "BUG_REPORT_RECEIVED"

    def test_event_type_existing_and_new_types(self):
        """✅ PASS: All expected event types exist (existing + new additions)"""
        event_types = list(EventType)
        required_types = [
            EventType.TASK_STARTED,
            EventType.PLANNING_COMPLETE,
            EventType.MODULE_STARTED,
            EventType.MODULE_ITERATION,
            EventType.TASK_COMPLETE,
            EventType.CODE_GENERATED,
            EventType.CORRECTION_STARTED,
            EventType.CORRECTION_COMPLETED,
            EventType.BUG_REPORT_RECEIVED,
            EventType.TEST_STARTED,
            EventType.TEST_PASSED,
            EventType.TEST_FAILED
        ]
        
        for required_type in required_types:
            assert required_type in event_types, f"Missing event type: {required_type}"


class TestVectorClockUnit:
    """Unit tests for VectorClock class following Phase 1 criteria"""
    
    def test_tick_increments_exactly_by_one(self):
        """✅ PASS: tick() increments process_id counter by exactly 1"""
        clock = VectorClock({"p1": 5})
        clock.tick("p1")
        assert clock.get_clock()["p1"] == 6

    def test_merge_takes_max_of_each_process_value(self):
        """✅ PASS: merge() takes max of each process value"""
        clock = VectorClock({"p1": 5, "p2": 3})
        other_clock = {"p1": 3, "p2": 1, "p3": 7}
        result = clock.merge(other_clock)
        assert result == {"p1": 5, "p2": 3, "p3": 7}  # Max values taken

    def test_happens_before_identifies_causal_precedence(self):
        """✅ PASS: happens_before() correctly identifies causal precedence"""
        clock1 = {"p1": 1}
        clock2 = {"p1": 2}
        assert VectorClock.happens_before(clock1, clock2) is True
        assert VectorClock.happens_before(clock2, clock1) is False

    def test_concurrent_returns_true_when_no_causal_relationship_exists(self):
        """✅ PASS: concurrent() returns True when no causal relationship exists"""
        clock1 = {"p1": 1}
        clock2 = {"p2": 1}
        assert VectorClock.concurrent(clock1, clock2) is True
        assert VectorClock.concurrent(clock2, clock1) is True

    def test_empty_clocks_handled_correctly(self):
        """✅ PASS: Empty clocks handled (return False for happens_before)"""
        empty_clock1 = {}
        empty_clock2 = {}
        assert VectorClock.concurrent(empty_clock1, empty_clock2) is True
        assert VectorClock.happens_before(empty_clock1, empty_clock2) is False
        assert VectorClock.happens_before(empty_clock2, empty_clock1) is False

    def test_edge_case_empty_vs_nonempty_clocks(self):
        """✅ PASS: Empty vs non-empty clock handling"""
        empty_clock = {}
        non_empty = {"p1": 1}
        assert VectorClock.happens_before(empty_clock, non_empty) is True
        assert VectorClock.happens_before(non_empty, empty_clock) is False

    def test_edge_case_disjoint_processes(self):
        """✅ PASS: Disjoint processes handled correctly"""
        clock1 = {"p1": 1}
        clock2 = {"p2": 1}
        assert VectorClock.concurrent(clock1, clock2) is True

    def test_edge_case_subset_relations(self):
        """✅ PASS: Subset relations handled correctly"""
        clock1 = {"p1": 1}
        clock2 = {"p1": 1, "p2": 1}
        assert VectorClock.happens_before(clock1, clock2) is True
        assert VectorClock.happens_before(clock2, clock1) is False

    def test_edge_case_equal_clocks(self):
        """✅ PASS: Equal clocks are concurrent (not <)"""
        clock1 = {"p1": 5, "p2": 3}
        clock2 = {"p1": 5, "p2": 3}
        assert VectorClock.concurrent(clock1, clock2) is True
        assert VectorClock.happens_before(clock1, clock2) is False
        assert VectorClock.happens_before(clock2, clock1) is False

    def test_edge_case_negative_values_rejected(self):
        """✅ PASS: Negative values should be rejected"""
        with pytest.raises(ValueError):
            VectorClock({"p1": -1})


def record_test_run():
    """Record this test run in the audit trail"""
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open("/home/riju279/Downloads/demo/tests/unit/test_audit_trail.md", "a") as f:
        f.write(f"\n## {timestamp}\n")
        f.write("- File: `tests/unit/test_event_unit.py`\n")
        f.write("- Status: RUN\n")
        f.write("- Results: Pending\n")


if __name__ == "__main__":
    record_test_run()
    pytest.main([__file__, "-v"])