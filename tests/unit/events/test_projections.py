"""
Tests for StateProjection implementation.

Tests state rebuilding from event replay.
"""

import pytest
import uuid
from src.events.event import Event
from src.events.event_types import EventType
from src.events.projections import StateProjection
from src.common.types import TaskStatus


def create_event(event_type: EventType, task_id: str = "test-task", seq: int = 1, data: dict = None):
    """Helper to create events for testing"""
    return Event(
        event_id=str(uuid.uuid4()),
        task_id=task_id,
        event_type=event_type,
        timestamp="2024-01-01T00:00:00Z",
        sequence_number=seq,
        vector_clock={"p1": seq},
        causation_id=None,
        correlation_id=str(uuid.uuid4()),
        data=data or {},
        code_version=1
    )


class TestStateProjectionBasics:
    """Test basic state rebuilding"""

    def test_rebuild_empty_events(self):
        """✅ PASS: rebuild_state([]) → None"""
        state = StateProjection.rebuild_state([])
        assert state is None

    def test_rebuild_no_task_started(self):
        """✅ PASS: No TASK_STARTED → None"""
        events = [
            create_event(EventType.TASK_COMPLETE, seq=1)
        ]
        state = StateProjection.rebuild_state(events)
        assert state is None

    def test_rebuild_from_task_started(self):
        """✅ PASS: TASK_STARTED creates initial state"""
        events = [
            create_event(EventType.TASK_STARTED, seq=1)
        ]
        state = StateProjection.rebuild_state(events)

        assert state is not None
        assert state.task_id == "test-task"
        assert state.status == TaskStatus.CREATED

    def test_rebuild_preserves_task_id(self):
        """✅ PASS: State preserves task_id from events"""
        events = [
            create_event(EventType.TASK_STARTED, task_id="my-special-task", seq=1)
        ]
        state = StateProjection.rebuild_state(events)

        assert state.task_id == "my-special-task"


class TestEventTransitions:
    """Test event type transitions"""

    def test_requirements_complete_transition(self):
        """✅ PASS: REQUIREMENTS_COMPLETE → PLANNING status"""
        events = [
            create_event(EventType.TASK_STARTED, seq=1),
            create_event(EventType.REQUIREMENTS_COMPLETE, seq=2, data={
                "requirements": {
                    "goal": "Test goal",
                    "approach": "Test approach",
                    "technologies": ["Python"],
                    "libraries": {}
                }
            })
        ]
        state = StateProjection.rebuild_state(events)

        assert state.status == TaskStatus.PLANNING
        assert state.requirements is not None

    def test_planning_complete_transition(self):
        """✅ PASS: PLANNING_COMPLETE → GENERATING status"""
        events = [
            create_event(EventType.TASK_STARTED, seq=1),
            create_event(EventType.PLANNING_COMPLETE, seq=2, data={
                "plan": {
                    "modules": [],
                    "dependencies": {},
                    "test_plan": [],
                    "performance_targets": {}
                }
            })
        ]
        state = StateProjection.rebuild_state(events)

        assert state.status == TaskStatus.GENERATING
        assert state.plan is not None

    def test_module_started_sets_current_module(self):
        """✅ PASS: MODULE_STARTED sets current_module"""
        events = [
            create_event(EventType.TASK_STARTED, seq=1),
            create_event(EventType.MODULE_STARTED, seq=2, data={
                "module_name": "calculator.py"
            })
        ]
        state = StateProjection.rebuild_state(events)

        assert state.current_module == "calculator.py"
        assert state.current_iteration == 0

    def test_module_iteration_updates_counter(self):
        """✅ PASS: MODULE_ITERATION updates current_iteration"""
        events = [
            create_event(EventType.TASK_STARTED, seq=1),
            create_event(EventType.MODULE_STARTED, seq=2, data={"module_name": "calc.py"}),
            create_event(EventType.MODULE_ITERATION, seq=3, data={"iteration": 3})
        ]
        state = StateProjection.rebuild_state(events)

        assert state.current_iteration == 3

    def test_module_complete_adds_result(self):
        """✅ PASS: MODULE_COMPLETE adds to module_results"""
        events = [
            create_event(EventType.TASK_STARTED, seq=1),
            create_event(EventType.MODULE_COMPLETE, seq=2, data={
                "module_name": "calculator.py",
                "result": {
                    "module_name": "calculator.py",
                    "code": "def add(a, b): return a + b",
                    "tests": "def test_add(): assert add(1, 2) == 3",
                    "iterations": 2,
                    "final_score": 0.95,
                    "metrics": {
                        "execution_time": 0.01,
                        "memory_peak": 10.0,
                        "cpu_usage": 5.0
                    },
                    "test_results": {
                        "total": 1,
                        "passed": 1,
                        "failed": 0,
                        "errors": [],
                        "duration": 0.01
                    },
                    "status": "success"
                }
            })
        ]
        state = StateProjection.rebuild_state(events)

        assert "calculator.py" in state.module_results
        assert state.module_results["calculator.py"].status == "success"

    def test_task_complete_transition(self):
        """✅ PASS: TASK_COMPLETE → COMPLETED status"""
        events = [
            create_event(EventType.TASK_STARTED, seq=1),
            create_event(EventType.TASK_COMPLETE, seq=2)
        ]
        state = StateProjection.rebuild_state(events)

        assert state.status == TaskStatus.COMPLETED
        assert state.current_module is None

    def test_task_failed_transition(self):
        """✅ PASS: TASK_FAILED → FAILED status, adds to error_trail"""
        events = [
            create_event(EventType.TASK_STARTED, seq=1),
            create_event(EventType.TASK_FAILED, seq=2, data={
                "error": "Test execution failed"
            })
        ]
        state = StateProjection.rebuild_state(events)

        assert state.status == TaskStatus.FAILED
        assert len(state.error_trail) == 1
        assert state.error_trail[0]["error"] == "Test execution failed"

    def test_error_event_adds_to_trail(self):
        """✅ PASS: ERROR event adds to error_trail"""
        events = [
            create_event(EventType.TASK_STARTED, seq=1),
            create_event(EventType.ERROR, seq=2, data={
                "error": "Module generation error"
            })
        ]
        state = StateProjection.rebuild_state(events)

        assert len(state.error_trail) == 1


