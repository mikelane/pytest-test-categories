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
