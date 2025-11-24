"""
Event ordering and version validation utilities.

Validates bug reports and events against current code version.
"""

from typing import Tuple, List

from src.events.event import Event
from src.events.vector_clock import VectorClock


class EventOrdering:
    """
    Event ordering and version validation.

    Passing criteria:
    - is_report_valid_for_current_code() rejects stale reports
    - 3-layer validation: code_version, vector_clock, sequence_number
    - Accepts valid reports (same version, causal precedence)
    - Rejects invalid reports (old version, concurrent/future clocks)
    """

    @staticmethod
    def is_report_valid_for_current_code(
        bug_report: Event,
        current_code_event: Event
    ) -> Tuple[bool, str]:
        """
        Validate if bug report is for current code version.

        Returns (is_valid, reason).

        3-layer validation:
        1. Code version must match exactly
        2. Bug report must happen-after code generation (vector clock)
        3. Bug report sequence > code generation sequence
        """

        # Layer 1: Code version check
        if bug_report.code_version != current_code_event.code_version:
            return (
                False,
                f"Stale version: report={bug_report.code_version}, "
                f"current={current_code_event.code_version}"
            )

        # Layer 2: Vector clock causality
        # Bug report should happen-after code generation
        if not VectorClock.happens_before(
            current_code_event.vector_clock,
            bug_report.vector_clock
        ):
            # Check if concurrent
            if VectorClock.concurrent(
                current_code_event.vector_clock,
                bug_report.vector_clock
            ):
                return (False, "Concurrent: report and code from different branches")
            else:
                # Bug report happens-before code (invalid - future report)
                return (False, "Future: bug report predates code generation")

        # Layer 3: Sequence number check (global ordering)
        if bug_report.sequence_number <= current_code_event.sequence_number:
            return (
                False,
                f"Out of order: report seq={bug_report.sequence_number}, "
                f"code seq={current_code_event.sequence_number}"
            )

        return (True, "Valid: report is for current code")

    @staticmethod
    def sort_events_causal(events: List[Event]) -> List[Event]:
        """
        Sort events by sequence number (total order).

        Sequence numbers provide a global total order that respects causality.
        """
        return sorted(events, key=lambda e: e.sequence_number)

    @staticmethod
    def find_causal_chain(
        start_event: Event,
        all_events: List[Event]
    ) -> List[Event]:
        """
        Find all events in the causal chain starting from start_event.

        Returns events where start_event → event (causally precedes).
        """
        causal_chain = []

        for event in all_events:
            if event.event_id == start_event.event_id:
                causal_chain.append(event)
            elif VectorClock.happens_before(
                start_event.vector_clock,
                event.vector_clock
            ):
                causal_chain.append(event)

        return EventOrdering.sort_events_causal(causal_chain)

    @staticmethod
    def find_concurrent_events(
        reference_event: Event,
        all_events: List[Event]
    ) -> List[Event]:
        """
        Find all events concurrent with reference_event.

        Returns events with no causal relationship to reference.
        """
        concurrent = []

        for event in all_events:
            if event.event_id == reference_event.event_id:
                continue
            if VectorClock.concurrent(
                reference_event.vector_clock,
                event.vector_clock
            ):
                concurrent.append(event)

        return concurrent
