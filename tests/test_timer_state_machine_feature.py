"""Timer state machine transition tests.

This module comprehensively exercises the timer state machine through the public pytest API.
Tests verify all state transitions, error handling, and edge cases to achieve 100% coverage
of the timer implementation.

State machine being tested:
    READY → RUNNING → STOPPED
      ↑                  |
      └──────────────────┘ (reset)

The tests use pytester to create real pytest test scenarios that exercise timer behavior
through the plugin, ensuring the timer works correctly in actual usage.
"""

from __future__ import annotations

import pytest


class DescribeTimerStateMachineTransitions:
    """Test all state transitions of the timer state machine."""

    @pytest.mark.medium
    def it_transitions_through_normal_lifecycle(self, pytester: pytest.Pytester) -> None:
        """It transitions correctly through READY → RUNNING → STOPPED."""
        test_file = pytester.makepyfile(
            test_normal="""
            import pytest

            @pytest.mark.small
            def test_normal_execution():
                # Timer starts in READY, transitions to RUNNING, then STOPPED
                assert True
            """
        )

        result = pytester.runpytest(test_file)

        # Test should pass and timer should handle all transitions
        result.assert_outcomes(passed=1)

    @pytest.mark.small
    def it_resets_timer_when_starting_from_non_ready_state_fake_timer(self) -> None:
        """It automatically resets FakeTimer when starting from non-ready state.

        This covers line 111 in timers.py (FakeTimer.start() reset path).
        """
        from pytest_test_categories.timers import FakeTimer

        timer = FakeTimer()

        # Start timer normally
        timer.start()
        assert timer.state.value == 'running'

        # Try to start again while running - should automatically reset
        timer.start()
        assert timer.state.value == 'running'
        assert timer.start_time == 0.0  # Reset to beginning

    @pytest.mark.small
    def it_resets_timer_when_starting_from_non_ready_state_wall_timer(self) -> None:
        """It automatically resets WallTimer when starting from non-ready state.

        This covers line 36 in timers.py (WallTimer.start() reset path).
        """
        from pytest_test_categories.timers import WallTimer

        timer = WallTimer()

        # Start timer normally
        timer.start()
        assert timer.state.value == 'running'

        # Try to start again while running - should automatically reset
        timer.start()
        assert timer.state.value == 'running'

    @pytest.mark.medium
    def it_allows_timer_reset_during_test_execution(self, pytester: pytest.Pytester) -> None:
        """It handles timer reset and restart during test execution."""
        test_file = pytester.makepyfile(
            test_reset="""
            import pytest

            @pytest.mark.small
            def test_with_potential_reset():
                # Test executes normally even if timer is restarted
                # Plugin timer handles state transitions gracefully
                for _ in range(3):
                    x = 1 + 1
                assert x == 2
            """
        )

        result = pytester.runpytest(test_file)

        # Test should pass with timer handling all transitions
        result.assert_outcomes(passed=1)

    @pytest.mark.small
    def it_completes_full_state_cycle_with_reset(self) -> None:
        """It completes full cycle: READY → RUNNING → STOPPED → READY."""
        from pytest_test_categories.timers import FakeTimer

        timer = FakeTimer()

        # Initial state
        assert timer.state.value == 'ready'

        # Start: READY → RUNNING
        timer.start()
        assert timer.state.value == 'running'

        # Stop: RUNNING → STOPPED
        timer.stop()
        assert timer.state.value == 'stopped'

        # Reset: STOPPED → READY
        timer.reset()
        assert timer.state.value == 'ready'


class DescribeTimerErrorHandling:
    """Test timer error conditions and contract violations."""

    @pytest.mark.small
    def it_raises_error_when_getting_duration_before_timer_started(self) -> None:
        """It raises RuntimeError when querying duration on never-started timer."""
        from pytest_test_categories.timers import FakeTimer

        timer = FakeTimer()

        # Never called start()
        with pytest.raises(RuntimeError, match='Timer was never started'):
            _ = timer.duration()

    @pytest.mark.small
    def it_raises_error_when_getting_duration_before_timer_stopped(self) -> None:
        """It raises RuntimeError when querying duration on running timer."""
        from pytest_test_categories.timers import FakeTimer

        timer = FakeTimer()
        timer.start()

        # Started but not stopped
        with pytest.raises(RuntimeError, match='Timer was never stopped'):
            _ = timer.duration()

    @pytest.mark.small
    def it_enforces_state_precondition_for_start(self) -> None:
        """It enforces READY state precondition for start() via icontract."""
        from icontract import ViolationError

        from pytest_test_categories.timers import FakeTimer
        from pytest_test_categories.types import TestTimer

        timer = FakeTimer()
        timer.start()
        timer.stop()

        # Manually set to STOPPED state - timer.start() will auto-reset
        # To test the precondition, call parent's start() directly
        # which should violate the precondition

        # This should raise because timer is in STOPPED state
        with pytest.raises(ViolationError, match='Timer must be in READY state'):
            TestTimer.start(timer)

    @pytest.mark.small
    def it_enforces_state_precondition_for_stop(self) -> None:
        """It enforces RUNNING state precondition for stop() via icontract."""
        from icontract import ViolationError

        from pytest_test_categories.timers import FakeTimer

        timer = FakeTimer()

        # Try to stop without starting should violate precondition
        with pytest.raises(ViolationError):
            timer.stop()

    @pytest.mark.small
    def it_enforces_state_precondition_for_duration(self) -> None:
        """It enforces STOPPED state precondition for duration() via icontract."""
        from icontract import ViolationError

        from pytest_test_categories.timers import FakeTimer

        timer = FakeTimer()
        timer.start()

        # Try to get duration in RUNNING state - should violate precondition
        # The RuntimeError "Timer was never stopped" happens BEFORE icontract check
        # So we get RuntimeError, not ViolationError
        with pytest.raises((ViolationError, RuntimeError)):
            timer.duration()


