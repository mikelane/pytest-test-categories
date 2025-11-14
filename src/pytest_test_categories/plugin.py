"""Core plugin implementation."""

from __future__ import annotations

import warnings
from collections import defaultdict
from typing import (
    TYPE_CHECKING,
    Final,
)

import pytest
from pydantic import BaseModel

from pytest_test_categories import timing
from pytest_test_categories.adapters.pytest_adapter import (
    PytestItemAdapter,
    PytestWarningAdapter,
    TerminalReporterAdapter,
)
from pytest_test_categories.distribution.stats import (
    DistributionStats,
    TestPercentages,
)
from pytest_test_categories.reporting import TestSizeReport
from pytest_test_categories.services.test_discovery import TestDiscoveryService
from pytest_test_categories.timers import (
    WallTimer,
)
from pytest_test_categories.types import (
    TestSize,
    TestTimer,
    TimerState,
    TimingViolationError,
)

if TYPE_CHECKING:
    from collections.abc import Generator


MULTIPLE_MARKERS_ERROR: Final[str] = 'Test cannot have multiple size markers: {}'
DISTRIBUTION_WARNING: Final[str] = 'Test distribution does not meet targets: {}'
MAX_LARGE_XLARGE_PCT: Final[float] = 8.0
MIN_SMALL_PCT: Final[float] = 75.0
MAX_MEDIUM_PCT: Final[float] = 20.0
CRITICAL_SMALL_PCT: Final[float] = 50.0  # Threshold for severe warning


class PluginState(BaseModel):
    """Plugin state for a test session.

    This class manages the state for the entire test session and supports
    hexagonal architecture through dependency injection of the timer factory
    and test discovery service.

    The timer_factory allows tests to inject FakeTimer for deterministic
    testing while production uses WallTimer for actual timing.

    The test_discovery_service is created during pytest_configure and uses
    dependency injection to provide the warning system adapter.
    """

    model_config = {'arbitrary_types_allowed': True}

    active: bool = True
    distribution_stats: DistributionStats = DistributionStats()
    warned_tests: set[str] = set()
    test_size_report: TestSizeReport | None = None
    # Store timers per test item to avoid race conditions in parallel execution
    timers: dict[str, TestTimer] = {}
    # Timer factory for dependency injection (hexagonal architecture port)
    timer_factory: type[TestTimer] = WallTimer
    # Test discovery service for finding size markers (hexagonal architecture)
    test_discovery_service: TestDiscoveryService | None = None


def _get_session_state(config: pytest.Config) -> PluginState:
    """Get or create plugin state for the current session."""
    if not hasattr(config, '_test_categories_state'):
        config._test_categories_state = PluginState()  # type: ignore[attr-defined]  # noqa: SLF001
    return config._test_categories_state  # type: ignore[attr-defined,no-any-return]  # noqa: SLF001


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add plugin-specific command-line options."""
    group = parser.getgroup('test-categories')
    group.addoption(
        '--test-size-report',
        action='store',
        default=None,
        choices=[None, 'basic', 'detailed'],  # Added "basic" to valid choices
        nargs='?',
        const='basic',
        help='Generate a report of test sizes (basic or detailed)',
    )


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    """Register the plugin and markers."""
    session_state = _get_session_state(config)

    if not hasattr(config, 'distribution_stats'):
        config.distribution_stats = session_state.distribution_stats  # type: ignore[attr-defined]

    for size in TestSize:
        config.addinivalue_line('markers', f'{size.marker_name}: {size.description}')

    # Initialize the test discovery service with dependency injection
    if session_state.test_discovery_service is None:
        warning_system = PytestWarningAdapter()
        session_state.test_discovery_service = TestDiscoveryService(warning_system=warning_system)

    # Initialize the report if requested
    if config.getoption('--test-size-report') is not None:
        session_state.test_size_report = TestSizeReport()


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Count tests by size during collection and append size labels to test IDs.

    This hook uses the TestDiscoveryService to find test size markers and the
    PytestItemAdapter to work with test items through the port interface.
    This follows hexagonal architecture by depending on abstractions rather
    than concrete pytest implementations.
    """
    session_state = _get_session_state(config)
    discovery_service = session_state.test_discovery_service

    # Safety check - should never be None after pytest_configure
    if discovery_service is None:
        warning_system = PytestWarningAdapter()
        discovery_service = TestDiscoveryService(warning_system=warning_system)
        session_state.test_discovery_service = discovery_service

    # Count tests by size using the discovery service
    counts: dict[str, int] = defaultdict(int)
    for item in items:
        item_adapter = PytestItemAdapter(item)
        test_size = discovery_service.find_test_size(item_adapter)
        if test_size:
            counts[test_size.marker_name] += 1
            # Append size label to test node ID
            item_adapter.set_nodeid(f'{item_adapter.nodeid} {test_size.label}')

    # Update distribution stats with the counts
    config.distribution_stats = DistributionStats.update_counts(counts=counts)  # type: ignore[attr-defined,arg-type]


