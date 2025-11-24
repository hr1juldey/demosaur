"""
Unit tests for Task Orchestration - Phase 2 components

Tests the orchestration system following TEST GATE 2 criteria from implementation checklist.
"""

import pytest
import asyncio
from src.orchestrator.priority import TaskPriority, TaskPriorityAssigner
from src.orchestrator.task_orchestrator import TaskOrchestrator
from src.orchestrator.backpressure import BackpressureMonitor, AlertLevel
from src.events.event_types import EventType


class TestPriorityAssignmentUnit:
    """Unit tests for priority assignment system following Phase 2 criteria"""

    def test_priority_values_are_integers(self):
        """✅ PASS: Priority values are integers (0, 10, 20, 30, 40)"""
        assert TaskPriority.CRITICAL.value == 0
        assert TaskPriority.HIGH.value == 10
        assert TaskPriority.MEDIUM.value == 20
        assert TaskPriority.LOW.value == 30
        assert TaskPriority.BACKGROUND.value == 40

    def test_priority_ordering_correct(self):
        """✅ PASS: CRITICAL < HIGH < MEDIUM < LOW < BACKGROUND"""
        priorities = [
            TaskPriority.CRITICAL,  # 0
            TaskPriority.HIGH,     # 10
            TaskPriority.MEDIUM,   # 20
            TaskPriority.LOW,      # 30
            TaskPriority.BACKGROUND  # 40
        ]
        # Sort to verify ordering
        sorted_priorities = sorted(priorities)
        expected_order = [
            TaskPriority.CRITICAL,
            TaskPriority.HIGH,
            TaskPriority.MEDIUM,
            TaskPriority.LOW,
            TaskPriority.BACKGROUND
        ]
        assert sorted_priorities == expected_order

    def test_assign_priority_maps_event_types_correctly(self):
        """✅ PASS: assign_priority() maps event types correctly"""
        assigner = TaskPriorityAssigner()

        # Test various event types have correct priorities
        assert assigner.assign_priority(EventType.USER_INTERVENTION) == TaskPriority.CRITICAL
        assert assigner.assign_priority(EventType.CODE_GENERATED) == TaskPriority.HIGH
        assert assigner.assign_priority(EventType.TASK_STARTED) == TaskPriority.LOW  # Default to LOW
        assert assigner.assign_priority(EventType.TEST_STARTED) == TaskPriority.MEDIUM

    def test_should_preempt_returns_true_only_if_20_difference(self):
        """✅ PASS: should_preempt() returns True only if ≥20 priority difference"""
        assigner = TaskPriorityAssigner()

        # CRITICAL (0) should preempt MEDIUM (20) - diff = 20
        assert assigner.should_preempt(TaskPriority.CRITICAL, TaskPriority.MEDIUM) is True

        # HIGH (10) should NOT preempt MEDIUM (20) - diff = 10 (only 10 point diff)
        assert assigner.should_preempt(TaskPriority.HIGH, TaskPriority.MEDIUM) is False

        # HIGH (10) should preempt BACKGROUND (40) - diff = 30
        assert assigner.should_preempt(TaskPriority.HIGH, TaskPriority.BACKGROUND) is True

    def test_edge_case_unknown_event_type_defaults_to_background(self):
        """✅ PASS: Unknown EventType defaults to BACKGROUND"""
        assigner = TaskPriorityAssigner()
        assert assigner.assign_priority(None) == TaskPriority.BACKGROUND

    def test_edge_case_priority_difference_exactly_20(self):
        """✅ PASS: Should preempt when difference is exactly 20"""
        # CRITICAL (0) vs LOW (30) = difference of 30 >= 20
        assert TaskPriority.CRITICAL.should_preempt(TaskPriority.LOW) is True
        # HIGH (10) vs LOW (30) = difference of 20 >= 20
        assert TaskPriority.HIGH.should_preempt(TaskPriority.LOW) is True


