"""Core plugin implementation.

This module provides the pytest plugin entry point and hook implementations.
It follows hexagonal architecture by orchestrating services and adapters
rather than containing business logic.

The plugin's sole responsibility is:
- Registering pytest hooks
- Orchestrating calls to services through ports
- Managing session lifecycle

All business logic is delegated to services:
- TestDiscoveryService: Finding test size markers
- TimingValidationService: Validating test timing
- DistributionValidationService: Validating distribution
- TestReportingService: Managing test reports

All pytest interactions go through adapters:
- PytestConfigAdapter: Config state management
- PytestItemAdapter: Test item abstraction
- PytestWarningAdapter: Warning system
- TerminalReporterAdapter: Terminal output

This design makes the hooks thin orchestration layers (5-15 lines each)
that are easy to understand and maintain.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

import pytest

from pytest_test_categories.adapters.pytest_adapter import (
    PytestConfigAdapter,
    PytestItemAdapter,
    PytestWarningAdapter,
    TerminalReporterAdapter,
)
from pytest_test_categories.distribution.stats import DistributionStats
from pytest_test_categories.services.distribution_validation import DistributionValidationService
from pytest_test_categories.services.test_discovery import TestDiscoveryService
from pytest_test_categories.services.test_reporting import TestReportingService
from pytest_test_categories.services.timing_validation import TimingValidationService
from pytest_test_categories.timers import WallTimer
from pytest_test_categories.types import (
    TestSize,
    TimerState,
    TimingViolationError,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    import pytest_test_categories.types


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add plugin-specific command-line options.

    This hook registers the --test-size-report option that controls
    whether and how test size reports are generated.

    Args:
        parser: The pytest command-line option parser.

    """
    group = parser.getgroup('test-categories')
    group.addoption(
        '--test-size-report',
        action='store',
        default=None,
        choices=[None, 'basic', 'detailed'],
        nargs='?',
        const='basic',
        help='Generate a report of test sizes (basic or detailed)',
    )


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    """Register the plugin and markers.

    This hook:
    1. Initializes plugin state through ConfigStatePort
    2. Registers size markers dynamically from TestSize enum
    3. Initializes TestDiscoveryService with WarningSystemPort
    4. Creates TestSizeReport if requested

    Args:
        config: The pytest configuration object.

    """
    # Wrap config in adapter to access state through port
    config_adapter = PytestConfigAdapter(config)
    session_state = config_adapter.get_plugin_state()

    # Initialize defaults if not set
    if session_state.distribution_stats is None:
        session_state.distribution_stats = DistributionStats()
    if session_state.timer_factory is None:
        session_state.timer_factory = WallTimer

    # Initialize distribution stats on config if not present
    if not hasattr(config, 'distribution_stats'):
        config.distribution_stats = session_state.distribution_stats  # type: ignore[attr-defined]

    # Register size markers dynamically
    for size in TestSize:
        config_adapter.add_marker(f'{size.marker_name}: {size.description}')

    # Initialize test discovery service with warning system
    if session_state.test_discovery_service is None:
        warning_system = PytestWarningAdapter()
        session_state.test_discovery_service = TestDiscoveryService(warning_system=warning_system)

    # Initialize test size report if requested
    reporting_service = TestReportingService()
    report_option = config_adapter.get_option('--test-size-report')
    session_state.test_size_report = reporting_service.create_report_if_requested(report_option)


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Count tests by size during collection and append size labels to test IDs.

    This hook:
    1. Uses TestDiscoveryService to find test size markers
    2. Counts tests by size category
    3. Appends size labels to test node IDs (e.g., [SMALL])
    4. Updates distribution stats on config

    Args:
        config: The pytest configuration object.
        items: List of collected test items.

    """
    config_adapter = PytestConfigAdapter(config)
    session_state = config_adapter.get_plugin_state()
    discovery_service = _ensure_discovery_service(session_state)

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
    config.distribution_stats = config.distribution_stats.update_counts(counts=counts)


@pytest.hookimpl
def pytest_collection_finish(session: pytest.Session) -> None:
    """Validate test distribution after collection.

    This hook uses DistributionValidationService to validate that the
    test suite distribution meets target percentages.

    Args:
        session: The pytest session object.

    """
    config_adapter = PytestConfigAdapter(session.config)
    stats = config_adapter.get_distribution_stats()
    warning_system = PytestWarningAdapter()
    validation_service = DistributionValidationService()
    validation_service.validate_distribution(stats, warning_system)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item: pytest.Item, nextitem: pytest.Item | None) -> Generator[None, None, None]:  # noqa: ARG001
    """Track test timing and collect report data.

    This hook:
    1. Adds test to report if reporting is enabled
    2. Creates and starts a timer for the test
    3. Ensures timer is stopped in finally block

    Args:
        item: The test item to run.
        nextitem: The next test item (unused).

    Yields:
        Control to pytest to run the test.

    """
    config_adapter = PytestConfigAdapter(item.config)
    session_state = config_adapter.get_plugin_state()
    discovery_service = _ensure_discovery_service(session_state)

    # Add test to report if reporting is enabled
    if session_state.test_size_report is not None:
        item_adapter = PytestItemAdapter(item)
        test_size = discovery_service.find_test_size(item_adapter)
        reporting_service = TestReportingService()
        reporting_service.add_test_to_report(session_state.test_size_report, item.nodeid, test_size)

    # Create and start timer for this test
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

    This hook:
    1. Uses TestDiscoveryService to find test size
    2. Validates timing using TimingValidationService
    3. Updates test report with timing violations
    4. Updates test size report with outcome and duration

    Args:
        item: The test item that ran.

    Yields:
        Control to pytest to generate the report.

    """
    config_adapter = PytestConfigAdapter(item.config)
    session_state = config_adapter.get_plugin_state()
    discovery_service = _ensure_discovery_service(session_state)

    # Find test size
    item_adapter = PytestItemAdapter(item)
    test_size = discovery_service.find_test_size(item_adapter)

    outcome = yield
    report = outcome.get_result()  # type: ignore[attr-defined]

    # Only validate timing for tests in the call phase
    if test_size and report.when == 'call':
        timer = session_state.timers.get(item.nodeid)
        timing_service = TimingValidationService()
        duration = timing_service.get_test_duration(
            timer,
            report.duration if hasattr(report, 'duration') else None,
        )
        if duration is not None:
            try:
                timing_service.validate_timing(test_size, duration)
            except TimingViolationError as e:
                report.longrepr = str(e)
                report.outcome = 'failed'

    # Update test report data if we're generating a report
    if session_state.test_size_report is not None and report.when == 'call':
        timer = session_state.timers.get(item.nodeid)
        timing_service = TimingValidationService()
        duration = timing_service.get_test_duration(
            timer,
            report.duration if hasattr(report, 'duration') else None,
        )
        reporting_service = TestReportingService()
        reporting_service.update_test_result(
            session_state.test_size_report,
            item.nodeid,
            report.outcome,
            duration,
        )

        # Clean up the timer after use to prevent memory leaks
        timing_service.cleanup_timer(session_state.timers, item.nodeid)


