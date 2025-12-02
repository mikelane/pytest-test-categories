"""Type definitions for pytest-test-categories."""

from __future__ import annotations

from abc import (
    ABC,
    abstractmethod,
)
from enum import StrEnum
from typing import TYPE_CHECKING

from icontract import (
    ensure,
    require,
)
from pydantic import BaseModel


# TimingViolationError is now defined in timing.py with enhanced error messages
# This is a re-export for backward compatibility
def __getattr__(name: str) -> type:
    """Lazy import for backward compatibility with TimingViolationError."""
    if name == 'TimingViolationError':
        from pytest_test_categories.timing import TimingViolationError  # noqa: PLC0415

        return TimingViolationError
    msg = f'module {__name__!r} has no attribute {name!r}'
    raise AttributeError(msg)


class NetworkMode(StrEnum):
    """Network access modes for test size enforcement.

    Each test size category has an associated network mode that determines
    what network access is permitted during test execution:
    - BLOCK_ALL: No network access permitted (small tests)
    - LOCALHOST_ONLY: Only localhost connections allowed (medium tests)
    - ALLOW_ALL: Full network access permitted (large/xlarge tests)

    This enum is used by NetworkBlockerPort to enforce appropriate
    network restrictions based on test size.
    """

    BLOCK_ALL = 'block_all'
    LOCALHOST_ONLY = 'localhost'
    ALLOW_ALL = 'allow_all'


class TestSize(StrEnum):
    """Test size categories."""

    SMALL = 'small'
    MEDIUM = 'medium'
    LARGE = 'large'
    XLARGE = 'xlarge'

    @property
    def marker_name(self) -> str:
        """Get the pytest marker name for this size."""
        return self.name.lower()

    @property
    def description(self) -> str:
        """Get the description for this test size marker."""
        descriptions = {
            'SMALL': 'Fast unit test (<1s, no network/filesystem/subprocess/database/sleep)',
            'MEDIUM': 'Integration test (<5min, localhost network, filesystem allowed)',
            'LARGE': 'System test (<15min, full network and resource access)',
            'XLARGE': 'Extended test (<15min, full network and resource access)',
        }
        return descriptions.get(self.name, f'mark test as {self.name} size')

    @property
    def label(self) -> str:
        """Get the label to show in test output."""
        return f'[{self.name}]'

    @property
    def network_mode(self) -> NetworkMode:
        """Get the network access mode for this test size.

        Returns the appropriate NetworkMode based on Google's test size
        definitions:
        - SMALL: No network access (BLOCK_ALL)
        - MEDIUM: Localhost only (LOCALHOST_ONLY)
        - LARGE/XLARGE: Full network access (ALLOW_ALL)
        """
        if self == TestSize.SMALL:
            return NetworkMode.BLOCK_ALL
        if self == TestSize.MEDIUM:
            return NetworkMode.LOCALHOST_ONLY
        return NetworkMode.ALLOW_ALL


class TimerState(StrEnum):
    """Represents the possible states of a timer."""

    READY = 'ready'
    RUNNING = 'running'
    STOPPED = 'stopped'


class TestTimer(BaseModel, ABC):
    """Abstract base class defining the timer interface."""

    state: TimerState = TimerState.READY

    def reset(self) -> None:
        """Reset timer to initial state."""
        self.state = TimerState.READY

    @require(lambda self: self.state == TimerState.READY, 'Timer must be in READY state to start')
    @ensure(lambda self: self.state == TimerState.RUNNING, 'Timer must be in RUNNING state after starting')
    def start(self) -> None:
        """Start timing a test.

        Raises:
            RuntimeError: If the timer is not in READY state.

        """
        self.state = TimerState.RUNNING

    @require(lambda self: self.state == TimerState.RUNNING, 'Timer must be in RUNNING state to stop')
    @ensure(lambda self: self.state == TimerState.STOPPED, 'Timer must be in STOPPED state after stopping')
    def stop(self) -> None:
        """Stop timing a test.

        Raises:
            RuntimeError: If the timer is not in RUNNING state.

        """
        self.state = TimerState.STOPPED

    @require(lambda self: self.state == TimerState.STOPPED, 'Timer must be in STOPPED state to get duration')
    @ensure(lambda result: result > 0, 'Duration must be positive')
    @abstractmethod
    def duration(self) -> float:
        """Get the duration of the test in seconds.

        Returns:
            The duration of the test in seconds (must be positive).

        Raises:
            RuntimeError: If the timer is not in STOPPED state.

        """


