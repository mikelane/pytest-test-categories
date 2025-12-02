"""Timing validation service for test execution.

This module provides the TimingValidationService that validates test execution
timing against fixed time limits. It follows hexagonal architecture by
depending on abstract ports rather than concrete pytest implementations.

The service encapsulates the logic for:
- Retrieving timers for test items
- Extracting duration from timers or reports
- Validating timing constraints against fixed limits
- Modifying test reports on timing violations

Test sizes have fixed time limits that are not configurable. This follows
Google's "Software Engineering at Google" philosophy where test sizes are
DEFINITIONS, not suggestions.

This is pure domain logic that can be tested without pytest.

Example:
    >>> from tests._fixtures.timer import FakeTimer
    >>> from pytest_test_categories.types import TestSize, TimerState
    >>> timer = FakeTimer(state=TimerState.STOPPED)
    >>> timer.advance(0.5)
    >>> service = TimingValidationService()
    >>> # Validate that 0.5s is within SMALL test limit (1s)
    >>> service.validate_timing(TestSize.SMALL, timer.duration())  # Returns None (success)

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytest_test_categories import timing
from pytest_test_categories.types import (
    TestSize,
    TestTimer,
    TimerState,
)

if TYPE_CHECKING:
    from collections.abc import MutableMapping


class TimingValidationService:
    """Service for validating test timing constraints.

    This service encapsulates the logic for validating that tests complete
    within their fixed time limits. It works with timers and test reports
    through abstract interfaces, making it testable without pytest dependencies.

    The service is stateless and thread-safe - all state is passed as parameters.

    Example:
        >>> service = TimingValidationService()
        >>> # Validate timing for a test
        >>> try:
        ...     service.validate_timing(TestSize.SMALL, 1.5)  # Exceeds 1s limit
        ... except TimingViolationError:
        ...     print('Test took too long')

    """

    def validate_timing(
        self,
        test_size: TestSize,
        duration: float,
    ) -> None:
        """Validate that a test completed within its fixed time limit.

        Delegates to the timing module's validate() function to check if
        the duration is within the fixed limit for the test size.

        Test sizes have fixed time limits:
        - Small: 1 second
        - Medium: 300 seconds (5 minutes)
        - Large: 900 seconds (15 minutes)
        - XLarge: 900 seconds (15 minutes)

        Args:
            test_size: The size category of the test.
            duration: The test duration in seconds.

        Raises:
            TimingViolationError: If the test exceeded its time limit.

        Example:
            >>> service = TimingValidationService()
            >>> service.validate_timing(TestSize.SMALL, 0.5)  # OK
            >>> service.validate_timing(TestSize.SMALL, 2.0)  # Raises TimingViolationError

        """
        timing.validate(test_size, duration)

    def get_test_duration(
        self,
        timer: TestTimer | None,
        report_duration: float | None,
    ) -> float | None:
        """Extract test duration from timer or report.

        Attempts to get the duration from multiple sources in priority order:
        1. Report duration (most reliable for capturing actual execution time)
        2. Timer duration (if timer is stopped)
        3. None (if no duration available)

        This function handles all the edge cases and exceptions that can occur
        when extracting durations.

        Args:
            timer: The timer for this test (may be None).
            report_duration: Duration from the test report (may be None).

        Returns:
            The test duration in seconds, or None if unavailable.

        Example:
            >>> timer = FakeTimer(state=TimerState.STOPPED)
            >>> timer.advance(0.5)
            >>> service = TimingValidationService()
            >>> # Report duration takes precedence
            >>> service.get_test_duration(timer, 0.6)
            0.6
            >>> # Falls back to timer duration
            >>> service.get_test_duration(timer, None)
            0.5
            >>> # Returns None if no duration available
            >>> service.get_test_duration(None, None)
            None

        """
        # Prefer report duration as it's more reliable
        if report_duration is not None:
            return report_duration

        # Fall back to timer duration if available
        if timer is not None and timer.state == TimerState.STOPPED:
            try:
                return timer.duration()
            except (RuntimeError, ValueError):
                # Timer had an error - return None
                return None

        # No duration available
        return None

    def cleanup_timer(self, timers: MutableMapping[str, TestTimer], nodeid: str) -> None:
        """Remove a timer from the timers dictionary to prevent memory leaks.

        This is a utility function for cleaning up timers after test execution.
        It modifies the timers dict in place.

        Args:
            timers: Dictionary mapping node IDs to timers.
            nodeid: The node ID of the test to clean up.

        Example:
            >>> timers = {'test.py::test_func': FakeTimer()}
            >>> service = TimingValidationService()
            >>> service.cleanup_timer(timers, 'test.py::test_func')
            >>> len(timers)
            0

        """
        timers.pop(nodeid, None)
