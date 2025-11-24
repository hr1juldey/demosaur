"""
Event summary helper methods.

Contains additional methods for event summarization that were in the original file.
"""

from typing import List
from src.events.event import Event


def build_recent_events_section(events: List[Event]) -> str:
    """
    Build section for recent events in full detail.
    """
    if not events:
        return ""

    lines = ["# Recent Events (Full Detail)"]
    for event in events:
        lines.append(f"## Event #{event.sequence_number}: {event.event_type.value}")
        lines.append(f"Time: {event.timestamp}")
        lines.append(f"Code Version: {event.code_version}")

        # Format data nicely
        for key, value in event.data.items():
            lines.append(f"{key.title()}: {value}")
        lines.append("")  # Blank line between events

    return "\n".join(lines)


def build_compressed_events_section(events: List[Event]) -> str:
    """
    Build compressed section for older events.
    """
    if not events:
        return ""

    lines = ["# Older Events (Compressed)"]
    for event in events:
        # Only include essential info for older events
        summary_line = f"Event #{event.sequence_number}: {event.event_type.value} (v{event.code_version})"
        # Limit data fields for compression
        data_items = list(event.data.items())[:2]  # Take only first 2 data items
        data_summary = ", ".join(f"{k}={v}" for k, v in data_items)
        if data_summary:
            summary_line += f" - {data_summary}"

        lines.append(f"- {summary_line}")

    return "\n".join(lines)