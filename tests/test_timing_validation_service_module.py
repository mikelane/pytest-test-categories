"""Unit tests for TimingValidationService module.

This module tests the TimingValidationService in isolation without pytest dependencies.
Uses FakeTimer for deterministic timing tests.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from pytest_test_categories.services.timing_validation import TimingValidationService
from pytest_test_categories.timers import FakeTimer
from pytest_test_categories.timing import (
    PerformanceBaselineViolationError,
    TimingViolationError,
)
from pytest_test_categories.types import (
    TestSize,
    TestTimer,
    TimerState,
)

if TYPE_CHECKING:
    from collections.abc import MutableMapping


@pytest.mark.small
class DescribeTimingValidationService:
    """Test suite for TimingValidationService."""

    def it_validates_small_test_within_limit(self) -> None:
        """Validate small test that completes within 1s limit."""
        service = TimingValidationService()

        # Should not raise exception
        service.validate_timing(TestSize.SMALL, 0.5)

    def it_raises_error_for_small_test_exceeding_limit(self) -> None:
        """Raise TimingViolationError when small test exceeds 1s limit."""
        service = TimingValidationService()

        with pytest.raises(TimingViolationError):
            service.validate_timing(TestSize.SMALL, 1.5)

    def it_validates_medium_test_within_limit(self) -> None:
        """Validate medium test that completes within 300s limit."""
        service = TimingValidationService()

        service.validate_timing(TestSize.MEDIUM, 250.0)

    def it_raises_error_for_medium_test_exceeding_limit(self) -> None:
        """Raise TimingViolationError when medium test exceeds 300s limit."""
        service = TimingValidationService()

        with pytest.raises(TimingViolationError):
            service.validate_timing(TestSize.MEDIUM, 350.0)

    def it_validates_large_test_within_limit(self) -> None:
        """Validate large test that completes within 900s limit."""
        service = TimingValidationService()

        service.validate_timing(TestSize.LARGE, 800.0)

    def it_raises_error_for_large_test_exceeding_limit(self) -> None:
        """Raise TimingViolationError when large test exceeds 900s limit."""
        service = TimingValidationService()

        with pytest.raises(TimingViolationError):
            service.validate_timing(TestSize.LARGE, 950.0)

    def it_validates_xlarge_test_within_limit(self) -> None:
        """Validate xlarge test that completes within 900s limit."""
        service = TimingValidationService()

        service.validate_timing(TestSize.XLARGE, 850.0)

    def it_raises_error_for_xlarge_test_exceeding_limit(self) -> None:
        """Raise TimingViolationError when xlarge test exceeds 900s limit."""
        service = TimingValidationService()

        with pytest.raises(TimingViolationError):
            service.validate_timing(TestSize.XLARGE, 1000.0)

    def it_validates_test_at_exact_limit(self) -> None:
        """Validate test that completes exactly at the time limit."""
        service = TimingValidationService()

        # Exactly 1s should pass for SMALL
        service.validate_timing(TestSize.SMALL, 1.0)


@pytest.mark.small
class DescribeGetTestDuration:
    """Test suite for get_test_duration method."""

    def it_prefers_report_duration_over_timer(self) -> None:
        """Return report duration when both report and timer are available."""
        service = TimingValidationService()
        timer = FakeTimer()
        timer.start()
        timer.advance(0.5)
        timer.stop()

        duration = service.get_test_duration(timer, 0.6)

        assert duration == 0.6

    def it_falls_back_to_timer_duration(self) -> None:
        """Return timer duration when report duration is None."""
        service = TimingValidationService()
        timer = FakeTimer()
        timer.start()
        timer.advance(0.5)
        timer.stop()

        duration = service.get_test_duration(timer, None)

        assert duration == 0.5

    def it_returns_none_when_both_unavailable(self) -> None:
        """Return None when both timer and report duration are unavailable."""
        service = TimingValidationService()

        duration = service.get_test_duration(None, None)

        assert duration is None

    def it_returns_none_when_timer_is_not_stopped(self) -> None:
        """Return None when timer is not in STOPPED state."""
        service = TimingValidationService()
        timer = FakeTimer(state=TimerState.READY)

        duration = service.get_test_duration(timer, None)

        assert duration is None

    def it_returns_none_when_timer_is_running(self) -> None:
        """Return None when timer is still running."""
        service = TimingValidationService()
        timer = FakeTimer(state=TimerState.RUNNING)

        duration = service.get_test_duration(timer, None)

        assert duration is None

    def it_handles_timer_duration_error_gracefully(self) -> None:
        """Return None when timer.duration() raises an error."""
        service = TimingValidationService()

        # Create a timer that will raise an error when duration() is called
        # We can't easily make FakeTimer raise an error, so we'll use a mock
        class BrokenTimer(FakeTimer):
            """Timer that raises error on duration()."""

            def duration(self) -> float:
                """Raise RuntimeError."""
                msg = 'Timer error'
                raise RuntimeError(msg)

        timer = BrokenTimer(state=TimerState.STOPPED)
        duration = service.get_test_duration(timer, None)

        assert duration is None

    def it_handles_timer_value_error_gracefully(self) -> None:
        """Return None when timer.duration() raises ValueError."""
        service = TimingValidationService()

        class BrokenTimer(FakeTimer):
            """Timer that raises ValueError on duration()."""

            def duration(self) -> float:
                """Raise ValueError."""
                msg = 'Invalid duration'
                raise ValueError(msg)

        timer = BrokenTimer(state=TimerState.STOPPED)
        duration = service.get_test_duration(timer, None)

        assert duration is None

    def it_returns_zero_duration_from_report(self) -> None:
        """Return zero duration when report duration is 0.0."""
        service = TimingValidationService()

        duration = service.get_test_duration(None, 0.0)

        assert duration == 0.0


@pytest.mark.small
class DescribeCleanupTimer:
    """Test suite for cleanup_timer method."""

    def it_removes_timer_from_dictionary(self) -> None:
        """Remove timer from timers dictionary."""
        service = TimingValidationService()
        timer = FakeTimer()
        timers: MutableMapping[str, TestTimer] = {'test.py::test_func': timer}

        service.cleanup_timer(timers, 'test.py::test_func')

        assert 'test.py::test_func' not in timers
        assert len(timers) == 0

    def it_handles_missing_timer_gracefully(self) -> None:
        """Handle cleanup when timer is not in dictionary."""
        service = TimingValidationService()
        timers: MutableMapping[str, TestTimer] = {}

        # Should not raise exception
        service.cleanup_timer(timers, 'test.py::test_func')

        assert len(timers) == 0

    def it_only_removes_specified_timer(self) -> None:
        """Remove only the specified timer, leaving others intact."""
        service = TimingValidationService()
        timer1 = FakeTimer()
        timer2 = FakeTimer()
        timers: MutableMapping[str, TestTimer] = {
            'test.py::test_one': timer1,
            'test.py::test_two': timer2,
        }

        service.cleanup_timer(timers, 'test.py::test_one')

        assert 'test.py::test_one' not in timers
        assert 'test.py::test_two' in timers
        assert len(timers) == 1

    def it_modifies_timers_dict_in_place(self) -> None:
        """Modify the original timers dictionary in place."""
        service = TimingValidationService()
        timer = FakeTimer()
        timers: MutableMapping[str, TestTimer] = {'test.py::test_func': timer}
        original_dict_id = id(timers)

        service.cleanup_timer(timers, 'test.py::test_func')

        # Should be the same dictionary object
        assert id(timers) == original_dict_id


@pytest.mark.small
class DescribeValidateTimingWithBaseline:
    """Test suite for validate_timing_with_baseline method."""

    def it_passes_when_duration_is_within_baseline(self) -> None:
        """Pass validation when duration is within custom baseline."""
        service = TimingValidationService()

        # Should not raise exception
        service.validate_timing_with_baseline(
            test_size=TestSize.SMALL,
            duration=0.05,
            baseline=0.1,
        )

    def it_raises_baseline_violation_when_exceeding_baseline(self) -> None:
        """Raise PerformanceBaselineViolationError when exceeding baseline."""
        service = TimingValidationService()

        with pytest.raises(PerformanceBaselineViolationError):
            service.validate_timing_with_baseline(
                test_size=TestSize.SMALL,
                duration=0.15,  # Exceeds 0.1 baseline
                baseline=0.1,
            )

    def it_falls_back_to_category_limit_when_no_baseline(self) -> None:
        """Fall back to category limit when baseline is None."""
        service = TimingValidationService()

        with pytest.raises(TimingViolationError):
            service.validate_timing_with_baseline(
                test_size=TestSize.SMALL,
                duration=1.5,  # Exceeds 1.0 category limit
                baseline=None,
            )

    def it_passes_within_category_limit_without_baseline(self) -> None:
        """Pass when duration is within category limit and no baseline."""
        service = TimingValidationService()

        # Should not raise exception
        service.validate_timing_with_baseline(
            test_size=TestSize.SMALL,
            duration=0.5,  # Within 1.0 category limit
            baseline=None,
        )

    def it_raises_value_error_when_baseline_exceeds_category_limit(self) -> None:
        """Raise ValueError when baseline exceeds category limit."""
        service = TimingValidationService()

        with pytest.raises(ValueError, match=r'baseline.*category limit'):
            service.validate_timing_with_baseline(
                test_size=TestSize.SMALL,
                duration=0.5,
                baseline=2.0,  # Exceeds 1.0 category limit
            )

    def it_works_with_medium_test_size(self) -> None:
        """Handle medium test size correctly."""
        service = TimingValidationService()

        with pytest.raises(PerformanceBaselineViolationError):
            service.validate_timing_with_baseline(
                test_size=TestSize.MEDIUM,
                duration=10.0,  # Exceeds 5.0 baseline
                baseline=5.0,
            )

    def it_works_with_large_test_size(self) -> None:
        """Handle large test size correctly."""
        service = TimingValidationService()

        with pytest.raises(PerformanceBaselineViolationError):
            service.validate_timing_with_baseline(
                test_size=TestSize.LARGE,
                duration=100.0,  # Exceeds 60.0 baseline
                baseline=60.0,
            )

    def it_works_with_xlarge_test_size(self) -> None:
        """Handle xlarge test size correctly."""
        service = TimingValidationService()

        with pytest.raises(PerformanceBaselineViolationError):
            service.validate_timing_with_baseline(
                test_size=TestSize.XLARGE,
                duration=200.0,  # Exceeds 120.0 baseline
                baseline=120.0,
            )

    def it_includes_test_nodeid_in_error(self) -> None:
        """Include test nodeid in error message."""
        service = TimingValidationService()

        with pytest.raises(PerformanceBaselineViolationError) as exc_info:
            service.validate_timing_with_baseline(
                test_size=TestSize.SMALL,
                duration=0.15,
                baseline=0.1,
                test_nodeid='tests/test_slow.py::test_compute',
            )

        assert 'tests/test_slow.py::test_compute' in str(exc_info.value)
