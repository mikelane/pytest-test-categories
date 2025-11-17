"""Formatting utilities for test distribution reports.

This module provides pure functions for formatting test distribution
data for terminal output. All functions are testable without pytest
dependencies.

These utilities follow functional programming principles:
- Pure functions with no side effects
- Depend only on input parameters
- Return formatted strings
- Fully testable with simple assertions

Example:
    >>> pluralize_test(1)
    'test'
    >>> pluralize_test(5)
    'tests'
    >>> format_distribution_row('Small', 10, 50.0)
    '      Small      10 tests (50.00%)'

"""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Final,
)

if TYPE_CHECKING:
    from pytest_test_categories.distribution.stats import TestPercentages

# Distribution thresholds for status messages
MAX_LARGE_XLARGE_PCT: Final[float] = 8.0
MIN_SMALL_PCT: Final[float] = 75.0
MAX_MEDIUM_PCT: Final[float] = 20.0
CRITICAL_SMALL_PCT: Final[float] = 50.0  # Threshold for severe warning

# Status message templates
LARGE_XLARGE_WARNING: Final[str] = """\
    Status: Warning! Distribution needs improvement:
      Large/XLarge tests are {large_xlarge_percentage:.0f}% of the suite (target: 2-8%)
      This indicates too many complex tests. Consider:
      • Breaking large tests into smaller focused tests
      • Moving test setup into fixtures
      • Using test parameterization for repeated scenarios
"""

CRITICAL_SMALL_WARNING: Final[str] = """\
    Status: Warning! Distribution needs improvement:
      Small tests are only {small:.2f}% of the suite (target: 75-85%)
      This indicates tests may be too complex. Consider:
      • Breaking down medium tests into smaller units
      • Testing more specific behaviors individually
      • Moving complex setup into fixtures or helpers
"""

MEDIUM_WARNING: Final[str] = """\
    Status: Warning! Distribution needs improvement:
      Medium tests are {medium:.2f}% of the suite (target: 10-20%)
      This suggests test complexity is creeping up. Consider:
      • Identifying shared setup that could be simplified
      • Looking for tests that could be split into smaller units
      • Reviewing test dependencies and fixture usage
"""

MODERATE_SMALL_WARNING: Final[str] = """\
    Status: Warning! Distribution needs improvement:
      Small tests are only {small:.2f}% of the suite (target: 75-85%)
      This indicates tests may be too complex. Consider:
      • Breaking down medium tests into smaller units
      • Testing more specific behaviors individually
      • Moving complex setup into fixtures or helpers
"""

SUCCESS_MESSAGE: Final[str] = """\
    Status: Great job! Your test distribution is on track.
"""


def pluralize_test(count: int) -> str:
    """Return 'test' or 'tests' based on count.

    This is a pure function that returns the correct singular or plural
    form of 'test' based on the count value.

    Args:
        count: The number of tests.

    Returns:
        'test' if count is 1, 'tests' otherwise.

    Example:
        >>> pluralize_test(1)
        'test'
        >>> pluralize_test(0)
        'tests'
        >>> pluralize_test(5)
        'tests'

    """
    return 'test' if count == 1 else 'tests'


def format_distribution_row(size: str, count: int, percentage: float) -> str:
    """Format a single row of the distribution table.

    This is a pure function that formats a distribution row with consistent
    spacing and formatting.

    Args:
        size: The test size category name (e.g., 'Small', 'Medium').
        count: Number of tests in this category.
        percentage: Percentage of tests in this category.

    Returns:
        Formatted row string with fixed-width columns.

    Example:
        >>> format_distribution_row('Small', 10, 50.0)
        '      Small      10 tests (50.00%)'
        >>> format_distribution_row('Medium', 1, 5.5)
        '      Medium      1 test  (5.50%)'

    """
    row_format = '      {:<8} {:>3} {:<5} ({:.2f}%)'
    return row_format.format(size, count, pluralize_test(count), percentage)


def get_status_message(percentages: TestPercentages) -> list[str]:
    """Get the status message based on distribution percentages.

    This is a pure function that determines which status message to display
    based on the distribution percentages. It prioritizes the most severe
    deviation from target distribution.

    The priority order is:
    1. Large/XLarge percentage too high (>8%)
    2. Small percentage critically low (<50%)
    3. Medium percentage too high (>20%)
    4. Small percentage moderately low (<75%)
    5. All good (success message)

    Args:
        percentages: The current test distribution percentages.

    Returns:
        List of message lines to display (suitable for join or iteration).

    Example:
        >>> from pytest_test_categories.distribution.stats import TestPercentages
        >>> percentages = TestPercentages(small=80.0, medium=15.0, large=5.0, xlarge=0.0)
        >>> lines = get_status_message(percentages)
        >>> 'Great job!' in ' '.join(lines)
        True

    """
    large_xlarge_percentage = percentages.large + percentages.xlarge

    # Check for most severe issues first
    if large_xlarge_percentage > MAX_LARGE_XLARGE_PCT:
        return LARGE_XLARGE_WARNING.format(large_xlarge_percentage=large_xlarge_percentage).splitlines()

    # If small tests are way below target (>25% below minimum), that's the primary issue
    if percentages.small < CRITICAL_SMALL_PCT:
        return CRITICAL_SMALL_WARNING.format(small=percentages.small).splitlines()

    # If medium tests are significantly over target or small tests moderately under, report the worse deviation
    small_deviation = MIN_SMALL_PCT - percentages.small if percentages.small < MIN_SMALL_PCT else 0
    medium_deviation = percentages.medium - MAX_MEDIUM_PCT if percentages.medium > MAX_MEDIUM_PCT else 0

    if medium_deviation > small_deviation:
        return MEDIUM_WARNING.format(medium=percentages.medium).splitlines()
    if small_deviation > 0:
        return MODERATE_SMALL_WARNING.format(small=percentages.small).splitlines()

    return SUCCESS_MESSAGE.splitlines()
