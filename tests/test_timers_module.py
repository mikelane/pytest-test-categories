"""Tests for the timers module public APIs."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from pytest_test_categories import (
    TestTimer,
    TimerState,
    WallTimer,
)


@pytest.mark.small
class DescribeWallTimer:
    """Test the WallTimer class."""

    def it_initializes_with_ready_state(self) -> None:
        """Test that WallTimer initializes with READY state."""
        timer = WallTimer()
        assert timer.state == TimerState.READY
        assert timer.start_time is None
        assert timer.end_time is None

    def it_can_reset_to_initial_state(self) -> None:
        """Test that reset() returns timer to initial state."""
        timer = WallTimer()
        timer.start_time = 123.0
        timer.end_time = 456.0
        timer.state = TimerState.STOPPED

        timer.reset()

        assert timer.state == TimerState.READY
        assert timer.start_time is None
        assert timer.end_time is None

    def it_can_start_timing(self) -> None:
        """Test that start() begins timing."""
        timer = WallTimer()

        with patch('time.perf_counter', return_value=100.0):
            timer.start()

        assert timer.state == TimerState.RUNNING
        assert timer.start_time == 100.0
        assert timer.end_time is None

    def it_resets_before_starting_if_not_ready(self) -> None:
        """Test that start() resets if not in READY state."""
        timer = WallTimer()
        timer.state = TimerState.STOPPED
        timer.start_time = 123.0
        timer.end_time = 456.0

        with patch('time.perf_counter', return_value=100.0):
            timer.start()

        assert timer.state == TimerState.RUNNING
        assert timer.start_time == 100.0
        assert timer.end_time is None

    def it_can_stop_timing(self) -> None:
        """Test that stop() ends timing."""
        timer = WallTimer()

        with patch('time.perf_counter', side_effect=[100.0, 200.0]):
            timer.start()
            timer.stop()

        assert timer.state == TimerState.STOPPED
        assert timer.start_time == 100.0
        assert timer.end_time == 200.0

    def it_calculates_duration_correctly(self) -> None:
        """Test that duration() returns correct time difference."""
        timer = WallTimer()

        with patch('time.perf_counter', side_effect=[100.0, 200.0]):
            timer.start()
            timer.stop()

        assert timer.duration() == 100.0

    def it_raises_error_when_getting_duration_before_start(self) -> None:
        """Test that duration() raises error when timer was never started."""
        timer = WallTimer()

        with pytest.raises(RuntimeError, match='Timer was never started'):
            timer.duration()

    def it_raises_error_when_getting_duration_before_stop(self) -> None:
        """Test that duration() raises error when timer was never stopped."""
        timer = WallTimer()

        with patch('time.perf_counter', return_value=100.0):
            timer.start()

        with pytest.raises(RuntimeError, match='Timer was never stopped'):
            timer.duration()

    def it_measures_actual_elapsed_time(self) -> None:
        """Test that WallTimer measures real elapsed time."""
        timer = WallTimer()

        timer.start()
        time.sleep(0.01)  # Sleep for 10ms
        timer.stop()

        duration = timer.duration()
        assert duration >= 0.01  # Should be at least 10ms
        assert duration < 0.1  # But not more than 100ms

    def it_can_be_reused_after_reset(self) -> None:
        """Test that timer can be reused after reset."""
        timer = WallTimer()

        # First use
        with patch('time.perf_counter', side_effect=[100.0, 200.0]):
            timer.start()
            timer.stop()
        assert timer.duration() == 100.0

        # Reset and reuse
        timer.reset()
        with patch('time.perf_counter', side_effect=[300.0, 350.0]):
            timer.start()
            timer.stop()
        assert timer.duration() == 50.0

    def it_handles_rapid_start_stop_cycles(self) -> None:
        """Test that timer handles rapid start/stop cycles correctly."""
        timer = WallTimer()

        for i in range(5):
            with patch('time.perf_counter', side_effect=[i * 100.0, i * 100.0 + 10.0]):
                timer.start()
                timer.stop()
            assert timer.duration() == 10.0
            timer.reset()

    def it_inherits_from_test_timer(self) -> None:
        """Test that WallTimer inherits from TestTimer."""
        assert issubclass(WallTimer, TestTimer)