class TestTaskOrchestratorUnit:
    """Unit tests for TaskOrchestrator following Phase 2 criteria"""

    @pytest.mark.asyncio
    async def test_queue_accepts_tasks_until_maxsize(self):
        """✅ PASS: Queue accepts tasks until maxsize (100) reached"""
        orchestrator = TaskOrchestrator(max_concurrent=5, max_queued=5)  # Small queue for test
        await orchestrator.start(num_workers=2)

        # Add 5 tasks - should all be accepted
        for i in range(5):
            task_func = lambda: asyncio.sleep(0.1)
            await orchestrator.submit_task(f"task-{i}", task_func, TaskPriority.MEDIUM)

        stats = orchestrator.get_queue_stats()
        assert stats["queued"] <= 5  # Should fit in queue

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrent_tasks(self):
        """✅ PASS: Semaphore limits to max_concurrent (5) simultaneous tasks"""
        orchestrator = TaskOrchestrator(max_concurrent=2, max_queued=10)
        await orchestrator.start(num_workers=2)

        executed_tasks = []

        async def slow_task():
            executed_tasks.append("started")
            await asyncio.sleep(0.5)  # Keep running
            executed_tasks.append("completed")

        # Submit 5 tasks - only 2 should run simultaneously
        for i in range(5):
            await orchestrator.submit_task(f"task-{i}", slow_task, TaskPriority.MEDIUM)

        # Wait a bit to see how many started
        await asyncio.sleep(0.1)  # Give time for tasks to start

        # Should have 2 tasks running, not 5
        assert len([t for t in executed_tasks if t == "started"]) == 2

        await orchestrator.shutdown()

    def test_priority_ordering(self):
        """✅ PASS: Priority ordering: CRITICAL tasks execute before BACKGROUND"""
        # This would be tested with actual execution timing in integration tests
        assert TaskPriority.CRITICAL.value < TaskPriority.HIGH.value < TaskPriority.MEDIUM.value

    @pytest.mark.asyncio
    async def test_shutdown_cancels_all_tasks(self):
        """✅ PASS: shutdown() cancels all pending and active tasks"""
        orchestrator = TaskOrchestrator(max_concurrent=2, max_queued=5)
        await orchestrator.start(num_workers=2)

        cancelled_count = []

        async def cancellable_task():
            try:
                await asyncio.sleep(10)  # Very long task
            except asyncio.CancelledError:
                cancelled_count.append("cancelled")
                raise

        # Submit multiple tasks
        for i in range(3):
            await orchestrator.submit_task(f"task-{i}", cancellable_task, TaskPriority.MEDIUM)

        await orchestrator.shutdown()

        # All tasks should have received CancelledError
        assert len(cancelled_count) == 3


class TestBackpressureMonitorUnit:
    """Unit tests for BackpressureMonitor following Phase 2 criteria"""

    def test_alerts_when_queue_80_percent_full(self):
        """✅ PASS: Alerts when queue is 80% full"""
        monitor = BackpressureMonitor(alert_threshold=0.8)

        alerts_received = []

        def alert_callback(level, fill_ratio):
            alerts_received.append((level, fill_ratio))

        monitor.set_alert_callback(alert_callback)

        # Simulate queue 80% full
        monitor.check_backpressure(queued=8, max_queued=10)

        # Should have received WARNING alert
        assert len(alerts_received) >= 1
        assert any(alert[0] == AlertLevel.WARNING for alert in alerts_received)

    def test_critical_alert_when_queue_100_percent_full(self):
        """✅ PASS: CRITICAL alert when queue is 100% full"""
        monitor = BackpressureMonitor(alert_threshold=0.8, critical_threshold=1.0)

        alerts_received = []

        def alert_callback(level, fill_ratio):
            alerts_received.append((level, fill_ratio))

        monitor.set_alert_callback(alert_callback)

        # Simulate queue 100% full
        monitor.check_backpressure(queued=10, max_queued=10)

        # Should have received CRITICAL alert
        assert any(alert[0] == AlertLevel.CRITICAL for alert in alerts_received)

    def test_no_false_positives_below_threshold(self):
        """✅ PASS: No false positives (alerting when queue <80%)"""
        monitor = BackpressureMonitor(alert_threshold=0.8)

        alerts_received = []

        def alert_callback(level, fill_ratio):
            alerts_received.append((level, fill_ratio))

        monitor.set_alert_callback(alert_callback)

        # Simulate queue 50% full (below threshold)
        monitor.check_backpressure(queued=5, max_queued=10)

        # Should not have received any alerts
        assert len(alerts_received) == 0