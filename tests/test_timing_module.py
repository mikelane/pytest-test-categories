"""Tests for the timing module public APIs."""

from __future__ import annotations

import pytest

from pytest_test_categories.timing import (
    TimeLimit,
    get_limit,
    validate,
)
from pytest_test_categories.types import (
    TestSize,
    TimingViolationError,
)


class DescribeTimeLimit:
    """Test the TimeLimit model."""

    def it_creates_with_valid_limit(self) -> None:
        """Test that TimeLimit can be created with a positive limit."""
        limit = TimeLimit(limit=5.0)
        assert limit.limit == 5.0

    def it_rejects_negative_limits(self) -> None:
        """Test that TimeLimit rejects negative limits."""
        with pytest.raises(ValueError, match='Input should be greater than 0'):
            TimeLimit(limit=-1.0)

    def it_rejects_zero_limits(self) -> None:
        """Test that TimeLimit rejects zero limits."""
        with pytest.raises(ValueError, match='Input should be greater than 0'):
            TimeLimit(limit=0.0)

    def it_is_frozen(self) -> None:
        """Test that TimeLimit is immutable."""
        limit = TimeLimit(limit=5.0)
        with pytest.raises(ValueError, match='Instance is frozen'):
            limit.limit = 10.0


class DescribeGetLimit:
    """Test the get_limit function."""

    def it_returns_correct_limits_for_all_sizes(self) -> None:
        """Test that get_limit returns correct limits for all test sizes."""
        assert get_limit(TestSize.SMALL).limit == 1.0
        assert get_limit(TestSize.MEDIUM).limit == 300.0
        assert get_limit(TestSize.LARGE).limit == 900.0
        assert get_limit(TestSize.XLARGE).limit == 900.0

    def it_returns_time_limit_instances(self) -> None:
        """Test that get_limit returns TimeLimit instances."""
        for size in TestSize:
            limit = get_limit(size)
            assert isinstance(limit, TimeLimit)


class DescribeValidate:
    """Test the validate function."""

    def it_passes_when_duration_is_within_limit(self) -> None:
        """Test that validate passes when duration is within limit."""
        # Should not raise any exception
        validate(TestSize.SMALL, 0.5)  # 0.5 < 1.0
        validate(TestSize.MEDIUM, 200.0)  # 200.0 < 300.0
        validate(TestSize.LARGE, 800.0)  # 800.0 < 900.0
        validate(TestSize.XLARGE, 800.0)  # 800.0 < 900.0

    def it_passes_when_duration_equals_limit(self) -> None:
        """Test that validate passes when duration equals limit."""
        # Should not raise any exception
        validate(TestSize.SMALL, 1.0)  # 1.0 == 1.0
        validate(TestSize.MEDIUM, 300.0)  # 300.0 == 300.0
        validate(TestSize.LARGE, 900.0)  # 900.0 == 900.0
        validate(TestSize.XLARGE, 900.0)  # 900.0 == 900.0

    def it_raises_timing_violation_error_when_exceeding_limit(self) -> None:
        """Test that validate raises TimingViolationError when exceeding limit."""
        with pytest.raises(TimingViolationError, match='SMALL test exceeded time limit of 1.0 seconds'):
            validate(TestSize.SMALL, 1.1)  # 1.1 > 1.0

        with pytest.raises(TimingViolationError, match='MEDIUM test exceeded time limit of 300.0 seconds'):
            validate(TestSize.MEDIUM, 301.0)  # 301.0 > 300.0

        with pytest.raises(TimingViolationError, match='LARGE test exceeded time limit of 900.0 seconds'):
            validate(TestSize.LARGE, 901.0)  # 901.0 > 900.0

        with pytest.raises(TimingViolationError, match='XLARGE test exceeded time limit of 900.0 seconds'):
            validate(TestSize.XLARGE, 901.0)  # 901.0 > 900.0

    def it_includes_actual_duration_in_error_message(self) -> None:
        """Test that error message includes the actual duration."""
        with pytest.raises(TimingViolationError, match='took 1.5 seconds'):
            validate(TestSize.SMALL, 1.5)

    def it_handles_all_test_sizes(self) -> None:
        """Test that validate works for all test sizes."""
        for size in TestSize:
            # Test passing case
            validate(size, 0.1)

            # Test failing case
            with pytest.raises(TimingViolationError):
                validate(size, 1000.0)  # All limits are <= 900.0
