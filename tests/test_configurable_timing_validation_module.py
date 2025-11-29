"""Unit tests for configurable timing validation.

This module tests that TimingValidationService and timing.validate()
properly use configurable time limits.
"""

from __future__ import annotations

import pytest

from pytest_test_categories.timing import (
    TimeLimitConfig,
    validate,
)
from pytest_test_categories.types import (
    TestSize,
    TimingViolationError,
)


@pytest.mark.small
class DescribeValidateWithConfig:
    """Test validate() with custom TimeLimitConfig."""

    def it_uses_default_config_when_none_provided(self) -> None:
        """Use DEFAULT_TIME_LIMIT_CONFIG when no config provided."""
        # Should pass with default small limit of 1.0s
        validate(TestSize.SMALL, 0.5)

        # Should fail when exceeding default small limit
        with pytest.raises(TimingViolationError, match=r'1\.0 seconds'):
            validate(TestSize.SMALL, 1.5)

    def it_respects_custom_small_limit(self) -> None:
        """Respect custom small time limit from config."""
        config = TimeLimitConfig(small=5.0)

        # 2.0s would fail with default, but passes with custom 5.0s limit
        validate(TestSize.SMALL, 2.0, config=config)

        # 6.0s exceeds custom 5.0s limit
        with pytest.raises(TimingViolationError, match=r'5\.0 seconds'):
            validate(TestSize.SMALL, 6.0, config=config)

    def it_respects_custom_medium_limit(self) -> None:
        """Respect custom medium time limit from config."""
        config = TimeLimitConfig(medium=600.0)

        # 400s would pass anyway, but let's verify custom limit is used
        validate(TestSize.MEDIUM, 400.0, config=config)

        # 650s exceeds custom 600s limit
        with pytest.raises(TimingViolationError, match=r'600\.0 seconds'):
            validate(TestSize.MEDIUM, 650.0, config=config)

    def it_respects_custom_large_limit(self) -> None:
        """Respect custom large time limit from config."""
        config = TimeLimitConfig(large=1800.0, xlarge=1800.0)

        # 1500s exceeds default 900s but passes with custom 1800s
        validate(TestSize.LARGE, 1500.0, config=config)

        # 2000s exceeds custom 1800s limit
        with pytest.raises(TimingViolationError, match=r'1800\.0 seconds'):
            validate(TestSize.LARGE, 2000.0, config=config)

    def it_respects_custom_xlarge_limit(self) -> None:
        """Respect custom xlarge time limit from config."""
        config = TimeLimitConfig(large=1800.0, xlarge=3600.0)

        # 2000s exceeds default 900s but passes with custom 3600s
        validate(TestSize.XLARGE, 2000.0, config=config)

        # 4000s exceeds custom 3600s limit
        with pytest.raises(TimingViolationError, match=r'3600\.0 seconds'):
            validate(TestSize.XLARGE, 4000.0, config=config)

    def it_includes_custom_limit_in_error_message(self) -> None:
        """Error message includes the custom limit value."""
        config = TimeLimitConfig(small=2.5)

        with pytest.raises(TimingViolationError, match=r'2\.5 seconds'):
            validate(TestSize.SMALL, 3.0, config=config)


@pytest.mark.small
class DescribeTimingValidationServiceWithConfig:
    """Test TimingValidationService with configurable limits."""

    def it_uses_default_config_when_none_provided(self) -> None:
        """Use default limits when no config provided."""
        from pytest_test_categories.services.timing_validation import TimingValidationService

        service = TimingValidationService()

        # Default small limit is 1.0s
        service.validate_timing(TestSize.SMALL, 0.5)

        with pytest.raises(TimingViolationError):
            service.validate_timing(TestSize.SMALL, 1.5)

    def it_respects_custom_config(self) -> None:
        """Respect custom config when provided."""
        from pytest_test_categories.services.timing_validation import TimingValidationService

        service = TimingValidationService()
        config = TimeLimitConfig(small=5.0)

        # 2.0s passes with custom 5.0s limit
        service.validate_timing(TestSize.SMALL, 2.0, config=config)

        # 6.0s fails with custom 5.0s limit
        with pytest.raises(TimingViolationError, match=r'5\.0 seconds'):
            service.validate_timing(TestSize.SMALL, 6.0, config=config)

    def it_validates_all_sizes_with_custom_config(self) -> None:
        """Validate all test sizes using custom config."""
        from pytest_test_categories.services.timing_validation import TimingValidationService

        service = TimingValidationService()
        config = TimeLimitConfig(
            small=2.0,
            medium=600.0,
            large=1800.0,
            xlarge=3600.0,
        )

        # All should pass with extended limits
        service.validate_timing(TestSize.SMALL, 1.5, config=config)
        service.validate_timing(TestSize.MEDIUM, 500.0, config=config)
        service.validate_timing(TestSize.LARGE, 1500.0, config=config)
        service.validate_timing(TestSize.XLARGE, 3000.0, config=config)

        # All should fail when exceeding custom limits
        with pytest.raises(TimingViolationError):
            service.validate_timing(TestSize.SMALL, 3.0, config=config)
        with pytest.raises(TimingViolationError):
            service.validate_timing(TestSize.MEDIUM, 700.0, config=config)
        with pytest.raises(TimingViolationError):
            service.validate_timing(TestSize.LARGE, 2000.0, config=config)
        with pytest.raises(TimingViolationError):
            service.validate_timing(TestSize.XLARGE, 4000.0, config=config)
