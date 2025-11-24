"""
Tests for priority assignment system.

Tests priority mapping, preemption logic, and edge cases.
"""

import pytest
from src.orchestrator.priority import TaskPriority, TaskPriorityAssigner
from src.events.event_types import EventType


class TestPriorityLevels:
    """Test priority level definitions"""

    def test_priority_ordering(self):
        """✅ PASS: CRITICAL < HIGH < MEDIUM < LOW < BACKGROUND"""
        assert TaskPriority.CRITICAL < TaskPriority.HIGH
        assert TaskPriority.HIGH < TaskPriority.MEDIUM
        assert TaskPriority.MEDIUM < TaskPriority.LOW
        assert TaskPriority.LOW < TaskPriority.BACKGROUND

    def test_priority_values(self):
        """✅ PASS: Priority values are 0, 10, 20, 30, 40"""
        assert TaskPriority.CRITICAL == 0
        assert TaskPriority.HIGH == 10
        assert TaskPriority.MEDIUM == 20
        assert TaskPriority.LOW == 30
        assert TaskPriority.BACKGROUND == 40


class TestPriorityAssignment:
    """Test event type to priority mapping"""

    def test_user_intervention_critical(self):
        """✅ PASS: USER_INTERVENTION → CRITICAL"""
        priority = TaskPriorityAssigner.assign_priority(EventType.USER_INTERVENTION)
        assert priority == TaskPriority.CRITICAL

    def test_bug_report_critical(self):
        """✅ PASS: BUG_REPORT_RECEIVED → CRITICAL"""
        priority = TaskPriorityAssigner.assign_priority(EventType.BUG_REPORT_RECEIVED)
        assert priority == TaskPriority.CRITICAL

    def test_code_generated_high(self):
        """✅ PASS: CODE_GENERATED → HIGH"""
        priority = TaskPriorityAssigner.assign_priority(EventType.CODE_GENERATED)
        assert priority == TaskPriority.HIGH

    def test_correction_high(self):
        """✅ PASS: CORRECTION_STARTED → HIGH"""
        priority = TaskPriorityAssigner.assign_priority(EventType.CORRECTION_STARTED)
        assert priority == TaskPriority.HIGH

    def test_test_events_medium(self):
        """✅ PASS: TEST_STARTED → MEDIUM"""
        priority = TaskPriorityAssigner.assign_priority(EventType.TEST_STARTED)
        assert priority == TaskPriority.MEDIUM

    def test_module_events_medium(self):
        """✅ PASS: MODULE_STARTED → MEDIUM"""
        priority = TaskPriorityAssigner.assign_priority(EventType.MODULE_STARTED)
        assert priority == TaskPriority.MEDIUM

    def test_planning_low(self):
        """✅ PASS: PLANNING_STARTED → LOW"""
        priority = TaskPriorityAssigner.assign_priority(EventType.PLANNING_STARTED)
        assert priority == TaskPriority.LOW

    def test_task_started_background(self):
        """✅ PASS: TASK_STARTED → BACKGROUND"""
        priority = TaskPriorityAssigner.assign_priority(EventType.TASK_STARTED)
        assert priority == TaskPriority.BACKGROUND

    def test_none_event_type(self):
        """✅ PASS: None → BACKGROUND (default)"""
        priority = TaskPriorityAssigner.assign_priority(None)
        assert priority == TaskPriority.BACKGROUND


class TestPreemptionLogic:
    """Test preemption decision logic"""

    def test_preempt_critical_over_medium(self):
        """✅ PASS: CRITICAL (0) should preempt MEDIUM (20) → True (diff=20)"""
        should = TaskPriorityAssigner.should_preempt(
            TaskPriority.CRITICAL,
            TaskPriority.MEDIUM
        )
        assert should is True

    def test_no_preempt_critical_over_high(self):
        """✅ PASS: CRITICAL (0) should NOT preempt HIGH (10) → False (diff=10)"""
        should = TaskPriorityAssigner.should_preempt(
            TaskPriority.CRITICAL,
            TaskPriority.HIGH
        )
        assert should is False

    def test_preempt_high_over_background(self):
        """✅ PASS: HIGH (10) should preempt BACKGROUND (40) → True (diff=30)"""
        should = TaskPriorityAssigner.should_preempt(
            TaskPriority.HIGH,
            TaskPriority.BACKGROUND
        )
        assert should is True

    def test_no_preempt_same_priority(self):
        """✅ PASS: Same priority → False (diff=0)"""
        should = TaskPriorityAssigner.should_preempt(
            TaskPriority.MEDIUM,
            TaskPriority.MEDIUM
        )
        assert should is False

    def test_no_preempt_lower_priority(self):
        """✅ PASS: BACKGROUND (40) should NOT preempt CRITICAL (0) → False"""
        should = TaskPriorityAssigner.should_preempt(
            TaskPriority.BACKGROUND,
            TaskPriority.CRITICAL
        )
        assert should is False

    def test_exact_20_point_diff_preempts(self):
        """✅ PASS: Exactly 20 point difference → True"""
        should = TaskPriorityAssigner.should_preempt(
            TaskPriority.CRITICAL,  # 0
            TaskPriority.MEDIUM     # 20
        )
        assert should is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
