"""Unit tests for the DistributionConfig model.

This module tests the configuration model for custom distribution targets per test size.
Tests follow TDD - these tests are written first, then implementation follows.
"""

from __future__ import annotations

import pytest


@pytest.mark.small
class DescribeDistributionConfig:
    """Test suite for DistributionConfig model."""

    def it_creates_with_default_targets(self) -> None:
        """Create config with default distribution targets matching Google's recommendations."""
        from pytest_test_categories.distribution.config import DistributionConfig

        config = DistributionConfig()

        assert config.small_target == 80.0
        assert config.medium_target == 15.0
        assert config.large_target == 5.0
        assert config.small_tolerance == 5.0
        assert config.medium_tolerance == 5.0
        assert config.large_tolerance == 3.0

    def it_creates_with_custom_targets(self) -> None:
        """Create config with custom distribution targets."""
        from pytest_test_categories.distribution.config import DistributionConfig

        config = DistributionConfig(
            small_target=70.0,
            medium_target=20.0,
            large_target=10.0,
        )

        assert config.small_target == 70.0
        assert config.medium_target == 20.0
        assert config.large_target == 10.0

    def it_creates_with_custom_tolerances(self) -> None:
        """Create config with custom tolerances."""
        from pytest_test_categories.distribution.config import DistributionConfig

        config = DistributionConfig(
            small_tolerance=8.0,
            medium_tolerance=8.0,
            large_tolerance=5.0,
        )

        assert config.small_tolerance == 8.0
        assert config.medium_tolerance == 8.0
        assert config.large_tolerance == 5.0

    def it_rejects_negative_targets(self) -> None:
        """Reject negative target values."""
        from pytest_test_categories.distribution.config import DistributionConfig

        with pytest.raises(ValueError, match='Input should be greater than or equal to 0'):
            DistributionConfig(small_target=-1.0)

    def it_rejects_targets_over_100(self) -> None:
        """Reject target values over 100%."""
        from pytest_test_categories.distribution.config import DistributionConfig

        with pytest.raises(ValueError, match='Input should be less than or equal to 100'):
            DistributionConfig(small_target=101.0)

    def it_rejects_zero_tolerance(self) -> None:
        """Reject zero tolerance values."""
        from pytest_test_categories.distribution.config import DistributionConfig

        with pytest.raises(ValueError, match='Input should be greater than 0'):
            DistributionConfig(small_tolerance=0.0)

    def it_rejects_tolerance_over_20(self) -> None:
        """Reject tolerance values over 20%."""
        from pytest_test_categories.distribution.config import DistributionConfig

        with pytest.raises(ValueError, match='Input should be less than or equal to 20'):
            DistributionConfig(small_tolerance=21.0)

    def it_is_frozen_immutable(self) -> None:
        """Configuration is immutable after creation."""
        from pytest_test_categories.distribution.config import DistributionConfig

        config = DistributionConfig()

        from pydantic import ValidationError

        with pytest.raises(ValidationError, match='Instance is frozen'):
            config.small_target = 90.0  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.small
class DescribeDistributionConfigValidation:
    """Test suite for target sum validation in DistributionConfig."""

    def it_warns_when_targets_do_not_sum_to_100(self) -> None:
        """Emit warning when targets do not sum to 100%."""
        from pytest_test_categories.distribution.config import DistributionConfig

        # targets sum to 90%, should still work but be flagged
        config = DistributionConfig(
            small_target=70.0,
            medium_target=15.0,
            large_target=5.0,
        )
        # Config should still be created
        assert config.small_target == 70.0
        # The targets_sum property should reflect the actual sum
        assert config.targets_sum == 90.0
        assert not config.targets_sum_to_100

    def it_recognizes_when_targets_sum_to_100(self) -> None:
        """Recognize when targets properly sum to 100%."""
        from pytest_test_categories.distribution.config import DistributionConfig

        config = DistributionConfig(
            small_target=70.0,
            medium_target=20.0,
            large_target=10.0,
        )

        assert config.targets_sum == 100.0
        assert config.targets_sum_to_100

    def it_allows_targets_within_rounding_tolerance(self) -> None:
        """Allow targets that sum to 100% within rounding tolerance."""
        from pytest_test_categories.distribution.config import DistributionConfig

        # Due to floating point, these might not sum to exactly 100.0
        config = DistributionConfig(
            small_target=80.01,
            medium_target=14.99,
            large_target=5.0,
        )

        # Should still be considered valid within tolerance
        assert config.targets_sum_to_100


