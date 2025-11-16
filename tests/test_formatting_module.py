"""Unit tests for formatting module.

This module tests the formatting utilities in isolation without pytest dependencies.
All functions are pure and testable with simple assertions.
"""

from __future__ import annotations

import pytest

from pytest_test_categories import formatting
from pytest_test_categories.distribution.stats import TestPercentages


@pytest.mark.small
class DescribePluralizeTest:
    """Test suite for pluralize_test function."""

    def it_returns_test_for_count_of_one(self) -> None:
        """Return singular 'test' when count is 1."""
        result = formatting.pluralize_test(1)
        assert result == 'test'

    def it_returns_tests_for_count_of_zero(self) -> None:
        """Return plural 'tests' when count is 0."""
        result = formatting.pluralize_test(0)
        assert result == 'tests'

    def it_returns_tests_for_count_of_two(self) -> None:
        """Return plural 'tests' when count is 2."""
        result = formatting.pluralize_test(2)
        assert result == 'tests'

    def it_returns_tests_for_large_count(self) -> None:
        """Return plural 'tests' when count is large."""
        result = formatting.pluralize_test(100)
        assert result == 'tests'


@pytest.mark.small
class DescribeFormatDistributionRow:
    """Test suite for format_distribution_row function."""

    def it_formats_row_with_singular_test(self) -> None:
        """Format row with singular 'test' when count is 1."""
        result = formatting.format_distribution_row('Small', 1, 5.5)
        assert result == '      Small      1 test  (5.50%)'

    def it_formats_row_with_plural_tests(self) -> None:
        """Format row with plural 'tests' when count is not 1."""
        result = formatting.format_distribution_row('Small', 10, 50.0)
        assert result == '      Small     10 tests (50.00%)'

    def it_formats_row_with_zero_tests(self) -> None:
        """Format row with plural 'tests' when count is 0."""
        result = formatting.format_distribution_row('Large', 0, 0.0)
        assert result == '      Large      0 tests (0.00%)'

    def it_formats_row_with_medium_size(self) -> None:
        """Format row for medium test size."""
        result = formatting.format_distribution_row('Medium', 5, 25.0)
        assert result == '      Medium     5 tests (25.00%)'

    def it_formats_row_with_xlarge_size(self) -> None:
        """Format row for xlarge test size."""
        result = formatting.format_distribution_row('XLarge', 2, 10.0)
        assert result == '      XLarge     2 tests (10.00%)'

    def it_formats_percentage_with_two_decimals(self) -> None:
        """Format percentage with exactly two decimal places."""
        result = formatting.format_distribution_row('Small', 7, 33.333333)
        assert '(33.33%)' in result

    def it_maintains_column_alignment(self) -> None:
        """Maintain consistent column alignment across different counts."""
        row1 = formatting.format_distribution_row('Small', 1, 5.0)
        row2 = formatting.format_distribution_row('Small', 100, 50.0)

        # Both rows should have the same structure before the count
        assert row1.startswith('      Small  ')
        assert row2.startswith('      Small  ')


