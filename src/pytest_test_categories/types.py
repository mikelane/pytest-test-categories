"""Type definitions for pytest-test-categories."""

from __future__ import annotations

from abc import (
    ABC,
    abstractmethod,
)
from enum import (
    Enum,
    StrEnum,
    auto,
)
from typing import TYPE_CHECKING

from icontract import (
    ensure,
    require,
)
from pydantic import BaseModel

if TYPE_CHECKING:
    from numbers import Real


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


class TimerState(Enum):
    """Represents the possible states of a timer."""

    READY = auto()
    RUNNING = auto()
    STOPPED = auto()


class TestTimer(ABC, BaseModel):
    """Abstract base class defining the timer interface.

    Attributes:
        _state: The current state of the timer, managed by Pydantic.

    """

    state: TimerState = TimerState.READY

    @require(lambda self: self.state == TimerState.READY, 'Timer must be in READY state to start')
    @ensure(lambda self: self.state == TimerState.RUNNING, 'Timer must be in RUNNING state after starting')
    @abstractmethod
    def start(self) -> None:
        """Start timing a test.

        Raises:
            RuntimeError: If the timer is not in READY state.

        """

    @require(lambda self: self.state == TimerState.RUNNING, 'Timer must be in RUNNING state to stop')
    @ensure(lambda self: self.state == TimerState.STOPPED, 'Timer must be in STOPPED state after stopping')
    @abstractmethod
    def stop(self) -> None:
        """Stop timing a test.

        Raises:
            RuntimeError: If the timer is not in RUNNING state.

        """

    @require(lambda self: self.state == TimerState.STOPPED, 'Timer must be in STOPPED state to get duration')
    @ensure(lambda result: result > 0, 'Duration must be positive')
    @abstractmethod
    def duration(self) -> Real:
        """Get the duration of the test in seconds.

        Returns:
            Real: The duration of the test in seconds (must be positive).

        Raises:
            RuntimeError: If the timer is not in STOPPED state.

        """