@pytest.mark.small
class DescribeDistributionConfigRanges:
    """Test suite for getting distribution ranges from config."""

    def it_provides_small_range(self) -> None:
        """Provide DistributionRange for small tests."""
        from pytest_test_categories.distribution.config import DistributionConfig
        from pytest_test_categories.distribution.stats import DistributionRange

        config = DistributionConfig()
        small_range = config.get_small_range()

        assert isinstance(small_range, DistributionRange)
        assert small_range.target == 80.0
        assert small_range.tolerance == 5.0
        assert small_range.min_value == 75.0
        assert small_range.max_value == 85.0

    def it_provides_medium_range(self) -> None:
        """Provide DistributionRange for medium tests."""
        from pytest_test_categories.distribution.config import DistributionConfig
        from pytest_test_categories.distribution.stats import DistributionRange

        config = DistributionConfig()
        medium_range = config.get_medium_range()

        assert isinstance(medium_range, DistributionRange)
        assert medium_range.target == 15.0
        assert medium_range.tolerance == 5.0
        assert medium_range.min_value == 10.0
        assert medium_range.max_value == 20.0

    def it_provides_large_xlarge_range(self) -> None:
        """Provide DistributionRange for large/xlarge tests combined."""
        from pytest_test_categories.distribution.config import DistributionConfig
        from pytest_test_categories.distribution.stats import DistributionRange

        config = DistributionConfig()
        large_range = config.get_large_xlarge_range()

        assert isinstance(large_range, DistributionRange)
        assert large_range.target == 5.0
        assert large_range.tolerance == 3.0
        assert large_range.min_value == 2.0
        assert large_range.max_value == 8.0

    def it_provides_custom_ranges(self) -> None:
        """Provide custom ranges based on config."""
        from pytest_test_categories.distribution.config import DistributionConfig

        config = DistributionConfig(
            small_target=70.0,
            small_tolerance=10.0,
            medium_target=20.0,
            medium_tolerance=8.0,
            large_target=10.0,
            large_tolerance=5.0,
        )

        small_range = config.get_small_range()
        assert small_range.target == 70.0
        assert small_range.tolerance == 10.0
        assert small_range.min_value == 60.0
        assert small_range.max_value == 80.0

        medium_range = config.get_medium_range()
        assert medium_range.target == 20.0
        assert medium_range.tolerance == 8.0

        large_range = config.get_large_xlarge_range()
        assert large_range.target == 10.0
        assert large_range.tolerance == 5.0


@pytest.mark.small
class DescribeDefaultDistributionConfig:
    """Test suite for DEFAULT_DISTRIBUTION_CONFIG constant."""

    def it_has_default_config_constant(self) -> None:
        """Module has DEFAULT_DISTRIBUTION_CONFIG constant."""
        from pytest_test_categories.distribution.config import (
            DEFAULT_DISTRIBUTION_CONFIG,
            DistributionConfig,
        )

        assert isinstance(DEFAULT_DISTRIBUTION_CONFIG, DistributionConfig)
        assert DEFAULT_DISTRIBUTION_CONFIG.small_target == 80.0
        assert DEFAULT_DISTRIBUTION_CONFIG.medium_target == 15.0
        assert DEFAULT_DISTRIBUTION_CONFIG.large_target == 5.0
        assert DEFAULT_DISTRIBUTION_CONFIG.small_tolerance == 5.0
        assert DEFAULT_DISTRIBUTION_CONFIG.medium_tolerance == 5.0
        assert DEFAULT_DISTRIBUTION_CONFIG.large_tolerance == 3.0
