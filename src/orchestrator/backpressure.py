"""
Backpressure monitoring for task orchestrator.

Monitors queue fill level and emits alerts when thresholds are exceeded.
"""

import asyncio
from typing import Optional, Callable
from datetime import datetime, timedelta
from enum import Enum


class AlertLevel(Enum):
    """Alert severity levels"""
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    CLEARED = "CLEARED"


class BackpressureMonitor:
    """
    Monitor queue backpressure and emit alerts.

    Passing criteria:
    - Alerts when queue ≥80% full
    - CRITICAL alert when queue =100% full
    - No false positives (queue <80%)
    - Debounces alerts (1 second minimum between same alert)
    """

    def __init__(
        self,
        warning_threshold: float = 0.8,
        critical_threshold: float = 1.0,
        debounce_seconds: float = 1.0
    ):
        """
        Initialize monitor.

        Args:
            warning_threshold: Fraction of queue (0.8 = 80%)
            critical_threshold: Fraction of queue (1.0 = 100%)
            debounce_seconds: Minimum time between same alert type
        """
        self._warning_threshold = warning_threshold
        self._critical_threshold = critical_threshold
        self._debounce_seconds = debounce_seconds

        self._last_alert: Optional[AlertLevel] = None
        self._last_alert_time: Optional[datetime] = None
        self._alert_callback: Optional[Callable] = None

    def set_alert_callback(self, callback: Callable[[AlertLevel, float], None]):
        """Set callback for alerts (callback receives AlertLevel and fill_ratio)"""
        self._alert_callback = callback

    def check_backpressure(self, queued: int, max_queued: int):
        """
        Check queue fill level and emit alerts if needed.

        Args:
            queued: Current number of queued tasks
            max_queued: Maximum queue capacity
        """
        if max_queued == 0:
            return  # Avoid division by zero

        fill_ratio = queued / max_queued
        current_alert = self._determine_alert_level(fill_ratio)

        # Check if we should emit alert (debounce)
        if self._should_emit_alert(current_alert):
            self._emit_alert(current_alert, fill_ratio)
            self._last_alert = current_alert
            self._last_alert_time = datetime.now()

    def _determine_alert_level(self, fill_ratio: float) -> Optional[AlertLevel]:
        """Determine alert level based on fill ratio"""
        if fill_ratio >= self._critical_threshold:
            return AlertLevel.CRITICAL
        elif fill_ratio >= self._warning_threshold:
            return AlertLevel.WARNING
        else:
            # Queue below warning threshold
            if self._last_alert is not None:
                return AlertLevel.CLEARED
            return None

    def _should_emit_alert(self, current_alert: Optional[AlertLevel]) -> bool:
        """Check if alert should be emitted (debouncing logic)"""
        if current_alert is None:
            return False

        # Always emit CRITICAL alerts
        if current_alert == AlertLevel.CRITICAL:
            return True

        # Emit if alert level changed
        if current_alert != self._last_alert:
            return True

        # Debounce: don't emit same alert within debounce period
        if self._last_alert_time is not None:
            time_since_last = datetime.now() - self._last_alert_time
            if time_since_last < timedelta(seconds=self._debounce_seconds):
                return False

        return True

    def _emit_alert(self, alert_level: AlertLevel, fill_ratio: float):
        """Emit alert via callback"""
        if self._alert_callback:
            self._alert_callback(alert_level, fill_ratio)

    def reset(self):
        """Reset alert state"""
        self._last_alert = None
        self._last_alert_time = None
