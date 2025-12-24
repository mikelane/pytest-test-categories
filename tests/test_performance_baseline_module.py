"""Unit tests for performance baseline validation.

This module tests the performance baseline feature which allows tests to define
custom timeout limits stricter than their category's default limit.

Example usage:
    @pytest.mark.small(timeout=0.1)  # Must complete in 100ms instead of 1s
    def test_critical_path():
        pass
"""

from __future__ import annotations

import pytest

from pytest_test_categories.types import TestSize


@pytest.mark.small
class DescribePerformanceBaselineViolationError:
    """Test PerformanceBaselineViolationError exception."""

    def it_can_be_imported_from_timing_module(self) -> None:
        """Import PerformanceBaselineViolationError from timing module."""
        from pytest_test_categories.timing import PerformanceBaselineViolationError

        assert PerformanceBaselineViolationError is not None

    def it_stores_test_size(self) -> None:
        """Store test size in error attributes."""
        from pytest_test_categories.timing import PerformanceBaselineViolationError

        error = PerformanceBaselineViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_slow.py::test_compute',
            baseline_limit=0.1,
            category_limit=1.0,
            actual=0.25,
        )

        assert error.test_size == TestSize.SMALL

    def it_stores_test_nodeid(self) -> None:
        """Store test nodeid in error attributes."""
        from pytest_test_categories.timing import PerformanceBaselineViolationError

        error = PerformanceBaselineViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_slow.py::test_compute',
            baseline_limit=0.1,
            category_limit=1.0,
            actual=0.25,
        )

        assert error.test_nodeid == 'tests/test_slow.py::test_compute'

    def it_stores_baseline_limit(self) -> None:
        """Store custom baseline limit in error attributes."""
        from pytest_test_categories.timing import PerformanceBaselineViolationError

        error = PerformanceBaselineViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_slow.py::test_compute',
            baseline_limit=0.1,
            category_limit=1.0,
            actual=0.25,
        )

        assert error.baseline_limit == 0.1

    def it_stores_category_limit(self) -> None:
        """Store category limit in error attributes."""
        from pytest_test_categories.timing import PerformanceBaselineViolationError

        error = PerformanceBaselineViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_slow.py::test_compute',
            baseline_limit=0.1,
            category_limit=1.0,
            actual=0.25,
        )

        assert error.category_limit == 1.0

    def it_stores_actual_duration(self) -> None:
        """Store actual duration in error attributes."""
        from pytest_test_categories.timing import PerformanceBaselineViolationError

        error = PerformanceBaselineViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_slow.py::test_compute',
            baseline_limit=0.1,
            category_limit=1.0,
            actual=0.25,
        )

        assert error.actual == 0.25

    def it_includes_baseline_in_error_message(self) -> None:
        """Include custom baseline limit in error message."""
        from pytest_test_categories.timing import PerformanceBaselineViolationError

        error = PerformanceBaselineViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_slow.py::test_compute',
            baseline_limit=0.1,
            category_limit=1.0,
            actual=0.25,
        )

        message = str(error)
        assert '0.1' in message

    def it_includes_category_limit_in_error_message(self) -> None:
        """Include category limit in error message for context."""
        from pytest_test_categories.timing import PerformanceBaselineViolationError

        error = PerformanceBaselineViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_slow.py::test_compute',
            baseline_limit=0.1,
            category_limit=1.0,
            actual=0.25,
        )

        message = str(error)
        assert '1.0' in message

    def it_includes_actual_duration_in_error_message(self) -> None:
        """Include actual duration in error message."""
        from pytest_test_categories.timing import PerformanceBaselineViolationError

        error = PerformanceBaselineViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_slow.py::test_compute',
            baseline_limit=0.1,
            category_limit=1.0,
            actual=0.25,
        )

        message = str(error)
        assert '0.2' in message  # 0.25 formatted

    def it_includes_test_nodeid_in_error_message(self) -> None:
        """Include test nodeid in error message."""
        from pytest_test_categories.timing import PerformanceBaselineViolationError

        error = PerformanceBaselineViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_slow.py::test_compute',
            baseline_limit=0.1,
            category_limit=1.0,
            actual=0.25,
        )

        message = str(error)
        assert 'tests/test_slow.py::test_compute' in message

    def it_is_distinct_from_timing_violation_error(self) -> None:
        """PerformanceBaselineViolationError is not TimingViolationError."""
        from pytest_test_categories.timing import (
            PerformanceBaselineViolationError,
            TimingViolationError,
        )

        # Verify they are different classes
        assert PerformanceBaselineViolationError.__name__ != TimingViolationError.__name__
        assert not issubclass(PerformanceBaselineViolationError, TimingViolationError)

    def it_includes_performance_baseline_in_title(self) -> None:
        """Include 'Performance Baseline' in error title."""
        from pytest_test_categories.timing import PerformanceBaselineViolationError

        error = PerformanceBaselineViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_slow.py::test_compute',
            baseline_limit=0.1,
            category_limit=1.0,
            actual=0.25,
        )

        message = str(error)
        assert 'Performance Baseline' in message


