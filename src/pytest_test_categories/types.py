"""Type definitions for pytest-test-categories."""

from __future__ import annotations

from abc import (
    ABC,
    abstractmethod,
)
from enum import StrEnum

from icontract import (
    ensure,
    require,
)
from pydantic import BaseModel


class TimingViolationError(Exception):
    """Exception raised for timing violations."""


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
        return f'mark test as {self.name} size'

    @property
    def label(self) -> str:
        """Get the label to show in test output."""
        return f'[{self.name}]'


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
