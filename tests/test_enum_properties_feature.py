"""Feature tests for TestSize enum properties and behavior.

This test file exercises all TestSize enum properties to ensure 100% coverage
of the types module through the public API.
"""

from __future__ import annotations

import pytest

from pytest_test_categories import (
    TestSize,
    TestTimer,
    TimerState,
    TimingViolationError,
)


@pytest.mark.small
class DescribeTestSizeEnumIteration:
    """Test TestSize enum iteration and membership."""

    def it_provides_all_four_size_members(self) -> None:
        """Test that TestSize enum has exactly four members."""
        sizes = list(TestSize)
        assert len(sizes) == 4
        assert TestSize.SMALL in sizes
        assert TestSize.MEDIUM in sizes
        assert TestSize.LARGE in sizes
        assert TestSize.XLARGE in sizes

    def it_provides_member_names(self) -> None:
        """Test that TestSize enum members have correct names."""
        assert TestSize.SMALL.name == 'SMALL'
        assert TestSize.MEDIUM.name == 'MEDIUM'
        assert TestSize.LARGE.name == 'LARGE'
        assert TestSize.XLARGE.name == 'XLARGE'

    def it_provides_member_values(self) -> None:
        """Test that TestSize enum members have correct values."""
        assert TestSize.SMALL.value == 'small'
        assert TestSize.MEDIUM.value == 'medium'
        assert TestSize.LARGE.value == 'large'
        assert TestSize.XLARGE.value == 'xlarge'


@pytest.mark.small
class DescribeTestSizeMarkerNameProperty:
    """Test TestSize marker_name property."""

    def it_returns_lowercase_name_for_small(self) -> None:
        """Test marker_name property for SMALL size."""
        result = TestSize.SMALL.marker_name
        assert result == 'small'

    def it_returns_lowercase_name_for_medium(self) -> None:
        """Test marker_name property for MEDIUM size."""
        result = TestSize.MEDIUM.marker_name
        assert result == 'medium'

    def it_returns_lowercase_name_for_large(self) -> None:
        """Test marker_name property for LARGE size."""
        result = TestSize.LARGE.marker_name
        assert result == 'large'

    def it_returns_lowercase_name_for_xlarge(self) -> None:
        """Test marker_name property for XLARGE size."""
        result = TestSize.XLARGE.marker_name
        assert result == 'xlarge'


@pytest.mark.small
class DescribeTestSizeDescriptionProperty:
    """Test TestSize description property."""

    def it_returns_description_for_small(self) -> None:
        """Test description property for SMALL size includes constraint info."""
        result = TestSize.SMALL.description
        assert 'no network' in result
        assert '<1s' in result

    def it_returns_description_for_medium(self) -> None:
        """Test description property for MEDIUM size includes constraint info."""
        result = TestSize.MEDIUM.description
        assert 'localhost' in result
        assert '<5min' in result

    def it_returns_description_for_large(self) -> None:
        """Test description property for LARGE size includes constraint info."""
        result = TestSize.LARGE.description
        assert 'full network' in result
        assert '<15min' in result

    def it_returns_description_for_xlarge(self) -> None:
        """Test description property for XLARGE size includes constraint info."""
        result = TestSize.XLARGE.description
        assert 'full network' in result
        assert '<15min' in result


@pytest.mark.small
class DescribeTestSizeLabelProperty:
    """Test TestSize label property."""

    def it_returns_label_for_small(self) -> None:
        """Test label property for SMALL size."""
        result = TestSize.SMALL.label
        assert result == '[SMALL]'

    def it_returns_label_for_medium(self) -> None:
        """Test label property for MEDIUM size."""
        result = TestSize.MEDIUM.label
        assert result == '[MEDIUM]'

    def it_returns_label_for_large(self) -> None:
        """Test label property for LARGE size."""
        result = TestSize.LARGE.label
        assert result == '[LARGE]'

    def it_returns_label_for_xlarge(self) -> None:
        """Test label property for XLARGE size."""
        result = TestSize.XLARGE.label
        assert result == '[XLARGE]'


@pytest.mark.small
class DescribeTimerStateEnumIteration:
    """Test TimerState enum iteration and membership."""

    def it_provides_all_three_state_members(self) -> None:
        """Test that TimerState enum has exactly three members."""
        states = list(TimerState)
        assert len(states) == 3
        assert TimerState.READY in states
        assert TimerState.RUNNING in states
        assert TimerState.STOPPED in states


@pytest.mark.small
class DescribeTimingViolationErrorException:
    """Test TimingViolationError exception class."""

    def it_raises_with_timing_details(self) -> None:
        """Test that TimingViolationError can be raised with timing details."""
        with pytest.raises(TimingViolationError, match='exceeded time limit'):
            raise TimingViolationError(
                test_size=TestSize.SMALL,
                test_nodeid='tests/test_slow.py::test_compute',
                limit=1.0,
                actual=2.5,
            )

    def it_includes_error_code_in_message(self) -> None:
        """Test that TimingViolationError includes the error code in its message."""
        exc = TimingViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_slow.py::test_compute',
            limit=1.0,
            actual=2.5,
        )

        assert 'TC006' in str(exc)


@pytest.mark.small
class DescribeTestTimerStateMachine:
    """Test TestTimer state machine behavior."""

    def it_transitions_through_all_states(self) -> None:
        """Test that timer can transition through all states."""

        class ConcreteTimer(TestTimer):
            def duration(self) -> float:
                return 1.0

        timer = ConcreteTimer()

        # Initial state
        assert timer.state == TimerState.READY

        # Start transition
        timer.start()
        assert timer.state == TimerState.RUNNING  # type: ignore[comparison-overlap]

        # Stop transition
        timer.stop()  # type: ignore[unreachable]
        assert timer.state == TimerState.STOPPED

        # Reset transition
        timer.reset()
        assert timer.state == TimerState.READY