@pytest.mark.small
class DescribeValidateWithBaseline:
    """Test validate function with custom baseline."""

    def it_passes_when_duration_is_within_baseline(self) -> None:
        """Pass validation when duration is within custom baseline."""
        from pytest_test_categories.timing import validate_with_baseline

        # Should not raise any exception
        validate_with_baseline(
            size=TestSize.SMALL,
            duration=0.05,
            baseline=0.1,
            test_nodeid='test.py::test_func',
        )

    def it_raises_baseline_violation_when_exceeding_baseline(self) -> None:
        """Raise PerformanceBaselineViolationError when exceeding baseline."""
        from pytest_test_categories.timing import (
            PerformanceBaselineViolationError,
            validate_with_baseline,
        )

        with pytest.raises(PerformanceBaselineViolationError):
            validate_with_baseline(
                size=TestSize.SMALL,
                duration=0.15,  # Exceeds 0.1 baseline
                baseline=0.1,
                test_nodeid='test.py::test_func',
            )

    def it_uses_category_limit_when_no_baseline_provided(self) -> None:
        """Fall back to category limit when baseline is None."""
        from pytest_test_categories.timing import (
            TimingViolationError,
            validate_with_baseline,
        )

        with pytest.raises(TimingViolationError):
            validate_with_baseline(
                size=TestSize.SMALL,
                duration=1.5,  # Exceeds 1.0 category limit
                baseline=None,
                test_nodeid='test.py::test_func',
            )

    def it_passes_when_within_category_limit_without_baseline(self) -> None:
        """Pass when duration is within category limit and no baseline."""
        from pytest_test_categories.timing import validate_with_baseline

        # Should not raise any exception
        validate_with_baseline(
            size=TestSize.SMALL,
            duration=0.5,  # Within 1.0 category limit
            baseline=None,
            test_nodeid='test.py::test_func',
        )

    def it_includes_category_limit_in_baseline_error(self) -> None:
        """Include category limit for context in baseline error."""
        from pytest_test_categories.timing import (
            PerformanceBaselineViolationError,
            validate_with_baseline,
        )

        with pytest.raises(PerformanceBaselineViolationError) as exc_info:
            validate_with_baseline(
                size=TestSize.SMALL,
                duration=0.15,
                baseline=0.1,
                test_nodeid='test.py::test_func',
            )

        # Category limit (1.0s for SMALL) should be in message
        assert '1.0' in str(exc_info.value)

    def it_works_with_medium_test_size(self) -> None:
        """Handle medium test size correctly."""
        from pytest_test_categories.timing import (
            PerformanceBaselineViolationError,
            validate_with_baseline,
        )

        with pytest.raises(PerformanceBaselineViolationError):
            validate_with_baseline(
                size=TestSize.MEDIUM,
                duration=10.0,  # Exceeds 5.0 baseline
                baseline=5.0,
                test_nodeid='test.py::test_func',
            )

    def it_validates_baseline_is_less_than_or_equal_to_category_limit(self) -> None:
        """Validate that baseline does not exceed category limit."""
        from pytest_test_categories.timing import validate_with_baseline

        with pytest.raises(ValueError, match=r'baseline.*category limit'):
            validate_with_baseline(
                size=TestSize.SMALL,
                duration=0.5,
                baseline=2.0,  # Exceeds 1.0 category limit
                test_nodeid='test.py::test_func',
            )
