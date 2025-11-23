"""
State projections from event log.

Rebuild current state by replaying events in order.
"""

from typing import List, Optional

from src.events.event import Event
from src.events.event_types import EventType
from src.orchestrator.state import TaskState
from src.common.types import TaskStatus, Requirements, CodePlan, ModuleResult


class StateProjection:
    """
    Rebuild TaskState from event replay.

    Passing criteria:
    - rebuild_state() processes all EventType transitions correctly
    - State is deterministic (same events = same state)
    - Handles missing/incomplete event sequences gracefully
    - Returns None if no TASK_STARTED event found
    """

    @staticmethod
    def rebuild_state(events: List[Event]) -> Optional[TaskState]:
        """
        Rebuild TaskState by replaying events in sequence.

        Returns None if events list is empty or no TASK_STARTED.
        """
        if not events:
            return None

        # Sort by sequence_number (ensure correct order)
        sorted_events = sorted(events, key=lambda e: e.sequence_number)

        # Find TASK_STARTED
        task_started = next(
            (e for e in sorted_events if e.event_type == EventType.TASK_STARTED),
            None
        )
        if not task_started:
            return None

        # Initialize state
        state = TaskState(task_id=task_started.task_id)

        # Replay all events
        for event in sorted_events:
            StateProjection._apply_event(state, event)

        return state

    @staticmethod
    def _apply_event(state: TaskState, event: Event) -> None:
        """Apply single event to state (mutates state)"""
        if event.event_type == EventType.TASK_STARTED:
            state.status = TaskStatus.CREATED

        elif event.event_type == EventType.REQUIREMENTS_COMPLETE:
            req_data = event.data.get('requirements', {})
            if req_data:
                state.requirements = Requirements(**req_data)
            state.status = TaskStatus.PLANNING

        elif event.event_type == EventType.PLANNING_STARTED:
            state.status = TaskStatus.PLANNING

        elif event.event_type == EventType.PLANNING_COMPLETE:
            plan_data = event.data.get('plan', {})
            if plan_data:
                state.plan = CodePlan(**plan_data)
            state.status = TaskStatus.GENERATING

        elif event.event_type == EventType.MODULE_STARTED:
            state.current_module = event.data.get('module_name')
            state.current_iteration = 0

        elif event.event_type == EventType.MODULE_ITERATION:
            state.current_iteration = event.data.get('iteration', 0)

        elif event.event_type == EventType.MODULE_COMPLETE:
            module_name = event.data.get('module_name')
            result_data = event.data.get('result', {})
            if module_name and result_data:
                state.module_results[module_name] = ModuleResult(**result_data)

        elif event.event_type == EventType.TASK_COMPLETE:
            state.status = TaskStatus.COMPLETED
            state.current_module = None

        elif event.event_type == EventType.TASK_FAILED:
            state.status = TaskStatus.FAILED
            error = event.data.get('error')
            if error:
                state.error_trail.append({
                    'timestamp': event.timestamp,
                    'error': error,
                    'event_id': event.event_id
                })

        elif event.event_type == EventType.ERROR:
            error = event.data.get('error')
            if error:
                state.error_trail.append({
                    'timestamp': event.timestamp,
                    'error': error,
                    'event_id': event.event_id
                })

        # Update metadata with latest event info
        state.metadata['last_event_id'] = event.event_id
        state.metadata['last_event_type'] = event.event_type.value
        state.metadata['code_version'] = event.code_version
