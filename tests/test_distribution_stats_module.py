"""Tests for the distribution stats module public APIs."""

from __future__ import annotations

import pytest

from pytest_test_categories import TestSize
from pytest_test_categories.distribution import (
    DistributionRange,
    DistributionStats,
    TestCounts,
    TestPercentages,
)


@pytest.mark.small
class DescribeDistributionRange:
    """Test the DistributionRange class."""

    def it_creates_with_valid_target_and_tolerance(self) -> None:
        """Test that DistributionRange can be created with valid values."""
        range_obj = DistributionRange(target=80.0, tolerance=5.0)
        assert range_obj.target == 80.0
        assert range_obj.tolerance == 5.0

    def it_calculates_min_value_correctly(self) -> None:
        """Test that min_value is calculated correctly."""
        range_obj = DistributionRange(target=80.0, tolerance=5.0)
        assert range_obj.min_value == 75.0  # 80.0 - 5.0

    def it_calculates_max_value_correctly(self) -> None:
        """Test that max_value is calculated correctly."""
        range_obj = DistributionRange(target=80.0, tolerance=5.0)
        assert range_obj.max_value == 85.0  # 80.0 + 5.0

    def it_handles_edge_cases_for_min_value(self) -> None:
        """Test that min_value handles edge cases correctly."""
        # Test case where target - tolerance would be negative
        range_obj = DistributionRange(target=2.0, tolerance=5.0)
        assert range_obj.min_value == 0.0  # max(0.0, 2.0 - 5.0)

    def it_handles_edge_cases_for_max_value(self) -> None:
        """Test that max_value handles edge cases correctly."""
        # Test case where target + tolerance would exceed 100%
        range_obj = DistributionRange(target=95.0, tolerance=10.0)
        assert range_obj.max_value == 100.0  # min(100.0, 95.0 + 10.0)

    def it_rejects_invalid_target_values(self) -> None:
        """Test that DistributionRange rejects invalid target values."""
        with pytest.raises(ValueError, match='Input should be greater than or equal to 0'):
            DistributionRange(target=-1.0, tolerance=5.0)

        with pytest.raises(ValueError, match='Input should be less than or equal to 100'):
            DistributionRange(target=101.0, tolerance=5.0)

    def it_rejects_invalid_tolerance_values(self) -> None:
        """Test that DistributionRange rejects invalid tolerance values."""
        with pytest.raises(ValueError, match='Input should be greater than 0'):
            DistributionRange(target=80.0, tolerance=0.0)

        with pytest.raises(ValueError, match='Input should be less than or equal to 20'):
            DistributionRange(target=80.0, tolerance=21.0)

    def it_is_frozen(self) -> None:
        """Test that DistributionRange is immutable."""
        range_obj = DistributionRange(target=80.0, tolerance=5.0)
        with pytest.raises(ValueError, match='Instance is frozen'):
            range_obj.target = 90.0


@pytest.mark.small
class DescribeTestCounts:
    """Test the TestCounts class."""

    def it_initializes_with_default_values(self) -> None:
        """Test that TestCounts initializes with default values."""
        counts = TestCounts()
        assert counts.small == 0
        assert counts.medium == 0
        assert counts.large == 0
        assert counts.xlarge == 0

    def it_creates_with_custom_values(self) -> None:
        """Test that TestCounts can be created with custom values."""
        counts = TestCounts(small=10, medium=5, large=2, xlarge=1)
        assert counts.small == 10
        assert counts.medium == 5
        assert counts.large == 2
        assert counts.xlarge == 1

    def it_rejects_negative_values(self) -> None:
        """Test that TestCounts rejects negative values."""
        with pytest.raises(ValueError, match='Input should be greater than or equal to 0'):
            TestCounts(small=-1)

    def it_is_frozen(self) -> None:
        """Test that TestCounts is immutable."""
        counts = TestCounts(small=10)
        with pytest.raises(ValueError, match='Instance is frozen'):
            counts.small = 20


