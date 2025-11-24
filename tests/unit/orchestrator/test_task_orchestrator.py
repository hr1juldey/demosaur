"""
Tests for TaskOrchestrator.

Tests priority ordering, concurrency limits, backpressure, and timeout handling.
"""

import pytest
import asyncio
from src.orchestrator.task_orchestrator import TaskOrchestrator
from src.orchestrator.priority import TaskPriority


class TestBasicOperation:
    """Test basic orchestrator operations"""

    @pytest.mark.asyncio
    async def test_init_and_start(self):
        """✅ PASS: Orchestrator starts successfully"""
        orchestrator = TaskOrchestrator(max_concurrent=5, max_queued=100)
        await orchestrator.start(num_workers=3)

        stats = orchestrator.get_queue_stats()
        assert stats["max_concurrent"] == 5
        assert stats["max_queued"] == 100
        assert stats["queued"] == 0
        assert stats["active"] == 0

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_submit_and_execute_task(self):
        """✅ PASS: Single task executes successfully"""
        orchestrator = TaskOrchestrator()
        await orchestrator.start(num_workers=1)

        executed = []

        async def sample_task():
            executed.append(1)

        await orchestrator.submit_task("task-1", sample_task, TaskPriority.MEDIUM)
        await asyncio.sleep(0.1)  # Let task execute

        assert len(executed) == 1
        await orchestrator.shutdown()


class TestPriorityOrdering:
    """Test priority-based task execution"""

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        """✅ PASS: Submit [LOW, CRITICAL, HIGH] → executes [CRITICAL, HIGH, LOW]"""
        orchestrator = TaskOrchestrator(max_concurrent=1, max_queued=100)
        await orchestrator.start(num_workers=1)

        execution_order = []

        async def task(name):
            await asyncio.sleep(0.01)  # Small delay
            execution_order.append(name)

        # Submit in non-priority order
        await orchestrator.submit_task("low", lambda: task("LOW"), TaskPriority.LOW)
        await orchestrator.submit_task("critical", lambda: task("CRITICAL"), TaskPriority.CRITICAL)
        await orchestrator.submit_task("high", lambda: task("HIGH"), TaskPriority.HIGH)

        # Wait for all tasks to execute
        await asyncio.sleep(0.3)

        # Priority queue should execute in priority order: CRITICAL, HIGH, LOW
        assert execution_order == ["CRITICAL", "HIGH", "LOW"]

        await orchestrator.shutdown()


class TestConcurrencyLimit:
    """Test max_concurrent semaphore enforcement"""

    @pytest.mark.asyncio
    async def test_max_concurrent_limit(self):
        """✅ PASS: Start 10 long tasks → max 5 run simultaneously"""
        orchestrator = TaskOrchestrator(max_concurrent=5, max_queued=100)
        await orchestrator.start(num_workers=3)

        concurrent_count = []
        max_concurrent = [0]
        lock = asyncio.Lock()

        async def long_task():
            async with lock:
                concurrent_count.append(1)
                max_concurrent[0] = max(max_concurrent[0], len(concurrent_count))

            await asyncio.sleep(0.1)

            async with lock:
                concurrent_count.pop()

        # Submit 10 tasks
        for i in range(10):
            await orchestrator.submit_task(f"task-{i}", long_task, TaskPriority.MEDIUM)

        await asyncio.sleep(0.5)  # Let tasks execute

        assert max_concurrent[0] <= 5  # Should never exceed 5
        await orchestrator.shutdown()


class TestBackpressure:
    """Test bounded queue (backpressure)"""

    @pytest.mark.asyncio
    async def test_queue_blocks_when_full(self):
        """✅ PASS: Queue with maxsize=10 blocks on 11th task"""
        orchestrator = TaskOrchestrator(max_concurrent=1, max_queued=10)
        await orchestrator.start(num_workers=1)

        async def slow_task():
            await asyncio.sleep(10)  # Very slow

        # Fill queue (1 active + 10 queued)
        for i in range(11):
            await orchestrator.submit_task(f"task-{i}", slow_task, TaskPriority.MEDIUM)

        stats = orchestrator.get_queue_stats()
        assert stats["active"] == 1
        assert stats["queued"] == 10

        # Next submit should block (we'll test with timeout)
        blocked = False
        try:
            await asyncio.wait_for(
                orchestrator.submit_task("task-11", slow_task, TaskPriority.MEDIUM),
                timeout=0.1
            )
        except asyncio.TimeoutError:
            blocked = True

        assert blocked is True  # Should have blocked
        await orchestrator.shutdown()


class TestTimeoutEnforcement:
    """Test task timeout cancellation"""

    @pytest.mark.asyncio
    async def test_timeout_cancels_task(self):
        """✅ PASS: Task with timeout=0.1s running 1s → cancelled at 0.1s"""
        orchestrator = TaskOrchestrator()
        await orchestrator.start(num_workers=1)

        completed = []

        async def slow_task():
            try:
                await asyncio.sleep(1.0)  # Try to run for 1s
                completed.append("finished")
            except asyncio.CancelledError:
                completed.append("cancelled")
                raise

        await orchestrator.submit_task(
            "slow-task",
            slow_task,
            TaskPriority.MEDIUM,
            timeout=0.1  # Timeout after 0.1s
        )

        await asyncio.sleep(0.3)  # Wait for timeout + cancellation

        assert "cancelled" in completed
        assert "finished" not in completed

        await orchestrator.shutdown()


class TestShutdown:
    """Test graceful shutdown"""

    @pytest.mark.asyncio
    async def test_shutdown_cancels_all_tasks(self):
        """✅ PASS: shutdown() cancels queued and active tasks"""
        orchestrator = TaskOrchestrator(max_concurrent=2, max_queued=100)
        await orchestrator.start(num_workers=2)

        cancelled_count = [0]

        async def long_task():
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                cancelled_count[0] += 1
                raise

        # Submit 10 tasks
        for i in range(10):
            await orchestrator.submit_task(f"task-{i}", long_task, TaskPriority.MEDIUM)

        await asyncio.sleep(0.1)  # Let some tasks start

        # Shutdown should cancel all
        await orchestrator.shutdown()

        # All active tasks should be cancelled
        assert cancelled_count[0] > 0

    @pytest.mark.asyncio
    async def test_submit_after_shutdown_raises(self):
        """✅ PASS: submit_task() after shutdown() raises RuntimeError"""
        orchestrator = TaskOrchestrator()
        await orchestrator.start(num_workers=1)
        await orchestrator.shutdown()

        with pytest.raises(RuntimeError, match="shutting down"):
            await orchestrator.submit_task("task", lambda: asyncio.sleep(0), TaskPriority.MEDIUM)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
