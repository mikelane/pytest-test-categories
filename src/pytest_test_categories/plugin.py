"""Core plugin implementation."""

from __future__ import annotations

import sys
import warnings
from collections import defaultdict
from typing import (
    TYPE_CHECKING,
    Final,
    NamedTuple,
)

import pytest
from pydantic import BaseModel

from pytest_test_categories import timing
from pytest_test_categories.distribution.stats import (
    DistributionStats,
    TestPercentages,
)
from pytest_test_categories.timers import WallTimer
from pytest_test_categories.types import (
    TestSize,
    TestTimer,
    TimerState,
    TimingViolationError,
)

if TYPE_CHECKING:
    from collections.abc import (
        Generator,
        Iterator,
    )


class SizedItem(NamedTuple):
    """Test item with its associated size."""

    size: TestSize
    item: pytest.Item


MULTIPLE_MARKERS_ERROR: Final[str] = 'Test cannot have multiple size markers: {}'
DISTRIBUTION_WARNING: Final[str] = 'Test distribution does not meet targets: {}'
MAX_LARGE_XLARGE_PCT: Final[float] = 8.0
MIN_SMALL_PCT: Final[float] = 75.0
MAX_MEDIUM_PCT: Final[float] = 20.0
CRITICAL_SMALL_PCT: Final[float] = 50.0  # Threshold for severe warning


class PluginState(BaseModel):
    """Global plugin state."""

    active: bool = True
    timer: TestTimer = WallTimer(state=TimerState.READY)
    distribution_stats: DistributionStats = DistributionStats()
    warned_tests: set[str] = set()


state = PluginState()


def _iter_sized_items(items: list[pytest.Item]) -> Iterator[SizedItem]:
    """Iterate through test items yielding those with size markers.

    Args:
        items: List of test items to process.

    Yields:
        Pairs of (TestSize, Item) for items with size markers.

    """
    for item in items:
        found_sizes = [size for size in TestSize if item.get_closest_marker(size.marker_name)]

        if not found_sizes:
            if item.nodeid not in state.warned_tests:
                warnings.warn(
                    f'Test has no size marker: {item.nodeid}',
                    pytest.PytestWarning,
                    stacklevel=2,
                )
                state.warned_tests.add(item.nodeid)
            continue

        if len(found_sizes) > 1:
            raise pytest.UsageError(MULTIPLE_MARKERS_ERROR.format(', '.join(size.marker_name for size in found_sizes)))

        yield SizedItem(found_sizes[0], item)


def _count_tests_by_size(items: list[pytest.Item]) -> dict[str, int]:
    """Count the number of tests in each size category.

    Args:
        items: List of test items to count.

    Returns:
        Dictionary mapping size marker names to counts.

    """
    counts = defaultdict(int)
    for sized_item in _iter_sized_items(items):
        counts[sized_item.size.marker_name] += 1
    return counts


def pytest_configure(config: pytest.Config) -> None:
    """Register the plugin and markers."""
    if not hasattr(config, 'distribution_stats'):
        config.distribution_stats = state.distribution_stats

    for size in TestSize:
        config.addinivalue_line('markers', f'{size.marker_name}: {size.description}')


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Count tests by size during collection."""
    config.distribution_stats = DistributionStats.update_counts(counts=_count_tests_by_size(items))

    for sized_item in _iter_sized_items(items):
        sized_item.item._nodeid = f'{sized_item.item._nodeid} {sized_item.size.label}'  # noqa: SLF001


@pytest.hookimpl
def pytest_collection_finish(session: pytest.Session) -> None:
    """Validate test distribution after collection."""
    try:
        session.config.distribution_stats.validate_distribution()
    except ValueError as e:
        warnings.warn(DISTRIBUTION_WARNING.format(e), pytest.PytestWarning, stacklevel=2)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item: pytest.Item, nextitem: pytest.Item | None) -> Generator[None, None, None]:  # noqa: ARG001
    """Track test timing."""
    try:
        if state.timer is not None:
            # Reset timer state for each test
            state.timer.state = TimerState.READY
            state.timer.start()

        yield  # Let the test run

    finally:
        # Ensure timer is always stopped, even if test fails
        if state.timer is not None and state.timer.state == TimerState.RUNNING:
            state.timer.stop()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item) -> Generator[None, None, None]:
    """Modify test report to show size category and validate timing."""
    found_sizes = [size.marker_name for size in TestSize if item.get_closest_marker(size.marker_name)]

    if not found_sizes and item.nodeid not in state.warned_tests:
        warnings.warn(
            f'Test has no size marker: {item.nodeid}',
            pytest.PytestWarning,
            stacklevel=2,
        )
        state.warned_tests.add(item.nodeid)

    outcome = yield
    report = outcome.get_result()

    test_size = next(
        (size for size in TestSize if item.get_closest_marker(size.marker_name)),
        None,
    )

    # Only validate timing for tests in the call phase
    if test_size and report.when == 'call' and state.timer and state.timer.state == TimerState.STOPPED:
        try:
            timing.validate(test_size, state.timer.duration())
        except TimingViolationError:
            excinfo = sys.exc_info()
            report.longrepr = item.repr_failure(excinfo)
            report.outcome = 'failed'
            report.failed = True
            report.passed = False


def _pluralize_test(count: int) -> str:
    """Return 'test' or 'tests' based on count."""
    return 'test' if count == 1 else 'tests'


def _format_distribution_row(size: str, count: int, percentage: float) -> str:
    """Format a single row of the distribution table.

    Args:
        size: The test size category name
        count: Number of tests in this category
        percentage: Percentage of tests in this category

    Returns:
        Formatted row string

    """
    row_format = '      {:<8} {:>3} {:<5} ({:.2f}%)'
    return row_format.format(size, count, _pluralize_test(count), percentage)


LARGE_XLARGE_WARNING = """\
    Status: Warning! Distribution needs improvement:
      Large/XLarge tests are {large_xlarge_percentage:.0f}% of the suite (target: 2-8%)
      This indicates too many complex tests. Consider:
      • Breaking large tests into smaller focused tests
      • Moving test setup into fixtures
      • Using test parameterization for repeated scenarios
