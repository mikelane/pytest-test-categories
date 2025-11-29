"""Fake sleep blocker adapter for testing.

This module provides a test double for the SleepBlockerPort that allows
controllable simulation of sleep blocking without actual patching.
This enables fast, deterministic unit tests.

The FakeSleepBlocker follows hexagonal architecture principles:
- Implements the SleepBlockerPort interface (port)
- Provides controllable behavior for testing
- Records sleep attempts and method invocations
- No actual time.sleep or asyncio.sleep patching

Example:
    >>> blocker = FakeSleepBlocker()
    >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
    >>> blocker.check_sleep_allowed('time.sleep', 0.1)
    False
    >>> assert len(blocker.sleep_attempts) == 1

See Also:
    - SleepBlockerPort: The abstract interface in ports/sleep.py
    - SleepPatchingBlocker: Production adapter in adapters/sleep.py
    - FakeDatabaseBlocker: Similar test double pattern for database blocking

"""

from __future__ import annotations

from pydantic import Field

from pytest_test_categories.exceptions import SleepViolationError
from pytest_test_categories.ports.network import EnforcementMode
from pytest_test_categories.ports.sleep import (
    SleepAttempt,
    SleepBlockerPort,
)
from pytest_test_categories.types import TestSize


class FakeSleepBlocker(SleepBlockerPort):
    """Test double for sleep blocking that records attempts without real patching.

    This adapter is designed for unit testing code that uses sleep blocking.
    It tracks all method calls and sleep attempts for verification in tests.

    Attributes:
        state: Current blocker state (inherited from SleepBlockerPort).
        current_test_size: The test size set during activation.
        current_enforcement_mode: The enforcement mode set during activation.
        sleep_attempts: List of recorded sleep call attempts.
        warnings: List of warning messages generated in WARN mode.
        activate_count: Number of times activate() was called.
        deactivate_count: Number of times deactivate() was called.
        check_count: Number of times check_sleep_allowed() was called.

    Example:
        >>> blocker = FakeSleepBlocker()
        >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        >>> assert blocker.check_sleep_allowed('time.sleep', 0.1) is False
        >>> assert blocker.check_count == 1

    """

    current_test_size: TestSize | None = Field(default=None, description='Test size')
    current_enforcement_mode: EnforcementMode | None = Field(default=None, description='Enforcement mode')
    sleep_attempts: list[SleepAttempt] = Field(default_factory=list, description='Sleep attempts')
    warnings: list[str] = Field(default_factory=list, description='Warning messages')
    activate_count: int = Field(default=0, description='Count of activate() calls')
    deactivate_count: int = Field(default=0, description='Count of deactivate() calls')
    check_count: int = Field(default=0, description='Count of check calls')

    def _do_activate(
        self,
        test_size: TestSize,
        enforcement_mode: EnforcementMode,
    ) -> None:
        """Record activation parameters for test verification.

        State transition is handled by the base class.

        Args:
            test_size: The size category of the current test.
            enforcement_mode: How to handle violations.

        """
        self.current_test_size = test_size
        self.current_enforcement_mode = enforcement_mode
        self.activate_count += 1

    def _do_deactivate(self) -> None:
        """Record deactivation for test verification.

        State transition is handled by the base class.

        """
        self.deactivate_count += 1

    def _do_check_sleep_allowed(self, function: str, duration: float) -> bool:
        """Check if sleep call is allowed and record the attempt.

        Returns whether sleep would be allowed based on the test size:
        - SMALL: Block all sleep calls
        - MEDIUM/LARGE/XLARGE: Allow all sleep calls

        Args:
            function: The sleep function name.
            duration: The sleep duration in seconds.

        Returns:
            True if the sleep is allowed, False if it should be blocked.

        """
        self.check_count += 1

        allowed = self._is_sleep_allowed()

        self.sleep_attempts.append(
            SleepAttempt(
                function=function,
                duration=duration,
                test_nodeid='',
                allowed=allowed,
            )
        )

        return allowed

    def _is_sleep_allowed(self) -> bool:
        """Determine if sleep call is allowed based on test size.

        Returns:
            True if allowed, False otherwise.

        """
        return self.current_test_size != TestSize.SMALL

    def _do_on_violation(
        self,
        function: str,
        duration: float,
        test_nodeid: str,
    ) -> None:
        """Handle a sleep violation based on enforcement mode.

        Behavior:
        - STRICT: Raise SleepViolationError
        - WARN: Record warning message
        - OFF: Do nothing

        Args:
            function: The sleep function name.
            duration: The sleep duration in seconds.
            test_nodeid: The pytest node ID of the violating test.

        Raises:
            SleepViolationError: If enforcement mode is STRICT.

        """
        if self.current_enforcement_mode == EnforcementMode.STRICT:
            raise SleepViolationError(
                test_size=self.current_test_size,  # type: ignore[arg-type]
                test_nodeid=test_nodeid,
                function=function,
                duration=duration,
            )

        if self.current_enforcement_mode == EnforcementMode.WARN:
            warning_msg = f'Sleep violation: {function}({duration}) in test {test_nodeid}'
            self.warnings.append(warning_msg)

    def reset(self) -> None:
        """Reset blocker to initial state, clearing all recorded data.

        This is safe to call regardless of current state.

        """
        super().reset()
        self.current_test_size = None
        self.current_enforcement_mode = None
        self.sleep_attempts = []
        self.warnings = []
