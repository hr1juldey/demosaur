"""
Tests for VectorClock implementation.

Tests causality tracking, clock merging, and concurrency detection.
"""

import pytest
from src.events.vector_clock import VectorClock


class TestVectorClockBasics:
    """Test basic vector clock operations"""

    def test_init_empty_clock(self):
        """✅ PASS: Empty clock initializes correctly"""
        vc = VectorClock()
        assert vc.get_clock() == {}

    def test_init_with_clock(self):
        """✅ PASS: Initialize with existing clock"""
        vc = VectorClock({"p1": 5, "p2": 3})
        assert vc.get_clock() == {"p1": 5, "p2": 3}

    def test_tick_increments(self):
        """✅ PASS: tick() increments process counter by exactly 1"""
        vc = VectorClock()
        clock1 = vc.tick("p1")
        assert clock1["p1"] == 1

        clock2 = vc.tick("p1")
        assert clock2["p1"] == 2

    def test_tick_multiple_processes(self):
        """✅ PASS: tick() handles multiple processes independently"""
        vc = VectorClock()
        vc.tick("p1")
        vc.tick("p2")
        vc.tick("p1")

        clock = vc.get_clock()
        assert clock["p1"] == 2
        assert clock["p2"] == 1

    def test_merge_takes_max(self):
        """✅ PASS: merge() takes max of each process value"""
        vc = VectorClock({"p1": 5, "p2": 2})
        merged = vc.merge({"p1": 3, "p2": 8, "p3": 1})

        assert merged["p1"] == 5  # max(5, 3)
        assert merged["p2"] == 8  # max(2, 8)
        assert merged["p3"] == 1  # new process


class TestVectorClockValidation:
    """Test validation and error handling"""

    def test_reject_negative_values_init(self):
        """❌ FAIL: Negative values should raise ValueError"""
        with pytest.raises(ValueError, match="clock value must be >= 0"):
            VectorClock({"p1": -1})

    def test_reject_negative_values_merge(self):
        """❌ FAIL: Negative values in merge should raise ValueError"""
        vc = VectorClock({"p1": 5})
        with pytest.raises(ValueError, match="clock value must be >= 0"):
            vc.merge({"p1": -1})

    def test_reject_invalid_process_id(self):
        """❌ FAIL: Non-string process_id should raise ValueError"""
        with pytest.raises(ValueError, match="process_id must be str"):
            VectorClock({123: 5})  # type: ignore

    def test_reject_empty_process_id(self):
        """❌ FAIL: Empty process_id should raise ValueError"""
        vc = VectorClock()
        with pytest.raises(ValueError, match="non-empty string"):
            vc.tick("")


class TestHappensBefore:
    """Test happens-before causality detection"""

    def test_empty_vs_empty(self):
        """✅ PASS: {} vs {} → False (equal, not happens-before)"""
        assert VectorClock.happens_before({}, {}) is False

    def test_empty_vs_nonempty(self):
        """✅ PASS: {} vs {"p1": 1} → True (empty happens before non-empty)"""
        assert VectorClock.happens_before({}, {"p1": 1}) is True

    def test_nonempty_vs_empty(self):
        """✅ PASS: {"p1": 1} vs {} → False (non-empty cannot happen before empty)"""
        assert VectorClock.happens_before({"p1": 1}, {}) is False

    def test_single_process_precedence(self):
        """✅ PASS: {"p1": 3} → {"p1": 5} (single process causality)"""
        assert VectorClock.happens_before({"p1": 3}, {"p1": 5}) is True

    def test_single_process_no_precedence(self):
        """✅ PASS: {"p1": 5} does not happen before {"p1": 3}"""
        assert VectorClock.happens_before({"p1": 5}, {"p1": 3}) is False

    def test_subset_relation(self):
        """✅ PASS: {"p1": 1} → {"p1": 1, "p2": 1} (subset happens before)"""
        assert VectorClock.happens_before({"p1": 1}, {"p1": 1, "p2": 1}) is True

    def test_disjoint_processes(self):
        """✅ PASS: {"p1": 1} vs {"p2": 1} → False (concurrent)"""
        # Neither happens-before the other
        assert VectorClock.happens_before({"p1": 1}, {"p2": 1}) is False

    def test_equal_clocks(self):
        """✅ PASS: {"p1": 5, "p2": 3} vs {"p1": 5, "p2": 3} → False (equal)"""
        clock1 = {"p1": 5, "p2": 3}
        clock2 = {"p1": 5, "p2": 3}
        assert VectorClock.happens_before(clock1, clock2) is False


class TestConcurrency:
    """Test concurrent event detection"""

    def test_concurrent_equal_clocks(self):
        """✅ PASS: Equal clocks are concurrent"""
        assert VectorClock.concurrent({"p1": 5}, {"p1": 5}) is True

    def test_concurrent_disjoint_processes(self):
        """✅ PASS: {"p1": 1} vs {"p2": 1} → concurrent"""
        assert VectorClock.concurrent({"p1": 1}, {"p2": 1}) is True

    def test_not_concurrent_when_happens_before(self):
        """✅ PASS: {"p1": 1} → {"p1": 2} are not concurrent"""
        assert VectorClock.concurrent({"p1": 1}, {"p1": 2}) is False

    def test_concurrent_empty_clocks(self):
        """✅ PASS: {} vs {} → concurrent (both equal)"""
        assert VectorClock.concurrent({}, {}) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