"""

CRITICAL_SMALL_WARNING = """\
    Status: Warning! Distribution needs improvement:
      Small tests are only {percentages.small:.2f}% of the suite (target: 75-85%)
      This indicates tests may be too complex. Consider:
      • Breaking down medium tests into smaller units
      • Testing more specific behaviors individually
      • Moving complex setup into fixtures or helpers
"""

MEDIUM_WARNING = """\
    Status: Warning! Distribution needs improvement:
      Medium tests are {percentages.medium:.2f}% of the suite (target: 10-20%)
      This suggests test complexity is creeping up. Consider:
      • Identifying shared setup that could be simplified
      • Looking for tests that could be split into smaller units
      • Reviewing test dependencies and fixture usage
"""

MODERATE_SMALL_WARNING = """\
    Status: Warning! Distribution needs improvement:
      Small tests are only {percentages.small:.2f}% of the suite (target: 75-85%)
      This indicates tests may be too complex. Consider:
      • Breaking down medium tests into smaller units
      • Testing more specific behaviors individually
      • Moving complex setup into fixtures or helpers
"""

SUCCESS_MESSAGE = """\
    Status: Great job! Your test distribution is on track.
"""


def _get_status_message(percentages: TestPercentages) -> list[str]:
    """Get the status message based on distribution percentages.

    Args:
        percentages: The current test distribution percentages

    Returns:
        List of lines to display

    """
    large_xlarge_percentage = percentages.large + percentages.xlarge

    # Check for most severe issues first
    if large_xlarge_percentage > MAX_LARGE_XLARGE_PCT:
        return LARGE_XLARGE_WARNING.format(large_xlarge_percentage=large_xlarge_percentage).splitlines()

    # If small tests are way below target (>25% below minimum), that's the primary issue
    if percentages.small < CRITICAL_SMALL_PCT:
        return CRITICAL_SMALL_WARNING.format(percentages=percentages).splitlines()

    # If medium tests are significantly over target or small tests moderately under, report the worse deviation
    small_deviation = MIN_SMALL_PCT - percentages.small if percentages.small < MIN_SMALL_PCT else 0
    medium_deviation = percentages.medium - MAX_MEDIUM_PCT if percentages.medium > MAX_MEDIUM_PCT else 0

    if medium_deviation > small_deviation:
        return MEDIUM_WARNING.format(percentages=percentages).splitlines()
    if small_deviation > 0:
        return MODERATE_SMALL_WARNING.format(percentages=percentages).splitlines()

    return SUCCESS_MESSAGE.splitlines()


@pytest.hookimpl
def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    """Add test size distribution summary to the terminal report."""
    distribution_stats = terminalreporter.config.distribution_stats
    counts = distribution_stats.counts
    percentages = distribution_stats.calculate_percentages()

    terminalreporter.section('Test Suite Distribution Summary', sep='=')
    terminalreporter.write_line('    Test Size Distribution:')

    for size, count, percentage in [
        ('Small', counts.small, percentages.small),
        ('Medium', counts.medium, percentages.medium),
        ('Large', counts.large, percentages.large),
        ('XLarge', counts.xlarge, percentages.xlarge),
    ]:
        terminalreporter.write_line(_format_distribution_row(size, count, percentage))

    # Write status message
    terminalreporter.write_line('')
    for line in _get_status_message(percentages):
        terminalreporter.write_line(line)

    terminalreporter.write_sep('=')
