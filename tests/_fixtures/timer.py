"""Timer fixtures for testing."""

from __future__ import annotations

from typing import Annotated

import pytest
from pydantic import Field

from pytest_test_categories.types import (
    TestTimer,
    TimerState,
)


class MockTimer(TestTimer):
    """A mock timer implementation for testing."""

    desired_duration: float = Annotated[float, Field(gt=0, default=1.0)]

    def start(self) -> None:
        """Start the mock timer."""
        self.state = TimerState.RUNNING

    def stop(self) -> None:
        """Stop the mock timer."""
        self.state = TimerState.STOPPED

    def duration(self) -> float:
        """Get the duration of the test."""
        return self.desired_duration


@pytest.fixture
def mock_timer(
    request: pytest.FixtureRequest,
    duration: Annotated[float, 'Must be positive'] = 1.0,
) -> MockTimer:
    """Create a MockTimer with the specified duration.

    Args:
        request: The pytest request object for parametrization.
        duration: The default duration to use if not parametrized (must be positive).

    Returns:
        A MockTimer configured with the specified duration.

    Note:
        When used with parametrize, the parametrized value overrides the duration parameter.
        Both the parametrized and direct duration values must be positive.

    Raises:
        RuntimeError: If the duration (either parametrized or direct) is not positive.

    """
    return MockTimer(desired_duration=getattr(request, 'param', duration))