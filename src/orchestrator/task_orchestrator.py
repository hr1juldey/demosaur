"""
Task orchestrator with priority queue and backpressure.

Manages concurrent task execution with priority ordering and bounded queues.
"""

import asyncio
from typing import Callable, Any, Dict, Optional
from dataclasses import dataclass, field

from src.orchestrator.priority import TaskPriority
from src.orchestrator.backpressure import BackpressureMonitor, AlertLevel


@dataclass(order=True)
class PrioritizedTask:
    """Task wrapper for priority queue (lower priority value = higher priority)"""
    priority: int
    task_id: str = field(compare=False)
    coro: Callable[[], Any] = field(compare=False)
    timeout: Optional[float] = field(compare=False, default=None)


class TaskOrchestrator:
    """
    Priority-based task orchestrator with backpressure.

    Passing criteria:
    - Queue blocks when maxsize reached (backpressure)
    - Semaphore limits concurrent tasks to max_concurrent
    - Priority ordering: lower priority value executes first
    - Timeout cancels long-running tasks
    - shutdown() cancels all pending and active tasks
    """

    def __init__(self, max_concurrent: int = 5, max_queued: int = 100):
        """Initialize orchestrator"""
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=max_queued)
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._workers: list[asyncio.Task] = []
        self._shutdown_flag = False
        self._active_tasks: set[asyncio.Task] = set()
        self._max_concurrent = max_concurrent
        self._max_queued = max_queued
        # Initialize backpressure monitor with default thresholds
        self._backpressure_monitor = BackpressureMonitor()
        self._alert_callback = None

    def set_backpressure_callback(self, callback: Callable[[AlertLevel, float], None]):
        """Set callback for backpressure alerts"""
        self._alert_callback = callback
        self._backpressure_monitor.set_alert_callback(callback)

    async def start(self, num_workers: int = 3):
        """Start worker pool"""
        for worker_id in range(num_workers):
            worker = asyncio.create_task(self._worker(worker_id))
            self._workers.append(worker)

    async def submit_task(
        self,
        task_id: str,
        coro: Callable[[], Any],
        priority: TaskPriority = TaskPriority.MEDIUM,
        timeout: Optional[float] = None
    ):
        """Submit task to queue (blocks if queue is full - backpressure)"""
        if self._shutdown_flag:
            raise RuntimeError("Orchestrator is shutting down")

        item = PrioritizedTask(
            priority=priority.value,
            task_id=task_id,
            coro=coro,
            timeout=timeout
        )
        await self._queue.put(item)  # Blocks if queue full
        # Check if backpressure threshold is exceeded after adding item
        self._check_backpressure()

    async def _worker(self, worker_id: int):
        """Worker that processes tasks from queue"""
        while not self._shutdown_flag:
            try:
                # Wait for task with timeout to allow checking shutdown flag
                item = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            # Check backpressure after removing an item from queue
            self._check_backpressure()

            # Acquire semaphore to limit concurrency
            async with self._semaphore:
                task = asyncio.create_task(item.coro())
                self._active_tasks.add(task)

                try:
                    if item.timeout:
                        await asyncio.wait_for(task, timeout=item.timeout)
                    else:
                        await task
                except asyncio.TimeoutError:
                    task.cancel()
                except asyncio.CancelledError:
                    raise  # Propagate cancellation
                except Exception:
                    # Log error but don't crash worker
                    pass
                finally:
                    self._active_tasks.discard(task)
                    self._queue.task_done()
                    # Check backpressure after task completion (queue might have space now)
                    self._check_backpressure()

    def _check_backpressure(self):
        """Internal method to check backpressure and emit alerts"""
        stats = self.get_queue_stats()
        self._backpressure_monitor.check_backpressure(
            queued=stats["queued"],
            max_queued=stats["max_queued"]
        )

    async def shutdown(self):
        """Gracefully shutdown orchestrator (cancel all tasks)"""
        self._shutdown_flag = True

        # Cancel all active tasks
        for task in list(self._active_tasks):
            task.cancel()

        # Cancel all workers
        for worker in self._workers:
            worker.cancel()

        # Wait for workers to finish
        await asyncio.gather(*self._workers, return_exceptions=True)

    def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics (non-blocking)"""
        return {
            "queued": self._queue.qsize(),
            "active": len(self._active_tasks),
            "max_queued": self._max_queued,
            "max_concurrent": self._max_concurrent
        }