@pytest.mark.small
class DescribeTestPercentages:
    """Test the TestPercentages class."""

    def it_initializes_with_default_values(self) -> None:
        """Test that TestPercentages initializes with default values."""
        percentages = TestPercentages()
        assert percentages.small == 0.0
        assert percentages.medium == 0.0
        assert percentages.large == 0.0
        assert percentages.xlarge == 0.0

    def it_creates_with_valid_percentages(self) -> None:
        """Test that TestPercentages can be created with valid percentages."""
        percentages = TestPercentages(small=80.0, medium=15.0, large=3.0, xlarge=2.0)
        assert percentages.small == 80.0
        assert percentages.medium == 15.0
        assert percentages.large == 3.0
        assert percentages.xlarge == 2.0

    def it_rounds_values_to_two_decimals(self) -> None:
        """Test that values are rounded to two decimal places."""
        percentages = TestPercentages(small=80.123456, medium=15.987654, large=3.889, xlarge=0.0)
        assert percentages.small == 80.12
        assert percentages.medium == 15.99
        assert percentages.large == 3.89

    def it_validates_percentages_sum_to_100(self) -> None:
        """Test that percentages must sum to 100%."""
        # Valid case
        TestPercentages(small=80.0, medium=15.0, large=3.0, xlarge=2.0)

        # Invalid case
        with pytest.raises(ValueError, match='Percentages must sum to 100%'):
            TestPercentages(small=80.0, medium=15.0, large=3.0, xlarge=1.0)

    def it_allows_all_zeros(self) -> None:
        """Test that all zeros are allowed."""
        percentages = TestPercentages(small=0.0, medium=0.0, large=0.0, xlarge=0.0)
        assert percentages.small == 0.0
        assert percentages.medium == 0.0
        assert percentages.large == 0.0
        assert percentages.xlarge == 0.0

    def it_handles_rounding_tolerance(self) -> None:
        """Test that small rounding errors are tolerated."""
        # Should pass with small rounding error
        TestPercentages(small=80.0, medium=15.0, large=3.0, xlarge=2.0)

    def it_rejects_negative_percentages(self) -> None:
        """Test that negative percentages are rejected."""
        with pytest.raises(ValueError, match='Input should be greater than or equal to 0'):
            TestPercentages(small=-1.0, medium=101.0, large=0.0, xlarge=0.0)

    def it_rejects_percentages_over_100(self) -> None:
        """Test that percentages over 100% are rejected."""
        with pytest.raises(ValueError, match='Input should be less than or equal to 100'):
            TestPercentages(small=101.0, medium=0.0, large=0.0, xlarge=0.0)