@pytest.mark.small
class DescribeGetStatusMessage:
    """Test suite for get_status_message function."""

    def it_returns_success_message_for_good_distribution(self) -> None:
        """Return success message when distribution is within targets."""
        percentages = TestPercentages(small=80.0, medium=15.0, large=5.0, xlarge=0.0)

        lines = formatting.get_status_message(percentages)

        message = ' '.join(lines)
        assert 'Great job!' in message
        assert 'on track' in message

    def it_prioritizes_large_xlarge_warning(self) -> None:
        """Return large/xlarge warning when that percentage is too high."""
        percentages = TestPercentages(small=40.0, medium=20.0, large=30.0, xlarge=10.0)

        lines = formatting.get_status_message(percentages)

        message = ' '.join(lines)
        assert 'Large/XLarge tests are' in message
        assert '40%' in message  # 30 + 10 = 40
        assert 'too many complex tests' in message

    def it_returns_critical_small_warning_when_below_50_percent(self) -> None:
        """Return critical warning when small tests are below 50%."""
        percentages = TestPercentages(small=45.0, medium=50.0, large=5.0, xlarge=0.0)

        lines = formatting.get_status_message(percentages)

        message = ' '.join(lines)
        assert 'Small tests are only 45.00%' in message
        assert 'tests may be too complex' in message

    def it_returns_medium_warning_when_medium_too_high(self) -> None:
        """Return medium warning when medium tests exceed 20%."""
        # Need medium deviation > small deviation
        # medium_deviation = 25 - 20 = 5
        # small_deviation = 75 - 70 = 5 (equal, so medium wins due to if order)
        # Actually for medium to win, it needs to be > not >=, so let's make medium worse
        percentages = TestPercentages(small=72.0, medium=25.0, large=3.0, xlarge=0.0)

        lines = formatting.get_status_message(percentages)

        message = ' '.join(lines)
        assert 'Medium tests are 25.00%' in message
        assert 'test complexity is creeping up' in message

    def it_returns_moderate_small_warning_when_below_75_percent(self) -> None:
        """Return moderate warning when small tests are below 75% but above 50%."""
        # Need small deviation > 0 and large/xlarge <= 8%
        # large + xlarge = 15%, which is > 8%, so large/xlarge warning will fire first
        # Let's make large/xlarge acceptable
        percentages = TestPercentages(small=70.0, medium=15.0, large=13.0, xlarge=2.0)

        lines = formatting.get_status_message(percentages)

        message = ' '.join(lines)
        # Actually wait, 13+2 = 15% which is > 8%, so this will fail
        # Let me recalculate: we need large+xlarge <= 8%
        percentages = TestPercentages(small=70.0, medium=22.0, large=5.0, xlarge=3.0)
        lines = formatting.get_status_message(percentages)
        message = ' '.join(lines)

        # large+xlarge = 8%, small = 70% (deviation=5), medium = 22% (deviation=2)
        # medium_deviation < small_deviation, so small warning should fire
        assert 'Small tests are only 70.00%' in message
        assert 'tests may be too complex' in message

    def it_prioritizes_large_xlarge_over_small_issues(self) -> None:
        """Prioritize large/xlarge warning over small percentage issues."""
        # Both issues present, but large/xlarge should win
        percentages = TestPercentages(small=40.0, medium=10.0, large=40.0, xlarge=10.0)

        lines = formatting.get_status_message(percentages)

        message = ' '.join(lines)
        # Should show large/xlarge warning, not critical small warning
        assert 'Large/XLarge tests are' in message
        assert 'Small tests are only' not in message

    def it_prioritizes_critical_small_over_medium_issues(self) -> None:
        """Prioritize critical small warning over medium issues when large/xlarge is acceptable."""
        # Critical small (< 50%) with medium > 20% but large+xlarge <= 8%
        # small=45%, medium=49%, large+xlarge=6% (to sum to 100%)
        percentages = TestPercentages(small=45.0, medium=49.0, large=4.0, xlarge=2.0)

        lines = formatting.get_status_message(percentages)

        message = ' '.join(lines)
        # Should show critical small warning (prioritized over medium warning)
        assert 'Small tests are only 45.00%' in message

    def it_prioritizes_medium_over_moderate_small_issues(self) -> None:
        """Prioritize medium warning over moderate small issues when medium deviation is larger."""
        # Need medium_deviation > small_deviation
        # medium_deviation = medium - 20, small_deviation = 75 - small
        # Let's use: small=73%, medium=23%, large+xlarge=4%
        # medium_deviation = 3, small_deviation = 2, so medium wins
        percentages = TestPercentages(small=73.0, medium=23.0, large=3.0, xlarge=1.0)

        lines = formatting.get_status_message(percentages)

        message = ' '.join(lines)
        assert 'Medium tests are 23.00%' in message

    def it_returns_list_of_strings(self) -> None:
        """Return a list of strings suitable for line-by-line output."""
        percentages = TestPercentages(small=80.0, medium=15.0, large=5.0, xlarge=0.0)

        lines = formatting.get_status_message(percentages)

        assert isinstance(lines, list)
        assert all(isinstance(line, str) for line in lines)
        assert len(lines) > 0

    def it_handles_edge_case_at_exact_thresholds(self) -> None:
        """Return appropriate message when percentages are exactly at threshold boundaries."""
        # Exactly at the edge of acceptable range
        # small=75% is at MIN_SMALL_PCT, so small_deviation = 0
        # medium=20% is at MAX_MEDIUM_PCT, so medium_deviation = 0
        # Both deviations are 0, so should return success message
        percentages = TestPercentages(small=75.0, medium=20.0, large=5.0, xlarge=0.0)

        lines = formatting.get_status_message(percentages)

        message = ' '.join(lines)
        # Both deviations are 0, so success message
        assert 'Great job!' in message
