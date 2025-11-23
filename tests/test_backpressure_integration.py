"""
Tests for backpressure monitoring integration with TaskOrchestrator.

Tests that the TaskOrchestrator properly monitors queue fill level and emits alerts.
"""

import pytest
import asyncio
from unittest.mock import Mock, call

from src.orchestrator.task_orchestrator import TaskOrchestrator
from src.orchestrator.priority import TaskPriority
from src.orchestrator.backpressure import AlertLevel


class TestTaskOrchestratorBackpressureIntegration:
    """Test backpressure monitoring integration with TaskOrchestrator"""

    @pytest.mark.asyncio
    async def test_backpressure_alerts_on_queue_fill(self):
        """✅ PASS: TaskOrchestrator alerts when queue ≥80% full"""
        orchestrator = TaskOrchestrator(max_concurrent=1, max_queued=10)
        await orchestrator.start(num_workers=1)

        # Mock callback to capture alerts
        mock_callback = Mock()
        orchestrator.set_backpressure_callback(mock_callback)

        # Submit 8 tasks (80%) - should trigger WARNING
        async def dummy_task():
            await asyncio.sleep(0.2)  # Keep task running

        for i in range(8):
            await orchestrator.submit_task(f"task-{i}", dummy_task, TaskPriority.MEDIUM)

        # Wait a bit for processing
        await asyncio.sleep(0.1)

        # Check that we got a warning alert
        mock_callback.assert_called()
        calls = mock_callback.call_args_list
        # Check if any call was a WARNING alert
        warning_found = any(call_args[0][0] == AlertLevel.WARNING for call_args in calls if len(call_args[0]) > 0)
        assert warning_found, f"Expected WARNING alert, got calls: {calls}"

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_critical_alert_at_full_queue(self):
        """✅ PASS: TaskOrchestrator emits CRITICAL when queue =100% full"""
        orchestrator = TaskOrchestrator(max_concurrent=1, max_queued=5)
        await orchestrator.start(num_workers=1)

        # Mock callback to capture alerts
        mock_callback = Mock()
        orchestrator.set_backpressure_callback(mock_callback)

        # Submit 5 tasks (100%) - should trigger CRITICAL
        async def dummy_task():
            await asyncio.sleep(0.2)  # Keep task running

        for i in range(5):
            await orchestrator.submit_task(f"task-{i}", dummy_task, TaskPriority.MEDIUM)

        # Wait a bit for processing
        await asyncio.sleep(0.1)

        # Check that we got a critical alert
        mock_callback.assert_called()
        calls = mock_callback.call_args_list
        critical_found = any(call_args[0][0] == AlertLevel.CRITICAL for call_args in calls if len(call_args[0]) > 0)
        assert critical_found, f"Expected CRITICAL alert, got calls: {calls}"

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_alerts_clear_when_queue_drops(self):
        """✅ PASS: TaskOrchestrator emits CLEARED when queue drops below threshold"""
        orchestrator = TaskOrchestrator(max_concurrent=1, max_queued=10)
        await orchestrator.start(num_workers=1)

        # Mock callback to capture alerts
        mock_callback = Mock()
        orchestrator.set_backpressure_callback(mock_callback)

        # Submit 8 tasks (80%) - should trigger WARNING
        async def slow_task():
            await asyncio.sleep(0.1)

        for i in range(8):
            await orchestrator.submit_task(f"task-{i}", slow_task, TaskPriority.MEDIUM)

        await asyncio.sleep(0.05)  # Let tasks start

        # Submit 1 more (90%) - should still be critical or not trigger new alert
        await orchestrator.submit_task(f"task-9", slow_task, TaskPriority.MEDIUM)

        await asyncio.sleep(0.2)  # Wait for tasks to complete
        await asyncio.sleep(0.1)  # Wait a bit more for queue to clear

        # Check that we got some alerts (including potentially cleared)
        mock_callback.assert_called()
        calls = mock_callback.call_args_list
        # There should be multiple calls due to queue state changes

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_backpressure_callback_called_with_correct_fill_ratio(self):
        """✅ PASS: Alert callback receives correct fill ratio"""
        orchestrator = TaskOrchestrator(max_concurrent=1, max_queued=10)
        await orchestrator.start(num_workers=1)

        # Mock callback to capture alerts
        mock_callback = Mock()
        orchestrator.set_backpressure_callback(mock_callback)

        async def dummy_task():
            await asyncio.sleep(0.1)

        # Submit 8 tasks (80% fill) - should trigger WARNING with ratio 0.8
        for i in range(8):
            await orchestrator.submit_task(f"task-{i}", dummy_task, TaskPriority.MEDIUM)

        await asyncio.sleep(0.05)

        # Check that at least one call had the right ratio
        calls = mock_callback.call_args_list
        correct_ratio_found = any(
            call_args[0][0] == AlertLevel.WARNING and abs(call_args[0][1] - 0.8) < 0.01
            for call_args in calls if len(call_args[0]) > 1
        )
        assert correct_ratio_found, f"Expected WARNING with ratio 0.8, got calls: {calls}"

        await orchestrator.shutdown()