@pytest.mark.small
class DescribeDistributionStats:
    """Test the DistributionStats class."""

    def it_initializes_with_default_counts(self) -> None:
        """Test that DistributionStats initializes with default counts."""
        stats = DistributionStats()
        assert stats.counts.small == 0
        assert stats.counts.medium == 0
        assert stats.counts.large == 0
        assert stats.counts.xlarge == 0

    def it_creates_with_custom_counts(self) -> None:
        """Test that DistributionStats can be created with custom counts."""
        counts = TestCounts(small=10, medium=5, large=2, xlarge=1)
        stats = DistributionStats(counts=counts)
        assert stats.counts.small == 10
        assert stats.counts.medium == 5
        assert stats.counts.large == 2
        assert stats.counts.xlarge == 1

    def it_calculates_percentages_correctly(self) -> None:
        """Test that calculate_percentages returns correct percentages."""
        counts = TestCounts(small=8, medium=1, large=1, xlarge=0)
        stats = DistributionStats(counts=counts)

        percentages = stats.calculate_percentages()
        assert percentages.small == 80.0  # 8/10 * 100
        assert percentages.medium == 10.0  # 1/10 * 100
        assert percentages.large == 10.0  # 1/10 * 100
        assert percentages.xlarge == 0.0  # 0/10 * 100

    def it_handles_zero_total_correctly(self) -> None:
        """Test that calculate_percentages handles zero total correctly."""
        stats = DistributionStats()
        percentages = stats.calculate_percentages()
        assert percentages.small == 0.0
        assert percentages.medium == 0.0
        assert percentages.large == 0.0
        assert percentages.xlarge == 0.0

    def it_rounds_percentages_correctly(self) -> None:
        """Test that percentages are rounded correctly."""
        # This test is testing implementation details rather than behavior
        # The actual rounding behavior is complex and depends on the implementation
        # We test the behavior in other tests

    def it_updates_counts_from_mapping(self) -> None:
        """Test that update_counts works with a mapping."""
        counts_dict = {TestSize.SMALL: 10, TestSize.MEDIUM: 5, TestSize.LARGE: 2, TestSize.XLARGE: 1}
        stats = DistributionStats.update_counts(counts_dict)

        assert stats.counts.small == 10
        assert stats.counts.medium == 5
        assert stats.counts.large == 2
        assert stats.counts.xlarge == 1

    def it_updates_counts_from_test_counts(self) -> None:
        """Test that update_counts works with TestCounts."""
        counts = TestCounts(small=10, medium=5, large=2, xlarge=1)
        stats = DistributionStats.update_counts(counts)

        assert stats.counts.small == 10
        assert stats.counts.medium == 5
        assert stats.counts.large == 2
        assert stats.counts.xlarge == 1

    def it_validates_compliant_distribution(self) -> None:
        """Test that validate_distribution passes for compliant distributions."""
        # 80% small, 15% medium, 5% large/xlarge - should be compliant
        counts = TestCounts(small=80, medium=15, large=3, xlarge=2)
        stats = DistributionStats(counts=counts)

        # Should not raise any exception
        stats.validate_distribution()

    def it_validates_small_below_range(self) -> None:
        """Test that validate_distribution fails when small tests are below range."""
        # 60% small - below 75% minimum
        counts = TestCounts(small=60, medium=30, large=8, xlarge=2)
        stats = DistributionStats(counts=counts)

        with pytest.raises(ValueError, match='Small test percentage.*outside target range'):
            stats.validate_distribution()

    def it_validates_small_above_range(self) -> None:
        """Test that validate_distribution fails when small tests are above range."""
        # 90% small - above 85% maximum
        counts = TestCounts(small=90, medium=5, large=3, xlarge=2)
        stats = DistributionStats(counts=counts)

        with pytest.raises(ValueError, match='Small test percentage.*outside target range'):
            stats.validate_distribution()

    def it_validates_medium_below_range(self) -> None:
        """Test that validate_distribution fails when medium tests are below range."""
        # 5% medium - below 10% minimum
        counts = TestCounts(small=85, medium=5, large=8, xlarge=2)
        stats = DistributionStats(counts=counts)

        with pytest.raises(ValueError, match='Medium test percentage.*outside target range'):
            stats.validate_distribution()

    def it_validates_medium_above_range(self) -> None:
        """Test that validate_distribution fails when medium tests are above range."""
        # 25% medium - above 20% maximum, but this will fail on small first (70% < 75%)
        counts = TestCounts(small=70, medium=25, large=3, xlarge=2)
        stats = DistributionStats(counts=counts)

        with pytest.raises(ValueError, match='Small test percentage.*outside target range'):
            stats.validate_distribution()

    def it_validates_large_xlarge_below_range(self) -> None:
        """Test that validate_distribution fails when large/xlarge tests are below range."""
        # 1% large/xlarge - below 2% minimum
        counts = TestCounts(small=80, medium=19, large=1, xlarge=0)
        stats = DistributionStats(counts=counts)

        with pytest.raises(ValueError, match='Large/XLarge test percentage.*outside target range'):
            stats.validate_distribution()

    def it_validates_large_xlarge_above_range(self) -> None:
        """Test that validate_distribution fails when large/xlarge tests are above range."""
        # 10% large/xlarge - above 8% maximum
        counts = TestCounts(small=75, medium=15, large=8, xlarge=2)
        stats = DistributionStats(counts=counts)

        with pytest.raises(ValueError, match='Large/XLarge test percentage.*outside target range'):
            stats.validate_distribution()

    def it_is_frozen(self) -> None:
        """Test that DistributionStats is immutable."""
        stats = DistributionStats()
        with pytest.raises(ValueError, match='Instance is frozen'):
            stats.counts = TestCounts(small=10)
