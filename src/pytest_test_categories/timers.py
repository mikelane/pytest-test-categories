"""Real timer implementation for measuring test duration."""

from __future__ import annotations

import time

from pydantic import Field

from pytest_test_categories.types import (
    TestTimer,
    TimerState,
)


class WallTimer(TestTimer):
    """Timer implementation using wall clock time.

    This timer uses time.perf_counter() for high-resolution timing
    that is not affected by system clock updates.
    """

    start_time: float | None = Field(None, description='Start time in seconds')
    end_time: float | None = Field(None, description='End time in seconds')

    def reset(self) -> None:
        """Reset the timer to initial state."""
        self.state = TimerState.READY
        self.start_time = None
        self.end_time = None

    def start(self) -> None:
        """Start timing, recording the current time."""
        if self.state != TimerState.READY:
            self.reset()  # Reset if not in ready state
        super().start()  # Parent handles state transition and contracts
        self.start_time = time.perf_counter()
        self.end_time = None

    def stop(self) -> None:
        """Stop timing, recording the end time."""
        self.end_time = time.perf_counter()
        super().stop()  # Parent handles state transition and contracts

    def duration(self) -> float:
        """Calculate the duration in seconds.

        Returns:
            The duration in seconds with microsecond precision.

        Raises:
            RuntimeError: If called before both start and stop.

        """
        if self.start_time is None:
            msg = 'Timer was never started'
            raise RuntimeError(msg)
        if self.end_time is None:
            msg = 'Timer was never stopped'
            raise RuntimeError(msg)

        return self.end_time - self.start_time