class TestItemPort(ABC):
    """Abstract base class defining the test item interface.

    This port (interface) abstracts pytest.Item to enable hexagonal architecture.
    It allows testing code that interacts with test items without depending on
    pytest's internal implementation details.

    Implementations:
    - PytestItemAdapter: Production adapter that wraps pytest.Item
    - FakeTestItem: Test adapter providing controllable test double

    This follows the same pattern as TestTimer/WallTimer/FakeTimer.
    """

    @property
    @abstractmethod
    def nodeid(self) -> str:
        """Get the test item's node ID.

        Returns:
            The unique identifier for this test item.

        """

    @abstractmethod
    def get_marker(self, name: str) -> object | None:
        """Get a marker by name from this test item.

        Args:
            name: The marker name to retrieve.

        Returns:
            The marker object if found, None otherwise.

        """

    @abstractmethod
    def set_nodeid(self, nodeid: str) -> None:
        """Set the test item's node ID.

        Args:
            nodeid: The new node ID to assign.

        """

    @abstractmethod
    def get_marker_kwargs(self, name: str) -> dict[str, object]:
        """Get the keyword arguments from a marker.

        Args:
            name: The marker name to retrieve kwargs from.

        Returns:
            A dictionary of keyword arguments, or empty dict if marker not found.

        Example:
            >>> # For @pytest.mark.medium(allow_external_systems=True)
            >>> kwargs = item.get_marker_kwargs('medium')
            >>> assert kwargs == {'allow_external_systems': True}

        """


class OutputWriterPort(ABC):
    """Abstract base class defining the output writer interface.

    This port (interface) abstracts pytest.TerminalReporter to enable hexagonal architecture.
    It allows testing report formatting code without depending on pytest's terminal
    reporter implementation.

    Implementations:
    - TerminalReporterAdapter: Production adapter that wraps pytest.TerminalReporter
    - StringBufferWriter: Test adapter providing controllable output capture

    This follows the same pattern as TestTimer/WallTimer/FakeTimer and TestItemPort.

    Example:
        >>> writer = TerminalReporterAdapter(terminalreporter)
        >>> writer.write_section('Test Report', sep='=')
        >>> writer.write_line('Total tests: 10')
        >>> writer.write_separator(sep='-')

    """

    @abstractmethod
    def write_section(self, title: str, sep: str = '=') -> None:
        """Write a section header with title and separator.

        Args:
            title: The section title to display.
            sep: The separator character to use (default: '=').

        """

    @abstractmethod
    def write_line(self, message: str, **kwargs: object) -> None:
        """Write a single line of text.

        Args:
            message: The message to write.
            **kwargs: Additional styling arguments (e.g., red=True, bold=True).

        """

    @abstractmethod
    def write_separator(self, sep: str = '-') -> None:
        """Write a separator line.

        Args:
            sep: The separator character to use (default: '-').

        """


class WarningSystemPort(ABC):
    """Abstract base class defining the warning system interface.

    This port (interface) abstracts Python's warnings module to enable hexagonal architecture.
    It allows testing code that emits warnings without depending on the warnings module's
    implementation or causing actual warnings to be emitted during tests.

    Implementations:
    - PytestWarningAdapter: Production adapter that wraps warnings.warn
    - FakeWarningSystem: Test adapter providing controllable warning recording

    This follows the same pattern as TestTimer/WallTimer/FakeTimer, TestItemPort, and OutputWriterPort.

    Example:
        >>> warning_system = PytestWarningAdapter()
        >>> warning_system.warn('This feature is deprecated', category=DeprecationWarning)

    """

    @abstractmethod
    def warn(self, message: str, category: type[Warning] | None = None) -> None:
        """Emit a warning with the specified message and category.

        Args:
            message: The warning message to emit.
            category: The warning category (default: pytest.PytestWarning if None).

        """


