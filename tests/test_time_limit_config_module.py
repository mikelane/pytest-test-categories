"""Unit tests for the TimeLimitConfig model.

This module tests the configuration model for custom time limits per test size.
Tests follow TDD - these tests are written first, then implementation follows.
"""

from __future__ import annotations

import pytest

from pytest_test_categories.types import TestSize


@pytest.mark.small
class DescribeTimeLimitConfig:
    """Test suite for TimeLimitConfig model."""

    def it_creates_with_default_limits(self) -> None:
        """Create config with default time limits matching current constants."""
        from pytest_test_categories.timing import TimeLimitConfig

        config = TimeLimitConfig()

        assert config.small == 1.0
        assert config.medium == 300.0
        assert config.large == 900.0
        assert config.xlarge == 900.0

    def it_creates_with_custom_limits(self) -> None:
        """Create config with custom time limits."""
        from pytest_test_categories.timing import TimeLimitConfig

        config = TimeLimitConfig(
            small=2.0,
            medium=600.0,
            large=1800.0,
            xlarge=3600.0,
        )

        assert config.small == 2.0
        assert config.medium == 600.0
        assert config.large == 1800.0
        assert config.xlarge == 3600.0

    def it_rejects_negative_limits(self) -> None:
        """Reject negative time limits."""
        from pytest_test_categories.timing import TimeLimitConfig

        with pytest.raises(ValueError, match='Input should be greater than 0'):
            TimeLimitConfig(small=-1.0)

    def it_rejects_zero_limits(self) -> None:
        """Reject zero time limits."""
        from pytest_test_categories.timing import TimeLimitConfig

        with pytest.raises(ValueError, match='Input should be greater than 0'):
            TimeLimitConfig(medium=0.0)

    def it_is_frozen_immutable(self) -> None:
        """Configuration is immutable after creation."""
        from pytest_test_categories.timing import TimeLimitConfig

        config = TimeLimitConfig()

        from pydantic import ValidationError

        with pytest.raises(ValidationError, match='Instance is frozen'):
            config.small = 5.0  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.small
class DescribeTimeLimitConfigValidation:
    """Test suite for ordering validation in TimeLimitConfig."""

    def it_validates_small_less_than_medium(self) -> None:
        """Raise error when small limit exceeds medium limit."""
        from pytest_test_categories.timing import TimeLimitConfig

        with pytest.raises(ValueError, match=r'small .* must be less than medium'):
            TimeLimitConfig(small=500.0, medium=300.0)

    def it_validates_medium_less_than_large(self) -> None:
        """Raise error when medium limit exceeds large limit."""
        from pytest_test_categories.timing import TimeLimitConfig

        with pytest.raises(ValueError, match=r'medium .* must be less than large'):
            TimeLimitConfig(medium=1000.0, large=900.0)

    def it_validates_large_less_than_or_equal_xlarge(self) -> None:
        """Raise error when large limit exceeds xlarge limit."""
        from pytest_test_categories.timing import TimeLimitConfig

        with pytest.raises(ValueError, match=r'large .* must be less than or equal to xlarge'):
            TimeLimitConfig(large=1000.0, xlarge=900.0)

    def it_allows_equal_large_and_xlarge(self) -> None:
        """Allow large and xlarge to have the same limit."""
        from pytest_test_categories.timing import TimeLimitConfig

        config = TimeLimitConfig(large=1800.0, xlarge=1800.0)

        assert config.large == 1800.0
        assert config.xlarge == 1800.0

    def it_allows_valid_ordering(self) -> None:
        """Accept properly ordered limits."""
        from pytest_test_categories.timing import TimeLimitConfig

        config = TimeLimitConfig(
            small=1.0,
            medium=300.0,
            large=900.0,
            xlarge=900.0,
        )

        assert config.small < config.medium < config.large <= config.xlarge


@pytest.mark.small
class DescribeTimeLimitConfigGetLimit:
    """Test suite for get_limit method on TimeLimitConfig."""

    def it_returns_small_limit_for_small_size(self) -> None:
        """Return small limit for TestSize.SMALL."""
        from pytest_test_categories.timing import TimeLimitConfig

        config = TimeLimitConfig(small=2.0)

        assert config.get_limit(TestSize.SMALL) == 2.0

    def it_returns_medium_limit_for_medium_size(self) -> None:
        """Return medium limit for TestSize.MEDIUM."""
        from pytest_test_categories.timing import TimeLimitConfig

        config = TimeLimitConfig(medium=600.0)

        assert config.get_limit(TestSize.MEDIUM) == 600.0

    def it_returns_large_limit_for_large_size(self) -> None:
        """Return large limit for TestSize.LARGE."""
        from pytest_test_categories.timing import TimeLimitConfig

        config = TimeLimitConfig(large=1800.0, xlarge=1800.0)

        assert config.get_limit(TestSize.LARGE) == 1800.0

    def it_returns_xlarge_limit_for_xlarge_size(self) -> None:
        """Return xlarge limit for TestSize.XLARGE."""
        from pytest_test_categories.timing import TimeLimitConfig

        config = TimeLimitConfig(xlarge=3600.0)

        assert config.get_limit(TestSize.XLARGE) == 3600.0


@pytest.mark.small
class DescribeDefaultTimeLimitConfig:
    """Test suite for DEFAULT_TIME_LIMIT_CONFIG constant."""

    def it_has_default_config_constant(self) -> None:
        """Module has DEFAULT_TIME_LIMIT_CONFIG constant."""
        from pytest_test_categories.timing import DEFAULT_TIME_LIMIT_CONFIG, TimeLimitConfig

        assert isinstance(DEFAULT_TIME_LIMIT_CONFIG, TimeLimitConfig)
        assert DEFAULT_TIME_LIMIT_CONFIG.small == 1.0
        assert DEFAULT_TIME_LIMIT_CONFIG.medium == 300.0
        assert DEFAULT_TIME_LIMIT_CONFIG.large == 900.0
        assert DEFAULT_TIME_LIMIT_CONFIG.xlarge == 900.0