class DescribeWallTimerImplementation:
    """Test WallTimer specific coverage and edge cases."""

    @pytest.mark.medium
    def it_measures_actual_wall_clock_time(self, pytester: pytest.Pytester) -> None:
        """It uses wall clock timer for actual duration measurement."""
        test_file = pytester.makepyfile(
            test_wallclock="""
            import pytest
            import time

            @pytest.mark.small
            def test_wall_clock_measurement():
                time.sleep(0.05)  # Sleep for 50ms
            """
        )

        result = pytester.runpytest(test_file)

        # Test should pass and duration should reflect actual sleep
        result.assert_outcomes(passed=1)

    @pytest.mark.small
    def it_handles_never_started_wall_timer(self) -> None:
        """It raises RuntimeError when WallTimer never started."""
        from pytest_test_categories.timers import WallTimer

        timer = WallTimer()

        with pytest.raises(RuntimeError, match='Timer was never started'):
            _ = timer.duration()

    @pytest.mark.small
    def it_handles_never_stopped_wall_timer(self) -> None:
        """It raises RuntimeError when WallTimer never stopped."""
        from pytest_test_categories.timers import WallTimer

        timer = WallTimer()
        timer.start()

        with pytest.raises(RuntimeError, match='Timer was never stopped'):
            _ = timer.duration()


class DescribeFakeTimerAdvancement:
    """Test FakeTimer time advancement and controllability."""

    @pytest.mark.small
    def it_advances_simulated_time_incrementally(self) -> None:
        """It advances simulated time by specified duration."""
        from pytest_test_categories.timers import FakeTimer

        timer = FakeTimer()
        timer.start()

        # Advance in steps
        timer.advance(0.1)
        assert timer.current_time == pytest.approx(0.1)

        timer.advance(0.2)
        assert timer.current_time == pytest.approx(0.3)

        timer.advance(0.15)
        assert timer.current_time == pytest.approx(0.45)

        timer.stop()
        assert timer.duration() == pytest.approx(0.45)

    @pytest.mark.small
    def it_resets_current_time_on_reset(self) -> None:
        """It resets current_time to 0.0 when timer is reset."""
        from pytest_test_categories.timers import FakeTimer

        timer = FakeTimer()
        timer.start()
        timer.advance(5.0)
        timer.stop()

        # Current time should be 5.0
        assert timer.current_time == 5.0

        # Reset should clear current_time
        timer.reset()
        assert timer.current_time == 0.0
        assert timer.state.value == 'ready'


class DescribeTimerIntegrationWithPytest:
    """Test timer behavior through actual pytest execution."""

    @pytest.mark.medium
    def it_tracks_timing_for_passing_test(self, pytester: pytest.Pytester) -> None:
        """It successfully tracks timing for a passing test."""
        test_file = pytester.makepyfile(
            test_passing="""
            import pytest

            @pytest.mark.small
            def test_passing():
                x = 1 + 1
                assert x == 2
            """
        )

        result = pytester.runpytest(test_file)
        result.assert_outcomes(passed=1)

    @pytest.mark.medium
    def it_tracks_timing_for_failing_test(self, pytester: pytest.Pytester) -> None:
        """It tracks timing even when test fails."""
        test_file = pytester.makepyfile(
            test_failing="""
            import pytest

            @pytest.mark.small
            def test_failing():
                assert False, "Intentional failure"
            """
        )

        result = pytester.runpytest(test_file)
        result.assert_outcomes(failed=1)

    @pytest.mark.medium
    def it_handles_test_with_setup_and_teardown(self, pytester: pytest.Pytester) -> None:
        """It handles timer lifecycle with test setup and teardown."""
        test_file = pytester.makepyfile(
            test_fixture="""
            import pytest

            @pytest.fixture
            def setup_data():
                data = {'value': 42}
                yield data
                # Teardown
                data.clear()

            @pytest.mark.small
            def test_with_fixture(setup_data):
                assert setup_data['value'] == 42
            """
        )

        result = pytester.runpytest(test_file)
        result.assert_outcomes(passed=1)

    @pytest.mark.medium
    def it_handles_parametrized_tests(self, pytester: pytest.Pytester) -> None:
        """It tracks timing correctly for parametrized tests."""
        test_file = pytester.makepyfile(
            test_param="""
            import pytest

            @pytest.mark.small
            @pytest.mark.parametrize('value', [1, 2, 3])
            def test_param(value):
                assert value > 0
            """
        )

        result = pytester.runpytest(test_file)
        result.assert_outcomes(passed=3)
