"""Test the wall clock timer implementation."""

from __future__ import annotations

import time

import pytest

from pytest_test_categories.timers import WallTimer
from pytest_test_categories.types import TimerState


class DescribeWallTimer:
    def it_measures_elapsed_time(self) -> None:
        """Verify that the timer measures actual elapsed time."""
        timer = WallTimer(state=TimerState.READY)

        timer.start()
        time.sleep(0.1)  # Sleep for 100ms
        timer.stop()

        duration = timer.duration()
        assert 0.09 <= duration <= 0.2, f'Expected ~0.1s, got {duration}s'

    def it_fails_if_getting_duration_before_start(self) -> None:
        """Verify error when getting duration before starting."""
        timer = WallTimer(state=TimerState.READY)

        with pytest.raises(RuntimeError, match='Timer was never started'):
            timer.duration()

    def it_fails_if_getting_duration_before_stop(self) -> None:
        """Verify error when getting duration before stopping."""
        timer = WallTimer(state=TimerState.READY)
        timer.start()

        with pytest.raises(RuntimeError, match='Timer was never stopped'):
            timer.duration()

    def it_maintains_correct_state(self) -> None:
        """Verify that timer state transitions work correctly."""
        timer = WallTimer(state=TimerState.READY)
        assert timer.state == TimerState.READY

        timer.start()
        assert timer.state == TimerState.RUNNING

        timer.stop()
        assert timer.state == TimerState.STOPPED

    def it_can_be_reused(self) -> None:
        """Verify that timer can be used for multiple timings."""
        timer = WallTimer(state=TimerState.READY)

        # First timing
        timer.start()
        time.sleep(0.1)
        timer.stop()
        first_duration = timer.duration()

        # Reset state
        timer.state = TimerState.READY

        # Second timing
        timer.start()
        time.sleep(0.2)
        timer.stop()
        second_duration = timer.duration()

        assert first_duration < second_duration
        assert 0.09 <= first_duration <= 0.2
        assert 0.19 <= second_duration <= 0.3
