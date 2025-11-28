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

import tempfile
from collections import defaultdict
from contextlib import ExitStack
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    cast,
)

import pytest

from pytest_test_categories.adapters.filesystem import FilesystemPatchingBlocker
from pytest_test_categories.adapters.network import SocketPatchingNetworkBlocker
from pytest_test_categories.adapters.pytest_adapter import (
    PytestConfigAdapter,
    PytestItemAdapter,
    PytestWarningAdapter,
    TerminalReporterAdapter,
)
from pytest_test_categories.distribution.stats import DistributionStats
from pytest_test_categories.ports.network import EnforcementMode
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
    from pytest_test_categories.reporting import TestSizeReport

# Valid enforcement modes for ini option validation
_VALID_ENFORCEMENT_MODES = {'off', 'warn', 'strict'}


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add plugin-specific command-line options.

    This hook registers the --test-size-report option that controls
    whether and how test size reports are generated, the
    --test-categories-enforcement option for resource blocking control,
    and the --test-categories-allowed-paths option for filesystem access.

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
    group.addoption(
        '--test-categories-enforcement',
        action='store',
        default=None,
        choices=['off', 'warn', 'strict'],
        help='Set enforcement mode for test hermeticity (off, warn, strict). Overrides ini option.',
    )
    group.addoption(
        '--test-categories-allowed-paths',
        action='store',
        default=None,
        help='Comma-separated paths allowed for filesystem access in small tests. Extends ini option.',
    )

    parser.addini(
        'test_categories_enforcement',
        help='Enforcement mode for test hermeticity: off (default), warn, or strict',
        default='off',
    )
    parser.addini(
        'test_categories_allowed_paths',
        type='pathlist',
        help='Paths allowed for filesystem access in small tests (extends default temp paths)',
        default=[],
    )


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    """Register markers and initialize plugin state.

    Args:
        config: The pytest configuration object.

    """
    config_adapter = PytestConfigAdapter(config)
    session_state = config_adapter.get_plugin_state()

    # Initialize defaults
    if session_state.distribution_stats is None:
        session_state.distribution_stats = DistributionStats()
    if session_state.timer_factory is None:
        session_state.timer_factory = WallTimer
    if not hasattr(config, 'distribution_stats'):
        config.distribution_stats = session_state.distribution_stats  # type: ignore[attr-defined]

    # Register size markers
    for size in TestSize:
        config_adapter.add_marker(f'{size.marker_name}: {size.description}')

    # Initialize discovery service
    if session_state.test_discovery_service is None:
        session_state.test_discovery_service = TestDiscoveryService(PytestWarningAdapter())

    # Initialize reporting if requested
    report_option = config_adapter.get_option('--test-size-report')
    session_state.test_size_report = TestReportingService().create_report_if_requested(report_option)


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Count tests by size and append size labels to test IDs."""
    config_adapter = PytestConfigAdapter(config)
    session_state = config_adapter.get_plugin_state()
    discovery_service = _ensure_discovery_service(session_state)

    # Count tests by size using the discovery service
    counts: dict[TestSize, int] = defaultdict(int)
    for item in items:
        item_adapter = PytestItemAdapter(item)
        test_size = discovery_service.find_test_size(item_adapter)
        if test_size:
            counts[test_size] += 1
            # Append size label to test node ID
            item_adapter.set_nodeid(f'{item_adapter.nodeid} {test_size.label}')

    # Update distribution stats with the counts
    current_stats = config_adapter.get_distribution_stats()
    updated_stats = current_stats.update_counts(counts=counts)
    config_adapter.set_distribution_stats(updated_stats)


@pytest.hookimpl
def pytest_collection_finish(session: pytest.Session) -> None:
    """Validate test distribution after collection."""
    config_adapter = PytestConfigAdapter(session.config)
    stats = config_adapter.get_distribution_stats()
    warning_system = PytestWarningAdapter()
    validation_service = DistributionValidationService()
    validation_service.validate_distribution(stats, warning_system)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item: pytest.Item, nextitem: pytest.Item | None) -> Generator[None, None, None]:  # noqa: ARG001
    """Track test timing during execution."""
    config_adapter = PytestConfigAdapter(item.config)
    session_state = config_adapter.get_plugin_state()
    discovery_service = _ensure_discovery_service(session_state)

    # Add test to report if reporting is enabled
    if session_state.test_size_report is not None:
        item_adapter = PytestItemAdapter(item)
        test_size = discovery_service.find_test_size(item_adapter)
        reporting_service = TestReportingService()
        test_report = cast('TestSizeReport', session_state.test_size_report)
        reporting_service.add_test_to_report(test_report, item.nodeid, test_size)

    # Create and start timer for this test
    if item.nodeid not in session_state.timers:
        # Type narrowing: timer_factory is guaranteed to be set in pytest_configure
        if session_state.timer_factory is None:
            msg = 'timer_factory must be initialized in pytest_configure'
            raise RuntimeError(msg)
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
def pytest_runtest_call(item: pytest.Item) -> Generator[None, None, None]:
    """Block network and filesystem access for small tests during execution.

    This hook enforces resource isolation for small tests based on the
    enforcement configuration. When enforcement is enabled (strict or warn):
    - Small tests will have network access blocked
    - Small tests will have filesystem access blocked (except allowed paths)
    - Medium/large/xlarge tests are not affected

    Uses ExitStack pattern to manage both network and filesystem blockers
    together, ensuring proper cleanup even if exceptions occur.

    Args:
        item: The test item being executed.

    Yields:
        Control to pytest to run the test.

    """
    enforcement_mode = _get_enforcement_mode(item.config)

    if enforcement_mode == EnforcementMode.OFF:
        yield
        return

    config_adapter = PytestConfigAdapter(item.config)
    session_state = config_adapter.get_plugin_state()
    discovery_service = _ensure_discovery_service(session_state)
    item_adapter = PytestItemAdapter(item)
    test_size = discovery_service.find_test_size(item_adapter)

    if test_size != TestSize.SMALL:
        yield
        return

    # Use ExitStack for combined resource blocking
    with ExitStack() as stack:
        # Activate network blocker
        network_blocker = _get_network_blocker(item.config)
        network_blocker.current_test_nodeid = item.nodeid
        network_blocker.activate(test_size, enforcement_mode)
        stack.callback(_safe_deactivate_network, network_blocker)

        # Activate filesystem blocker
        filesystem_blocker = _get_filesystem_blocker(item.config)
        filesystem_blocker.current_test_nodeid = item.nodeid
        allowed_paths = _get_allowed_paths(item)
        filesystem_blocker.activate(test_size, enforcement_mode, allowed_paths)
        stack.callback(_safe_deactivate_filesystem, filesystem_blocker)

        yield


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item) -> Generator[None, None, None]:
    """Validate timing and update test reports.

    Args:
        item: The test item that ran.

    Yields:
        Control to pytest to generate the report.

    """
    config_adapter = PytestConfigAdapter(item.config)
    session_state = config_adapter.get_plugin_state()
    discovery_service = _ensure_discovery_service(session_state)
    item_adapter = PytestItemAdapter(item)
    test_size = discovery_service.find_test_size(item_adapter)

    outcome = yield
    report = outcome.get_result()  # type: ignore[attr-defined]

    # Only process call phase reports
    if report.when != 'call':
        return

    # Get duration once for both validation and reporting
    timer = session_state.timers.get(item.nodeid)
    timing_service = TimingValidationService()
    duration = timing_service.get_test_duration(
        timer,
        report.duration if hasattr(report, 'duration') else None,
    )

    # Validate timing if test has a size marker
    if test_size and duration is not None:
        try:
            timing_service.validate_timing(test_size, duration)
        except TimingViolationError as e:
            report.longrepr = str(e)
            report.outcome = 'failed'

    # Update test size report if enabled
    if session_state.test_size_report is not None:
        test_report = cast('TestSizeReport', session_state.test_size_report)
        TestReportingService().update_test_result(
            test_report,
            item.nodeid,
            report.outcome,
            duration,
        )
        timing_service.cleanup_timer(session_state.timers, item.nodeid)


@pytest.hookimpl
def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    """Write distribution summary and optional size report."""
    config_adapter = PytestConfigAdapter(terminalreporter.config)
    session_state = config_adapter.get_plugin_state()
    stats = config_adapter.get_distribution_stats()

    # Write distribution summary through the port interface
    writer = TerminalReporterAdapter(terminalreporter)
    reporting_service = TestReportingService()
    reporting_service.write_distribution_summary(stats, writer)

    # Add test size report if requested
    if session_state.test_size_report is not None:
        test_report = cast('TestSizeReport', session_state.test_size_report)
        report_type = config_adapter.get_option('--test-size-report')
        if report_type == 'detailed':
            test_report.write_detailed_report(terminalreporter)
        else:
            test_report.write_basic_report(terminalreporter)


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
    return cast('TestDiscoveryService', session_state.test_discovery_service)


def _get_enforcement_mode(config: pytest.Config) -> EnforcementMode:
    """Get the enforcement mode from configuration.

    CLI option takes precedence over ini setting.

    Args:
        config: The pytest configuration object.

    Returns:
        The EnforcementMode enum value.

    """
    cli_value = config.getoption('--test-categories-enforcement', default=None)
    if cli_value is not None:
        return EnforcementMode(cli_value)

    ini_value = config.getini('test_categories_enforcement')
    if ini_value and ini_value in _VALID_ENFORCEMENT_MODES:
        return EnforcementMode(ini_value)

    return EnforcementMode.OFF


def _get_network_blocker(config: pytest.Config) -> SocketPatchingNetworkBlocker:
    """Get or create the network blocker instance.

    The blocker is stored on the config object to ensure proper lifecycle
    management across test execution.

    Args:
        config: The pytest configuration object.

    Returns:
        The SocketPatchingNetworkBlocker instance.

    """
    blocker_attr = '_test_categories_network_blocker'
    if not hasattr(config, blocker_attr):
        blocker = SocketPatchingNetworkBlocker()
        setattr(config, blocker_attr, blocker)
    return cast('SocketPatchingNetworkBlocker', getattr(config, blocker_attr))


def _get_filesystem_blocker(config: pytest.Config) -> FilesystemPatchingBlocker:
    """Get or create the filesystem blocker instance.

    The blocker is stored on the config object to ensure proper lifecycle
    management across test execution.

    Args:
        config: The pytest configuration object.

    Returns:
        The FilesystemPatchingBlocker instance.

    """
    blocker_attr = '_test_categories_filesystem_blocker'
    if not hasattr(config, blocker_attr):
        blocker = FilesystemPatchingBlocker()
        setattr(config, blocker_attr, blocker)
    return cast('FilesystemPatchingBlocker', getattr(config, blocker_attr))


def _safe_deactivate_network(blocker: SocketPatchingNetworkBlocker) -> None:
    """Safely deactivate network blocker, handling edge cases.

    This function is used as a callback in ExitStack to ensure cleanup.

    Args:
        blocker: The network blocker to deactivate.

    """
    if blocker.state.value == 'active':
        blocker.deactivate()


def _safe_deactivate_filesystem(blocker: FilesystemPatchingBlocker) -> None:
    """Safely deactivate filesystem blocker, handling edge cases.

    This function is used as a callback in ExitStack to ensure cleanup.

    Args:
        blocker: The filesystem blocker to deactivate.

    """
    if blocker.state.value == 'active':
        blocker.deactivate()


def _get_allowed_paths(item: pytest.Item) -> frozenset[Path]:
    """Get the set of allowed filesystem paths for a test item.

    This function computes the allowed paths from:
    1. System temp directory (always allowed)
    2. pytest's basetemp directory (where tmp_path is created)
    3. User-configured paths from ini file
    4. User-configured paths from CLI option

    Args:
        item: The test item being executed.

    Returns:
        A frozenset of Path objects that are allowed for filesystem access.

    """
    config = item.config
    allowed: set[Path] = set()

    # System temp directory is always allowed
    allowed.add(Path(tempfile.gettempdir()).resolve())

    # pytest's basetemp (where tmp_path fixture creates directories)
    basetemp = config.getoption('basetemp', default=None)
    if basetemp:
        allowed.add(Path(basetemp).resolve())

    # User-configured allowed paths from ini file (pathlist type)
    ini_paths = config.getini('test_categories_allowed_paths')
    if ini_paths:
        for ini_path in ini_paths:
            # ini pathlist returns Path objects, resolve them
            allowed.add(Path(ini_path).resolve())

    # User-configured allowed paths from CLI (comma-separated string)
    cli_paths = config.getoption('--test-categories-allowed-paths', default=None)
    if cli_paths:
        for path_str in cli_paths.split(','):
            stripped_path = path_str.strip()
            if stripped_path:
                allowed.add(Path(stripped_path).expanduser().resolve())

    return frozenset(allowed)
