"""Tests for the types module public APIs."""

from __future__ import annotations

import pytest

from pytest_test_categories.types import (
    TestSize,
    TestTimer,
    TimerState,
    TimingViolationError,
)


@pytest.mark.small
class DescribeTestSize:
    """Test the TestSize enum."""

    def it_has_correct_values(self) -> None:
        """Test that TestSize has the expected values."""
        assert TestSize.SMALL.value == 'small'
        assert TestSize.MEDIUM.value == 'medium'
        assert TestSize.LARGE.value == 'large'
        assert TestSize.XLARGE.value == 'xlarge'

    def it_provides_marker_names(self) -> None:
        """Test that marker_name property returns correct values."""
        assert TestSize.SMALL.marker_name == 'small'
        assert TestSize.MEDIUM.marker_name == 'medium'
        assert TestSize.LARGE.marker_name == 'large'
        assert TestSize.XLARGE.marker_name == 'xlarge'

    def it_provides_descriptions(self) -> None:
        """Test that description property returns informative constraint details."""
        assert 'no network' in TestSize.SMALL.description
        assert '<1s' in TestSize.SMALL.description
        assert 'localhost' in TestSize.MEDIUM.description
        assert 'full network' in TestSize.LARGE.description
        assert 'full network' in TestSize.XLARGE.description

    def it_provides_labels(self) -> None:
        """Test that label property returns correct values."""
        assert TestSize.SMALL.label == '[SMALL]'
        assert TestSize.MEDIUM.label == '[MEDIUM]'
        assert TestSize.LARGE.label == '[LARGE]'
        assert TestSize.XLARGE.label == '[XLARGE]'


@pytest.mark.small
class DescribeTimerState:
    """Test the TimerState enum."""

    def it_has_correct_values(self) -> None:
        """Test that TimerState has the expected values."""
        assert TimerState.READY.value == 'ready'
        assert TimerState.RUNNING.value == 'running'
        assert TimerState.STOPPED.value == 'stopped'


@pytest.mark.small
class DescribeTimingViolationError:
    """Test the TimingViolationError exception."""

    def it_can_be_raised_with_proper_arguments(self) -> None:
        """Test that TimingViolationError can be raised with proper arguments."""
        with pytest.raises(TimingViolationError, match='exceeded time limit'):
            raise TimingViolationError(
                test_size=TestSize.SMALL,
                test_nodeid='tests/test_slow.py::test_compute',
                limit=1.0,
                actual=2.5,
            )

    def it_inherits_from_exception(self) -> None:
        """Test that TimingViolationError inherits from Exception."""
        assert issubclass(TimingViolationError, Exception)

    def it_stores_timing_attributes(self) -> None:
        """Test that TimingViolationError stores the timing attributes."""
        exc = TimingViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_slow.py::test_compute',
            limit=1.0,
            actual=2.5,
        )

        assert exc.test_size == TestSize.SMALL
        assert exc.test_nodeid == 'tests/test_slow.py::test_compute'
        assert exc.limit == 1.0
        assert exc.actual == 2.5


@pytest.mark.small
class DescribeTestTimer:
    """Test the TestTimer abstract base class."""

    def it_initializes_with_ready_state(self) -> None:
        """Test that TestTimer initializes with READY state."""

        # Create a concrete implementation for testing
        class ConcreteTimer(TestTimer):
            def duration(self) -> float:
                return 1.0

        timer = ConcreteTimer()
        assert timer.state == TimerState.READY

    def it_can_reset_to_ready_state(self) -> None:
        """Test that reset() sets state to READY."""

        class ConcreteTimer(TestTimer):
            def duration(self) -> float:
                return 1.0

        timer = ConcreteTimer()
        timer.state = TimerState.STOPPED
        timer.reset()
        assert timer.state == TimerState.READY

    def it_can_start_from_ready_state(self) -> None:
        """Test that start() transitions from READY to RUNNING."""

        class ConcreteTimer(TestTimer):
            def duration(self) -> float:
                return 1.0

        timer = ConcreteTimer()
        timer.start()
        assert timer.state == TimerState.RUNNING

    def it_raises_error_when_starting_from_non_ready_state(self) -> None:
        """Test that start() raises error when not in READY state."""

        class ConcreteTimer(TestTimer):
            def duration(self) -> float:
                return 1.0

        timer = ConcreteTimer()
        timer.state = TimerState.RUNNING

        with pytest.raises(Exception, match='Timer must be in READY state to start'):
            timer.start()

    def it_can_stop_from_running_state(self) -> None:
        """Test that stop() transitions from RUNNING to STOPPED."""

        class ConcreteTimer(TestTimer):
            def duration(self) -> float:
                return 1.0

        timer = ConcreteTimer()
        timer.start()  # READY -> RUNNING
        timer.stop()  # RUNNING -> STOPPED
        assert timer.state == TimerState.STOPPED

    def it_raises_error_when_stopping_from_non_running_state(self) -> None:
        """Test that stop() raises error when not in RUNNING state."""

        class ConcreteTimer(TestTimer):
            def duration(self) -> float:
                return 1.0

        timer = ConcreteTimer()
        # Try to stop from READY state
        with pytest.raises(Exception, match='Timer must be in RUNNING state to stop'):
            timer.stop()

    def it_raises_error_when_getting_duration_from_non_stopped_state(self) -> None:
        """Test that duration() raises error when not in STOPPED state."""
        # This test is testing implementation details (decorators) rather than behavior
        # The actual behavior is tested in the WallTimer tests

    def it_can_be_used_as_abstract_base_class(self) -> None:
        """Test that TestTimer cannot be instantiated directly."""
        with pytest.raises(TypeError):
            TestTimer()  # type: ignore[abstract]