@pytest.hookimpl
def pytest_collection_finish(session: pytest.Session) -> None:
    """Validate test distribution after collection."""
    try:
        session.config.distribution_stats.validate_distribution()  # type: ignore[attr-defined]
    except ValueError as e:
        warnings.warn(DISTRIBUTION_WARNING.format(e), pytest.PytestWarning, stacklevel=2)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item: pytest.Item, nextitem: pytest.Item | None) -> Generator[None, None, None]:  # noqa: ARG001
    """Track test timing and collect report data.

    This hook uses the TestDiscoveryService to find test size markers and the
    PytestItemAdapter to work with test items through the port interface.
    """
    session_state = _get_session_state(item.config)
    discovery_service = session_state.test_discovery_service

    # Safety check - should never be None after pytest_configure
    if discovery_service is None:
        warning_system = PytestWarningAdapter()
        discovery_service = TestDiscoveryService(warning_system=warning_system)
        session_state.test_discovery_service = discovery_service

    # Determine test size for reporting using the discovery service
    if session_state.test_size_report is not None:
        item_adapter = PytestItemAdapter(item)
        test_size = discovery_service.find_test_size(item_adapter)
        # Add test to report (outcome will be updated later)
        session_state.test_size_report.add_test(item.nodeid, test_size)

    # Create a unique timer for this test item to avoid race conditions
    # Only create if one doesn't already exist (allows test mocking)
    # Uses injected timer_factory for hexagonal architecture (production: WallTimer, tests: FakeTimer)
    if item.nodeid not in session_state.timers:
        timer = session_state.timer_factory(state=TimerState.READY)
        session_state.timers[item.nodeid] = timer
    else:
        timer = session_state.timers[item.nodeid]

    try:
        timer.start()
        yield  # Let the test run
    finally:
        # Ensure timer is always stopped, even if test fails
        if timer.state == TimerState.RUNNING:
            timer.stop()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item) -> Generator[None, None, None]:
    """Modify test report to show size category and validate timing.

    This hook uses the TestDiscoveryService to find test size markers and the
    PytestItemAdapter to work with test items through the port interface.

    Note: This hook still emits warnings directly (not through the service) to
    maintain backward compatibility with the warning tracking in session_state.
    The service tracks its own warned_tests internally and is used during collection.
    """
    session_state = _get_session_state(item.config)
    discovery_service = session_state.test_discovery_service

    # Safety check - should never be None after pytest_configure
    if discovery_service is None:
        warning_system = PytestWarningAdapter()
        discovery_service = TestDiscoveryService(warning_system=warning_system)
        session_state.test_discovery_service = discovery_service

    # Use the discovery service to find test size
    item_adapter = PytestItemAdapter(item)
    test_size = discovery_service.find_test_size(item_adapter)

    outcome = yield
    report = outcome.get_result()  # type: ignore[attr-defined]

    # Only validate timing for tests in the call phase
    if test_size and report.when == 'call':
        timer = session_state.timers.get(item.nodeid)
        if timer and timer.state == TimerState.STOPPED:
            try:
                timing.validate(test_size, timer.duration())
            except TimingViolationError as e:
                report.longrepr = str(e)
                report.outcome = 'failed'

    # Update test report data if we're generating a report
    if session_state.test_size_report is not None and report.when == 'call':
        timer = session_state.timers.get(item.nodeid)
        try:
            # Use the report's timing information instead of the timer
            # This is more reliable for capturing the actual sleep times
            duration = report.duration if hasattr(report, 'duration') else None
            if duration is None and timer and timer.state == TimerState.STOPPED:
                duration = timer.duration()
        except (RuntimeError, ValueError):
            duration = None

        # Update test information in the report
        if duration is not None:
            session_state.test_size_report.test_durations[item.nodeid] = duration
        session_state.test_size_report.test_outcomes[item.nodeid] = report.outcome

        # Clean up the timer after use to prevent memory leaks
        if item.nodeid in session_state.timers:
            del session_state.timers[item.nodeid]


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
    """Add test size distribution summary to the terminal report.

    This hook uses the TerminalReporterAdapter to work with the terminal reporter
    through the port interface. This follows hexagonal architecture by depending on
    abstractions rather than concrete pytest implementations.
    """
    session_state = _get_session_state(terminalreporter.config)
    distribution_stats = terminalreporter.config.distribution_stats  # type: ignore[attr-defined]
    counts = distribution_stats.counts
    percentages = distribution_stats.calculate_percentages()

    # Use the adapter to write output through the port interface
    writer = TerminalReporterAdapter(terminalreporter)

    writer.write_section('Test Suite Distribution Summary', sep='=')
    writer.write_line('    Test Size Distribution:')

    for size, count, percentage in [
        ('Small', counts.small, percentages.small),
        ('Medium', counts.medium, percentages.medium),
        ('Large', counts.large, percentages.large),
        ('XLarge', counts.xlarge, percentages.xlarge),
    ]:
        writer.write_line(_format_distribution_row(size, count, percentage))

    # Write status message
    writer.write_line('')
    for line in _get_status_message(percentages):
        writer.write_line(line)

    writer.write_separator(sep='=')

    # Add test size report if requested
    if session_state.test_size_report is not None:
        report_type = terminalreporter.config.getoption('--test-size-report')
        if report_type == 'detailed':
            session_state.test_size_report.write_detailed_report(terminalreporter)
        else:
            session_state.test_size_report.write_basic_report(terminalreporter)
