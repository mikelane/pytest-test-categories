"""Test the fake timer implementation for deterministic testing.

This module tests the FakeTimer adapter, which provides controllable
time advancement for testing timer behavior without depending on the
system clock. This eliminates flaky tests and ensures deterministic results.

The FakeTimer is part of the hexagonal architecture pattern where:
- TestTimer is the Port (interface)
- FakeTimer is a Test Adapter (test double)
- WallTimer is a Production Adapter (real implementation)
"""

from __future__ import annotations

import pytest

from pytest_test_categories.timers import FakeTimer
from pytest_test_categories.types import TimerState


@pytest.mark.small
class DescribeFakeTimer:
    """Tests for the FakeTimer test double."""

    def it_measures_simulated_elapsed_time(self) -> None:
        """Verify that the timer tracks simulated time advancement."""
        timer = FakeTimer()

        timer.start()
        timer.advance(0.5)  # Simulate 0.5 seconds
        timer.stop()

        duration = timer.duration()
        assert duration == 0.5, f'Expected exactly 0.5s, got {duration}s'

    def it_advances_time_incrementally(self) -> None:
        """Verify that multiple advance() calls accumulate."""
        timer = FakeTimer()

        timer.start()
        timer.advance(0.1)
        timer.advance(0.2)
        timer.advance(0.3)  # Total: 0.6 seconds
        timer.stop()

        # Use pytest.approx for floating-point comparison
        assert timer.duration() == pytest.approx(0.6)

    def it_fails_if_getting_duration_before_start(self) -> None:
        """Verify error when getting duration before starting."""
        timer = FakeTimer()

        with pytest.raises(RuntimeError, match='Timer was never started'):
            timer.duration()

    def it_fails_if_getting_duration_before_stop(self) -> None:
        """Verify error when getting duration before stopping."""
        timer = FakeTimer()
        timer.start()

        with pytest.raises(RuntimeError, match='Timer was never stopped'):
            timer.duration()

    def it_maintains_correct_state(self) -> None:
        """Verify that timer state transitions work correctly."""
        timer = FakeTimer()
        assert timer.state == TimerState.READY

        timer.start()
        assert timer.state == TimerState.RUNNING  # type: ignore[comparison-overlap]

        timer.stop()  # type: ignore[unreachable]
        assert timer.state == TimerState.STOPPED

    def it_can_be_reused_after_reset(self) -> None:
        """Verify that timer can be reset and used for multiple timings."""
        timer = FakeTimer(state=TimerState.READY)

        # First timing
        timer.start()
        timer.advance(0.5)
        timer.stop()
        first_duration = timer.duration()
        assert first_duration == 0.5

        # Reset completely
        timer.reset()
        assert timer.state == TimerState.READY
        assert timer.current_time == 0.0

        # Second timing should start from zero
        timer.start()
        timer.advance(1.0)
        timer.stop()
        second_duration = timer.duration()
        assert second_duration == 1.0

    def it_allows_zero_duration(self) -> None:
        """Verify that zero duration is valid (start immediately followed by stop)."""
        timer = FakeTimer(state=TimerState.READY)

        timer.start()
        # No advance() call
        timer.stop()

        assert timer.duration() == 0.0

    def it_supports_precise_fractional_seconds(self) -> None:
        """Verify that the timer handles precise fractional values."""
        timer = FakeTimer(state=TimerState.READY)

        timer.start()
        timer.advance(0.123456789)
        timer.stop()

        assert timer.duration() == 0.123456789

    def it_resets_current_time_on_reset(self) -> None:
        """Verify that reset() clears the internal clock."""
        timer = FakeTimer(state=TimerState.READY)

        timer.start()
        timer.advance(5.0)
        timer.stop()

        # After reset, internal clock should be zero
        timer.reset()
        assert timer.current_time == 0.0
        assert timer.start_time is None
        assert timer.end_time is None