class ConfigStatePort(ABC):
    """Abstract base class defining the config state interface.

    This port (interface) abstracts pytest.Config state management to enable hexagonal architecture.
    It allows testing code that accesses plugin state without depending on pytest's internal
    implementation details or using private attributes.

    This eliminates the need for noqa: SLF001 comments by encapsulating state access
    behind a well-defined interface.

    Implementations:
    - PytestConfigAdapter: Production adapter that wraps pytest.Config
    - FakeConfig: Test adapter providing controllable configuration

    Example:
        >>> config = PytestConfigAdapter(pytest_config)
        >>> state = config.get_plugin_state()
        >>> config.set_plugin_state(new_state)

    """

    @abstractmethod
    def get_plugin_state(self) -> PluginState:
        """Get the plugin state for the current session.

        Returns:
            The PluginState object containing all plugin session data.

        """

    @abstractmethod
    def set_plugin_state(self, state: PluginState) -> None:
        """Set the plugin state for the current session.

        Args:
            state: The PluginState object to store.

        """

    @abstractmethod
    def get_distribution_stats(self) -> DistributionStats:
        """Get the distribution statistics for the current session.

        Returns:
            The DistributionStats object.

        """

    @abstractmethod
    def set_distribution_stats(self, stats: DistributionStats) -> None:
        """Set the distribution statistics for the current session.

        Args:
            stats: The DistributionStats object to store.

        """

    @abstractmethod
    def add_marker(self, marker_definition: str) -> None:
        """Add a marker definition to the configuration.

        Args:
            marker_definition: The marker definition string (e.g., 'small: mark test as small size').

        """

    @abstractmethod
    def get_option(self, name: str) -> object:
        """Get a command-line option value.

        Args:
            name: The option name (e.g., '--test-size-report').

        Returns:
            The option value, or None if not set.

        """


# Import DistributionStats for ConfigStatePort
if not TYPE_CHECKING:
    from pytest_test_categories.distribution.stats import DistributionStats


class PluginState(BaseModel):
    """Plugin state for a test session.

    This class manages the state for the entire test session and supports
    hexagonal architecture through dependency injection of the timer factory
    and test discovery service.

    The timer_factory allows tests to inject FakeTimer for deterministic
    testing while production uses WallTimer for actual timing.

    The test_discovery_service is created during pytest_configure and uses
    dependency injection to provide the warning system adapter.

    The distribution_config holds the configured distribution targets and tolerances,
    allowing customization via pyproject.toml, pytest.ini, or CLI options.

    The violation_tracker collects hermeticity violations for terminal summary
    reporting in both WARN and STRICT enforcement modes.
    """

    model_config = {'arbitrary_types_allowed': True}

    active: bool = True
    distribution_stats: object | None = None  # Will be DistributionStats
    warned_tests: set[str] = set()
    test_size_report: object | None = None  # Will be TestSizeReport
    # Store timers per test item to avoid race conditions in parallel execution
    timers: dict[str, TestTimer] = {}
    # Timer factory for dependency injection (hexagonal architecture port)
    timer_factory: type[TestTimer] | None = None
    # Test discovery service for finding size markers (hexagonal architecture)
    test_discovery_service: object | None = None
    # Distribution configuration for targets and tolerances (configurable)
    distribution_config: object | None = None  # DistributionConfig, avoiding circular import
    # Violation tracker for hermeticity enforcement summary
    violation_tracker: object | None = None  # ViolationTracker, avoiding circular import

    def __init__(self, **data: object) -> None:
        """Initialize PluginState with defaults for circular import fields."""
        super().__init__(**data)
        # Set defaults after initialization to avoid circular imports at module load time
        if self.distribution_stats is None:
            from pytest_test_categories.distribution.stats import DistributionStats  # noqa: PLC0415

            self.distribution_stats = DistributionStats()
        if self.timer_factory is None:
            from pytest_test_categories.timers import WallTimer  # noqa: PLC0415

            self.timer_factory = WallTimer
        if self.distribution_config is None:
            from pytest_test_categories.distribution.config import DEFAULT_DISTRIBUTION_CONFIG  # noqa: PLC0415

            self.distribution_config = DEFAULT_DISTRIBUTION_CONFIG
        if self.violation_tracker is None:
            from pytest_test_categories.violation_tracking import ViolationTracker  # noqa: PLC0415

            self.violation_tracker = ViolationTracker()


# Add proper type hints for TYPE_CHECKING
if TYPE_CHECKING:
    from pytest_test_categories.distribution.stats import DistributionStats
