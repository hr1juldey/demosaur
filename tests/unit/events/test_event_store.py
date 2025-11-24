"""
Tests for EventStore implementation.

Tests thread-safe append, persistence, and event queries.
"""

import pytest
import asyncio
import json
from pathlib import Path
from src.events.event_store import EventStore
from src.events.event import Event
from src.events.event_types import EventType


@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary storage path"""
    return tmp_path / "events.json"


@pytest.fixture
def sample_event():
    """Create a sample event"""
    return Event.create(
        task_id="test-task-1",
        event_type=EventType.TASK_STARTED,
        data={"description": "Test task"},
        code_version=1,
        vector_clock={"p1": 1}
    )


class TestEventStoreBasics:
    """Test basic event store operations"""

    @pytest.mark.asyncio
    async def test_init_empty_store(self):
        """✅ PASS: Empty store initializes correctly"""
        store = EventStore()
        events = await store.get_events()
        assert events == []

    @pytest.mark.asyncio
    async def test_append_assigns_sequence(self, sample_event):
        """✅ PASS: append() assigns sequential sequence_numbers"""
        store = EventStore()

        event1 = await store.append(sample_event)
        assert event1.sequence_number == 1

        event2 = await store.append(sample_event)
        assert event2.sequence_number == 2

        event3 = await store.append(sample_event)
        assert event3.sequence_number == 3

    @pytest.mark.asyncio
    async def test_append_preserves_event_data(self, sample_event):
        """✅ PASS: append() preserves all event fields except sequence"""
        store = EventStore()
        appended = await store.append(sample_event)

        assert appended.event_id == sample_event.event_id
        assert appended.task_id == sample_event.task_id
        assert appended.event_type == sample_event.event_type
        assert appended.data == sample_event.data
        assert appended.code_version == sample_event.code_version

    @pytest.mark.asyncio
    async def test_get_events_returns_all(self, sample_event):
        """✅ PASS: get_events() returns all appended events"""
        store = EventStore()
        await store.append(sample_event)
        await store.append(sample_event)

        events = await store.get_events()
        assert len(events) == 2


class TestEventStoreFiltering:
    """Test event filtering"""

    @pytest.mark.asyncio
    async def test_filter_by_task_id(self):
        """✅ PASS: get_events(task_id) filters correctly"""
        store = EventStore()

        event1 = Event.create(
            task_id="task-1",
            event_type=EventType.TASK_STARTED,
            data={},
            code_version=1,
            vector_clock={"p1": 1}
        )
        event2 = Event.create(
            task_id="task-2",
            event_type=EventType.TASK_STARTED,
            data={},
            code_version=1,
            vector_clock={"p1": 2}
        )

        await store.append(event1)
        await store.append(event2)

        task1_events = await store.get_events(task_id="task-1")
        assert len(task1_events) == 1
        assert task1_events[0].task_id == "task-1"

    @pytest.mark.asyncio
    async def test_filter_by_event_type(self):
        """✅ PASS: get_events(event_type) filters correctly"""
        store = EventStore()

        event1 = Event.create(
            task_id="task-1",
            event_type=EventType.TASK_STARTED,
            data={},
            code_version=1,
            vector_clock={"p1": 1}
        )
        event2 = Event.create(
            task_id="task-1",
            event_type=EventType.TASK_COMPLETE,
            data={},
            code_version=1,
            vector_clock={"p1": 2}
        )

        await store.append(event1)
        await store.append(event2)

        started_events = await store.get_events(event_type=EventType.TASK_STARTED)
        assert len(started_events) == 1
        assert started_events[0].event_type == EventType.TASK_STARTED


class TestEventStorePersistence:
    """Test file persistence"""

    @pytest.mark.asyncio
    async def test_save_creates_file(self, temp_storage, sample_event):
        """✅ PASS: save() creates JSON file"""
        store = EventStore(storage_path=temp_storage)
        await store.append(sample_event)
        await store.save()

        assert temp_storage.exists()

    @pytest.mark.asyncio
    async def test_load_restores_events(self, temp_storage):
        """✅ PASS: load() restores events from file"""
        store1 = EventStore(storage_path=temp_storage)

        event1 = Event.create(
            task_id="task-1",
            event_type=EventType.TASK_STARTED,
            data={"test": "data"},
            code_version=1,
            vector_clock={"p1": 1}
        )
        await store1.append(event1)
        await store1.save()

        # Load into new store
        store2 = EventStore(storage_path=temp_storage)
        loaded_count = await store2.load()

        assert loaded_count == 1
        events = await store2.get_events()
        assert len(events) == 1
        assert events[0].task_id == "task-1"

    @pytest.mark.asyncio
    async def test_load_nonexistent_file(self, temp_storage):
        """✅ PASS: load() handles missing file gracefully"""
        store = EventStore(storage_path=temp_storage)
        loaded_count = await store.load()
        assert loaded_count == 0

    @pytest.mark.asyncio
    async def test_load_corrupt_json(self, temp_storage):
        """✅ PASS: load() handles corrupt JSON file"""
        temp_storage.write_text("{ invalid json")

        store = EventStore(storage_path=temp_storage)
        with pytest.raises(ValueError, match="corrupt file"):
            await store.load()


class TestEventStoreConcurrency:
    """Test thread safety"""

    @pytest.mark.asyncio
    async def test_concurrent_appends(self, sample_event):
        """✅ PASS: Concurrent appends get unique sequence numbers"""
        store = EventStore()

        # Simulate 10 concurrent appends
        tasks = [store.append(sample_event) for _ in range(10)]
        appended_events = await asyncio.gather(*tasks)

        # Check all sequence numbers are unique and sequential
        sequences = [e.sequence_number for e in appended_events]
        assert sequences == list(range(1, 11))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