class TestStateDeterminism:
    """Test deterministic rebuilding"""

    def test_same_events_same_state(self):
        """✅ PASS: Same events → same state (deterministic)"""
        events = [
            create_event(EventType.TASK_STARTED, seq=1),
            create_event(EventType.REQUIREMENTS_COMPLETE, seq=2, data={
                "requirements": {
                    "goal": "Test",
                    "approach": "Test approach",
                    "technologies": [],
                    "libraries": {}
                }
            }),
            create_event(EventType.PLANNING_COMPLETE, seq=3, data={
                "plan": {
                    "modules": [],
                    "dependencies": {},
                    "test_plan": [],
                    "performance_targets": {}
                }
            })
        ]

        state1 = StateProjection.rebuild_state(events)
        state2 = StateProjection.rebuild_state(events)

        assert state1.task_id == state2.task_id
        assert state1.status == state2.status
        assert state1.requirements is not None
        assert state2.requirements is not None

    def test_out_of_order_events_sorted(self):
        """✅ PASS: Out-of-order events are sorted by sequence_number"""
        events = [
            create_event(EventType.TASK_COMPLETE, seq=3),
            create_event(EventType.TASK_STARTED, seq=1),
            create_event(EventType.PLANNING_COMPLETE, seq=2, data={
                "plan": {
                    "modules": [],
                    "dependencies": {},
                    "test_plan": [],
                    "performance_targets": {}
                }
            })
        ]

        state = StateProjection.rebuild_state(events)

        assert state.status == TaskStatus.COMPLETED  # Final event applied


class TestMetadataTracking:
    """Test metadata updates"""

    def test_metadata_tracks_last_event(self):
        """✅ PASS: Metadata tracks last event info"""
        event1 = create_event(EventType.TASK_STARTED, seq=1)
        event2 = create_event(EventType.TASK_COMPLETE, seq=2)
        events = [event1, event2]

        state = StateProjection.rebuild_state(events)

        assert state.metadata["last_event_id"] == event2.event_id
        assert state.metadata["last_event_type"] == EventType.TASK_COMPLETE.value
        assert state.metadata["code_version"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
