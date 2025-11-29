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
from importlib.metadata import version
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    cast,
)

import pytest

from pytest_test_categories.adapters.database import DatabasePatchingBlocker
from pytest_test_categories.adapters.filesystem import FilesystemPatchingBlocker
from pytest_test_categories.adapters.network import SocketPatchingNetworkBlocker
from pytest_test_categories.adapters.process import SubprocessPatchingBlocker
from pytest_test_categories.adapters.pytest_adapter import (
    PytestConfigAdapter,
    PytestItemAdapter,
    PytestWarningAdapter,
    TerminalReporterAdapter,
)
from pytest_test_categories.adapters.threading import ThreadPatchingMonitor
from pytest_test_categories.distribution.stats import DistributionStats
from pytest_test_categories.json_report import JsonReport
from pytest_test_categories.ports.network import EnforcementMode
from pytest_test_categories.services.distribution_validation import (
    DistributionValidationService,
    DistributionViolationError,
)
from pytest_test_categories.services.test_discovery import TestDiscoveryService
from pytest_test_categories.services.test_reporting import TestReportingService
from pytest_test_categories.services.timing_validation import TimingValidationService
from pytest_test_categories.timers import WallTimer
from pytest_test_categories.timing import (
    DEFAULT_TIME_LIMIT_CONFIG,
    TimeLimitConfig,
)
from pytest_test_categories.types import (
    TestSize,
    TimerState,
    TimingViolationError,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    import pytest_test_categories.types
    from pytest_test_categories.adapters.pytest_adapter import PytestConfigAdapter as PytestConfigAdapterType
    from pytest_test_categories.distribution.stats import DistributionStats as DistributionStatsType
    from pytest_test_categories.reporting import TestSizeReport

# Package version for JSON report
PLUGIN_VERSION = version('pytest-test-categories')

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
        choices=[None, 'basic', 'detailed', 'json'],
        nargs='?',
        const='basic',
        help='Generate a report of test sizes (basic, detailed, or json)',
    )
    group.addoption(
        '--test-size-report-file',
        action='store',
        default=None,
        help='Output file path for JSON report (requires --test-size-report=json)',
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

    # Distribution enforcement options
    group.addoption(
        '--test-categories-distribution-enforcement',
        action='store',
        default=None,
        choices=['off', 'warn', 'strict'],
        help='Set enforcement mode for distribution validation (off, warn, strict). Overrides ini option.',
    )
    parser.addini(
        'test_categories_distribution_enforcement',
        help='Enforcement mode for distribution validation: off (default), warn, or strict',
        default='off',
    )

    # Time limit configuration options
    # Individual CLI options for each size (override ini)
    group.addoption(
        '--test-categories-small-time-limit',
        action='store',
        type=float,
        default=None,
        help='Time limit in seconds for small tests (default: 1.0). Overrides ini option.',
    )
    group.addoption(
        '--test-categories-medium-time-limit',
        action='store',
        type=float,
        default=None,
        help='Time limit in seconds for medium tests (default: 300.0). Overrides ini option.',
    )
    group.addoption(
        '--test-categories-large-time-limit',
        action='store',
        type=float,
        default=None,
        help='Time limit in seconds for large tests (default: 900.0). Overrides ini option.',
    )
    group.addoption(
        '--test-categories-xlarge-time-limit',
        action='store',
        type=float,
        default=None,
        help='Time limit in seconds for xlarge tests (default: 900.0). Overrides ini option.',
    )

    # Individual ini options for each size
    parser.addini(
        'test_categories_small_time_limit',
        help='Time limit in seconds for small tests (default: 1.0)',
        default='',
    )
    parser.addini(
        'test_categories_medium_time_limit',
        help='Time limit in seconds for medium tests (default: 300.0)',
        default='',
    )
    parser.addini(
        'test_categories_large_time_limit',
        help='Time limit in seconds for large tests (default: 900.0)',
        default='',
    )
    parser.addini(
        'test_categories_xlarge_time_limit',
        help='Time limit in seconds for xlarge tests (default: 900.0)',
        default='',
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

    # Initialize time limit configuration from CLI and ini options
    if session_state.time_limit_config is None:
        session_state.time_limit_config = _get_time_limit_config(config)

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
    """Validate test distribution after collection.

    Uses the distribution enforcement mode to determine behavior:
    - OFF: Skip validation entirely
    - WARN: Emit warning if out of spec, allow build to continue
    - STRICT: Raise DistributionViolationError if out of spec

    Args:
        session: The pytest session object.

    Raises:
        pytest.UsageError: If enforcement mode is STRICT and distribution
            is outside acceptable range.

    """
    config_adapter = PytestConfigAdapter(session.config)
    stats = config_adapter.get_distribution_stats()
    warning_system = PytestWarningAdapter()
    validation_service = DistributionValidationService()
    enforcement_mode = _get_distribution_enforcement_mode(session.config)

    try:
        validation_service.validate_distribution(stats, warning_system, enforcement_mode)
    except DistributionViolationError as e:
        raise pytest.UsageError(str(e)) from e


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
    """Block resources based on test size during execution and monitor threading.

    This hook enforces resource isolation based on test size and enforcement
    configuration. When enforcement is enabled (strict or warn):

    Network access (based on Google's test size definitions):
    - Small tests: All network blocked (BLOCK_ALL)
    - Medium tests: Localhost only (LOCALHOST_ONLY)
    - Large/XLarge tests: Full network access (ALLOW_ALL)

    Filesystem and process isolation (small tests only):
    - Small tests: Filesystem access blocked (except allowed paths)
    - Small tests: Subprocess spawning blocked
    - Small tests: Database connections blocked
    - Small tests: Thread creation warnings emitted

    Note: Thread monitoring WARNS instead of blocking because many libraries
    use threading internally. Blocking would break legitimate test infrastructure.

    Uses ExitStack pattern to manage all resource blockers together,
    ensuring proper cleanup even if exceptions occur.

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

    # Large, XLarge, and unsized tests have no restrictions
    if test_size is None or test_size in (TestSize.LARGE, TestSize.XLARGE):
        yield
        return

    # Use ExitStack for combined resource blocking
    # At this point test_size is guaranteed to be SMALL or MEDIUM
    with ExitStack() as stack:
        # Network blocking applies to both small and medium tests
        # - Small: BLOCK_ALL (no network)
        # - Medium: LOCALHOST_ONLY (localhost only)
        network_blocker = _get_network_blocker(item.config)
        network_blocker.current_test_nodeid = item.nodeid
        network_blocker.activate(test_size, enforcement_mode)
        stack.callback(_safe_deactivate_network, network_blocker)

        # Filesystem and process blocking only applies to small tests
        if test_size == TestSize.SMALL:
            # Activate filesystem blocker
            filesystem_blocker = _get_filesystem_blocker(item.config)
            filesystem_blocker.current_test_nodeid = item.nodeid
            allowed_paths = _get_allowed_paths(item)
            filesystem_blocker.activate(test_size, enforcement_mode, allowed_paths)
            stack.callback(_safe_deactivate_filesystem, filesystem_blocker)

            # Activate process blocker
            process_blocker = _get_process_blocker(item.config)
            process_blocker.current_test_nodeid = item.nodeid
            process_blocker.activate(test_size, enforcement_mode)
            stack.callback(_safe_deactivate_process, process_blocker)

        # Activate database blocker
        database_blocker = _get_database_blocker(item.config)
        database_blocker.current_test_nodeid = item.nodeid
        database_blocker.activate(test_size, enforcement_mode)
        stack.callback(_safe_deactivate_database, database_blocker)

        # Activate thread monitor (warns instead of blocking)
        thread_monitor = _get_thread_monitor(item.config)
        thread_monitor.current_test_nodeid = item.nodeid
        thread_monitor.activate(test_size, enforcement_mode)
        stack.callback(_safe_deactivate_thread_monitor, thread_monitor)

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
            time_limit_config = cast('TimeLimitConfig', session_state.time_limit_config)
            timing_service.validate_timing(test_size, duration, config=time_limit_config)
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
        if report_type == 'json':
            _write_json_report(test_report, stats, config_adapter, terminalreporter)
        elif report_type == 'detailed':
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


def _get_distribution_enforcement_mode(config: pytest.Config) -> EnforcementMode:
    """Get the distribution enforcement mode from configuration.

    CLI option takes precedence over ini setting.

    Args:
        config: The pytest configuration object.

    Returns:
        The EnforcementMode enum value for distribution validation.

    """
    cli_value = config.getoption('--test-categories-distribution-enforcement', default=None)
    if cli_value is not None:
        return EnforcementMode(cli_value)

    ini_value = config.getini('test_categories_distribution_enforcement')
    if ini_value and ini_value in _VALID_ENFORCEMENT_MODES:
        return EnforcementMode(ini_value)

    return EnforcementMode.OFF


def _get_time_limit_config(config: pytest.Config) -> TimeLimitConfig:
    """Get the time limit configuration from CLI and ini options.

    CLI options take precedence over ini settings. Individual size options
    take precedence over the combined time_limits option.

    Priority (highest to lowest):
    1. CLI individual options (--test-categories-small-time-limit, etc.)
    2. Ini individual options (test_categories_small_time_limit, etc.)
    3. Default values from DEFAULT_TIME_LIMIT_CONFIG

    Args:
        config: The pytest configuration object.

    Returns:
        A TimeLimitConfig with the resolved time limits.

    Raises:
        ValueError: If the configured limits violate ordering constraints
            (small < medium < large <= xlarge).

    """
    # Start with defaults
    limits: dict[str, float] = {
        'small': DEFAULT_TIME_LIMIT_CONFIG.small,
        'medium': DEFAULT_TIME_LIMIT_CONFIG.medium,
        'large': DEFAULT_TIME_LIMIT_CONFIG.large,
        'xlarge': DEFAULT_TIME_LIMIT_CONFIG.xlarge,
    }

    # Size name mappings for option names
    sizes = ['small', 'medium', 'large', 'xlarge']

    # Override with ini values (lower priority)
    for size in sizes:
        ini_value = config.getini(f'test_categories_{size}_time_limit')
        if ini_value and ini_value.strip():
            limits[size] = float(ini_value)

    # Override with CLI values (highest priority)
    for size in sizes:
        cli_value = config.getoption(f'--test-categories-{size}-time-limit', default=None)
        if cli_value is not None:
            limits[size] = float(cli_value)

    return TimeLimitConfig(**limits)


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


def _get_process_blocker(config: pytest.Config) -> SubprocessPatchingBlocker:
    """Get or create the process blocker instance.

    The blocker is stored on the config object to ensure proper lifecycle
    management across test execution.

    Args:
        config: The pytest configuration object.

    Returns:
        The SubprocessPatchingBlocker instance.

    """
    blocker_attr = '_test_categories_process_blocker'
    if not hasattr(config, blocker_attr):
        blocker = SubprocessPatchingBlocker()
        setattr(config, blocker_attr, blocker)
    return cast('SubprocessPatchingBlocker', getattr(config, blocker_attr))


def _safe_deactivate_process(blocker: SubprocessPatchingBlocker) -> None:
    """Safely deactivate process blocker, handling edge cases.

    This function is used as a callback in ExitStack to ensure cleanup.

    Args:
        blocker: The process blocker to deactivate.

    """
    if blocker.state.value == 'active':
        blocker.deactivate()


def _get_database_blocker(config: pytest.Config) -> DatabasePatchingBlocker:
    """Get or create the database blocker instance.

    The blocker is stored on the config object to ensure proper lifecycle
    management across test execution.

    Args:
        config: The pytest configuration object.

    Returns:
        The DatabasePatchingBlocker instance.

    """
    blocker_attr = '_test_categories_database_blocker'
    if not hasattr(config, blocker_attr):
        blocker = DatabasePatchingBlocker()
        setattr(config, blocker_attr, blocker)
    return cast('DatabasePatchingBlocker', getattr(config, blocker_attr))


def _safe_deactivate_database(blocker: DatabasePatchingBlocker) -> None:
    """Safely deactivate database blocker, handling edge cases.

    This function is used as a callback in ExitStack to ensure cleanup.

    Args:
        blocker: The database blocker to deactivate.

    """
    if blocker.state.value == 'active':
        blocker.deactivate()


def _get_thread_monitor(config: pytest.Config) -> ThreadPatchingMonitor:
    """Get or create the thread monitor instance.

    The monitor is stored on the config object to ensure proper lifecycle
    management across test execution.

    Args:
        config: The pytest configuration object.

    Returns:
        The ThreadPatchingMonitor instance.

    """
    monitor_attr = '_test_categories_thread_monitor'
    if not hasattr(config, monitor_attr):
        monitor = ThreadPatchingMonitor()
        setattr(config, monitor_attr, monitor)
    return cast('ThreadPatchingMonitor', getattr(config, monitor_attr))


def _safe_deactivate_thread_monitor(monitor: ThreadPatchingMonitor) -> None:
    """Safely deactivate thread monitor, handling edge cases.

    This function is used as a callback in ExitStack to ensure cleanup.

    Args:
        monitor: The thread monitor to deactivate.

    """
    if monitor.state.value == 'active':
        monitor.deactivate()


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


def _write_json_report(
    test_report: TestSizeReport,
    stats: DistributionStatsType,
    config_adapter: PytestConfigAdapterType,
    terminalreporter: pytest.TerminalReporter,
) -> None:
    """Write JSON report to file or stdout.

    Args:
        test_report: The test size report containing test data.
        stats: The distribution statistics.
        config_adapter: The config adapter for accessing options.
        terminalreporter: The terminal reporter for output.

    """
    json_report = JsonReport.from_test_size_report(
        test_report=test_report,
        distribution_stats=stats,
        version=PLUGIN_VERSION,
    )

    json_output = json_report.model_dump_json(indent=2)

    file_path = config_adapter.get_option('--test-size-report-file')
    if file_path:
        output_path = Path(str(file_path))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_output)
    else:
        terminalreporter.write_line('')
        terminalreporter.write_line(json_output)