@pytest.hookimpl
def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    """Add test size distribution summary to the terminal report.

    This hook:
    1. Uses TestReportingService to write distribution summary
    2. Writes optional test size report (basic or detailed)

    Args:
        terminalreporter: The pytest terminal reporter.

    """
    config_adapter = PytestConfigAdapter(terminalreporter.config)
    session_state = config_adapter.get_plugin_state()
    stats = config_adapter.get_distribution_stats()

    # Write distribution summary through the port interface
    writer = TerminalReporterAdapter(terminalreporter)
    reporting_service = TestReportingService()
    reporting_service.write_distribution_summary(stats, writer)

    # Add test size report if requested
    if session_state.test_size_report is not None:
        report_type = config_adapter.get_option('--test-size-report')
        if report_type == 'detailed':
            session_state.test_size_report.write_detailed_report(terminalreporter)
        else:
            session_state.test_size_report.write_basic_report(terminalreporter)


def _ensure_discovery_service(session_state: pytest_test_categories.types.PluginState) -> TestDiscoveryService:
    """Ensure TestDiscoveryService is initialized.

    This is a helper function that creates the discovery service if it
    doesn't exist. This should never be needed in normal operation (the
    service is created in pytest_configure), but provides a safety net.

    Args:
        session_state: The plugin state containing the discovery service.

    Returns:
        The TestDiscoveryService instance.

    """
    if session_state.test_discovery_service is None:
        warning_system = PytestWarningAdapter()
        session_state.test_discovery_service = TestDiscoveryService(warning_system=warning_system)
    return session_state.test_discovery_service


# Import for type annotation in helper function
