"""
Event summarizer for building context from event history.

Compresses event sequences into token-efficient summaries while preserving key information.
"""

from typing import List
from src.events.event import Event
from src.context.tokens.manager import TokenManager


class EventSummarizer:
    """
    Summarizes event sequences for efficient context building.

    PASSING CRITERIA:
    ✅ Compression achieves ≥5x token reduction
    ✅ Summary includes key statistics and state
    ✅ Recent events preserved in full detail
    ✅ Older events compressed appropriately
    """

    def __init__(self, token_manager: TokenManager, max_summary_tokens: int = 1500):
        self.token_manager = token_manager
        self.max_summary_tokens = max_summary_tokens

    def summarize_event_history(self,
                               events: List[Event],
                               keep_recent: int = 5,
                               include_statistics: bool = True) -> str:
        """
        Summarize event history with budget management.

        Args:
            events: List of events to summarize
            keep_recent: Number of most recent events to keep in full detail
            include_statistics: Whether to include statistical summary

        Returns:
            Compressed summary within token budget
        """
        if not events:
            return "No events in history."

        # Sort events by sequence number
        sorted_events = sorted(events, key=lambda e: e.sequence_number)

        # Prepare sections
        sections = []

        if include_statistics:
            stats_summary = self._build_statistics_summary(sorted_events)
            sections.append(stats_summary)

        # Keep recent events in full detail
        if keep_recent > 0 and len(sorted_events) > keep_recent:
            recent_events = sorted_events[-keep_recent:]
            older_events = sorted_events[:-keep_recent]

            if recent_events:
                recent_section = self._build_recent_events_section(recent_events)
                sections.append(recent_section)

            if older_events:
                compressed_section = self._build_compressed_events_section(older_events)
                sections.append(compressed_section)
        else:
            # All events are recent (or few events)
            all_events_section = self._build_recent_events_section(sorted_events)
            sections.append(all_events_section)

        # Combine sections and enforce budget
        summary = "\n\n".join(sections)

        if not self.token_manager.can_fit_in_budget(summary):
            summary = self.token_manager.truncate_to_budget(summary)

        return summary

    def _build_statistics_summary(self, events: List[Event]) -> str:
        """Build statistical summary of event history."""
        if not events:
            return "# Statistics\nNo events recorded."

        # Count event types
        event_counts = {}
        for event in events:
            event_type = event.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

        # Get current code version and status
        current_version = max((e.code_version for e in events), default=0)
        latest_event = max(events, key=lambda e: e.sequence_number)

        stats = [
            "# Event Statistics",
            f"Total Events: {len(events)}",
            f"Current Code Version: {current_version}",
            f"Latest Activity: {latest_event.event_type.value}",
            "",
            "## Event Type Breakdown:"
        ]

        for event_type, count in event_counts.items():
            stats.append(f"- {event_type}: {count} events")

        return "\n".join(stats)