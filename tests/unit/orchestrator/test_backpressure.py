"""
Tests for BackpressureMonitor.

Tests alert thresholds, debouncing, and edge cases.
"""

import pytest
import asyncio
from src.orchestrator.backpressure import BackpressureMonitor, AlertLevel


class TestAlertThresholds:
    """Test alert threshold detection"""

    def test_no_alert_below_threshold(self):
        """✅ PASS: No alert when queue <80% full"""
        monitor = BackpressureMonitor(warning_threshold=0.8, critical_threshold=1.0)
        alerts = []

        monitor.set_alert_callback(lambda level, ratio: alerts.append((level, ratio)))

        # 70% full - no alert
        monitor.check_backpressure(queued=70, max_queued=100)

        assert len(alerts) == 0

    def test_warning_at_80_percent(self):
        """✅ PASS: WARNING alert when queue ≥80% full"""
        monitor = BackpressureMonitor(warning_threshold=0.8, critical_threshold=1.0)
        alerts = []

        monitor.set_alert_callback(lambda level, ratio: alerts.append((level, ratio)))

        # 80% full - warning
        monitor.check_backpressure(queued=80, max_queued=100)

        assert len(alerts) == 1
        assert alerts[0][0] == AlertLevel.WARNING
        assert alerts[0][1] == 0.8

    def test_critical_at_100_percent(self):
        """✅ PASS: CRITICAL alert when queue =100% full"""
        monitor = BackpressureMonitor(warning_threshold=0.8, critical_threshold=1.0)
        alerts = []

        monitor.set_alert_callback(lambda level, ratio: alerts.append((level, ratio)))

        # 100% full - critical
        monitor.check_backpressure(queued=100, max_queued=100)

        assert len(alerts) == 1
        assert alerts[0][0] == AlertLevel.CRITICAL
        assert alerts[0][1] == 1.0

    def test_cleared_when_drops_below_threshold(self):
        """✅ PASS: CLEARED alert when queue drops below threshold"""
        monitor = BackpressureMonitor(warning_threshold=0.8, critical_threshold=1.0)
        alerts = []

        monitor.set_alert_callback(lambda level, ratio: alerts.append((level, ratio)))

        # First trigger warning
        monitor.check_backpressure(queued=80, max_queued=100)
        assert len(alerts) == 1
        assert alerts[0][0] == AlertLevel.WARNING

        # Then drop below threshold
        monitor.check_backpressure(queued=70, max_queued=100)
        assert len(alerts) == 2
        assert alerts[1][0] == AlertLevel.CLEARED


class TestDebouncing:
    """Test alert debouncing logic"""

    def test_debounce_prevents_spam(self):
        """✅ PASS: Same alert not emitted within debounce period"""
        monitor = BackpressureMonitor(
            warning_threshold=0.8,
            critical_threshold=1.0,
            debounce_seconds=1.0
        )
        alerts = []

        monitor.set_alert_callback(lambda level, ratio: alerts.append((level, ratio)))

        # First warning
        monitor.check_backpressure(queued=80, max_queued=100)
        assert len(alerts) == 1

        # Immediate re-check - should be debounced
        monitor.check_backpressure(queued=85, max_queued=100)
        assert len(alerts) == 1  # Still only 1 alert

    def test_critical_always_emits(self):
        """✅ PASS: CRITICAL alerts always emit (not debounced)"""
        monitor = BackpressureMonitor(
            warning_threshold=0.8,
            critical_threshold=1.0,
            debounce_seconds=1.0
        )
        alerts = []

        monitor.set_alert_callback(lambda level, ratio: alerts.append((level, ratio)))

        # First critical
        monitor.check_backpressure(queued=100, max_queued=100)
        assert len(alerts) == 1

        # Immediate re-check - should still emit (CRITICAL overrides debounce)
        monitor.check_backpressure(queued=100, max_queued=100)
        assert len(alerts) == 2  # CRITICAL always emits

    def test_level_change_emits_immediately(self):
        """✅ PASS: Alert level change emits immediately (ignores debounce)"""
        monitor = BackpressureMonitor(
            warning_threshold=0.8,
            critical_threshold=1.0,
            debounce_seconds=1.0
        )
        alerts = []

        monitor.set_alert_callback(lambda level, ratio: alerts.append((level, ratio)))

        # Warning
        monitor.check_backpressure(queued=80, max_queued=100)
        assert len(alerts) == 1
        assert alerts[0][0] == AlertLevel.WARNING

        # Immediate escalation to CRITICAL - should emit
        monitor.check_backpressure(queued=100, max_queued=100)
        assert len(alerts) == 2
        assert alerts[1][0] == AlertLevel.CRITICAL


class TestEdgeCases:
    """Test edge cases"""

    def test_zero_max_queued(self):
        """✅ PASS: max_queued=0 doesn't crash"""
        monitor = BackpressureMonitor()
        alerts = []

        monitor.set_alert_callback(lambda level, ratio: alerts.append((level, ratio)))

        # Should handle gracefully
        monitor.check_backpressure(queued=0, max_queued=0)

        assert len(alerts) == 0  # No division by zero

    def test_reset_clears_state(self):
        """✅ PASS: reset() clears alert state"""
        monitor = BackpressureMonitor(warning_threshold=0.8)
        alerts = []

        monitor.set_alert_callback(lambda level, ratio: alerts.append((level, ratio)))

        # Trigger warning
        monitor.check_backpressure(queued=80, max_queued=100)
        assert len(alerts) == 1

        # Reset
        monitor.reset()

        # Same condition should trigger again (state cleared)
        monitor.check_backpressure(queued=80, max_queued=100)
        assert len(alerts) == 2  # New alert after reset

    def test_no_callback_no_crash(self):
        """✅ PASS: Alerts without callback don't crash"""
        monitor = BackpressureMonitor()

        # No callback set - should not crash
        monitor.check_backpressure(queued=100, max_queued=100)

    def test_custom_thresholds(self):
        """✅ PASS: Custom thresholds work correctly"""
        monitor = BackpressureMonitor(warning_threshold=0.5, critical_threshold=0.9)
        alerts = []

        monitor.set_alert_callback(lambda level, ratio: alerts.append((level, ratio)))

        # 50% - warning
        monitor.check_backpressure(queued=50, max_queued=100)
        assert len(alerts) == 1
        assert alerts[0][0] == AlertLevel.WARNING

        # 90% - critical
        monitor.check_backpressure(queued=90, max_queued=100)
        assert len(alerts) == 2
        assert alerts[1][0] == AlertLevel.CRITICAL


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
