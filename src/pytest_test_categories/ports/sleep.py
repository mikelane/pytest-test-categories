"""Sleep blocking port interface for hermetic test enforcement.

This module defines the abstract interface (port) for sleep/timing control
during test execution. Following hexagonal architecture, this port defines
WHAT operations are available, while adapters define HOW they are implemented.

The pattern enables:
- Production adapter (`SleepPatchingBlocker`): Patches time.sleep, asyncio.sleep,
  and other timing functions to intercept real sleep calls
- Test adapter (`FakeSleepBlocker`): Controllable test double that records
  sleep attempts without actual patching

Sleep calls are blocked in small tests because:
- Small tests should be hermetic and not depend on wall-clock time
- Sleep indicates flaky timing assumptions or improper synchronization
- Proper patterns like condition-based waiting should be used instead
- Small tests must be fast and deterministic

Example:
    Production usage (via plugin hooks):
    >>> blocker = SleepPatchingBlocker()
    >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
    >>> # Test runs, any time.sleep() raises SleepViolationError
    >>> blocker.deactivate()

    Test usage:
    >>> blocker = FakeSleepBlocker()
    >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
    >>> assert blocker.is_active
    >>> blocker.check_sleep_allowed('time.sleep', 0.1)
    >>> assert len(blocker.sleep_attempts) == 1

See Also:
    - NetworkBlockerPort: Similar pattern in ports/network.py
    - ProcessBlockerPort: Similar pattern in ports/process.py
    - DatabaseBlockerPort: Similar pattern in ports/database.py

"""

from __future__ import annotations

from abc import (
    ABC,
    abstractmethod,
)
from typing import TYPE_CHECKING

from icontract import (
    ensure,
    require,
)
from pydantic import BaseModel

from pytest_test_categories.ports.network import (
    BlockerState,
    EnforcementMode,
)

if TYPE_CHECKING:
    from pytest_test_categories.types import TestSize


class SleepAttempt(BaseModel, frozen=True):
    """Immutable record of a sleep call attempt.

    Used for tracking and reporting sleep attempts during test execution.
    This is useful for diagnostics and for test adapters that need to record
    what sleep calls were attempted.

    Attributes:
        function: The sleep function called (e.g., 'time.sleep', 'asyncio.sleep').
        duration: The sleep duration in seconds.
        test_nodeid: The pytest node ID of the test that made the attempt.
        allowed: Whether the sleep was permitted.

    Example:
        >>> attempt = SleepAttempt(
        ...     function='time.sleep',
        ...     duration=0.1,
        ...     test_nodeid='test_module.py::test_function',
        ...     allowed=False
        ... )

    """

    function: str
    duration: float
    test_nodeid: str
    allowed: bool


class SleepBlockerPort(BaseModel, ABC):
    """Abstract port defining sleep blocking behavior.

    This port defines the contract for sleep/timing control during test
    execution. Implementations (adapters) provide the actual blocking
    mechanism.

    Following hexagonal architecture:
    - This port defines WHAT operations are available
    - Adapters define HOW they are implemented
    - Production adapter: SleepPatchingBlocker (patches time.sleep, asyncio.sleep)
    - Test adapter: FakeSleepBlocker (records attempts, no real patching)

    The blocker follows a state machine pattern:
    - INACTIVE: Not intercepting sleep calls (initial state)
    - ACTIVE: Intercepting and potentially blocking sleep calls

    State transitions are guarded by icontract preconditions/postconditions,
    following the same pattern as TestTimer, NetworkBlockerPort, and other ports.

    Attributes:
        state: Current blocker state (INACTIVE or ACTIVE).

    Example:
        >>> class FakeSleepBlocker(SleepBlockerPort):
        ...     def _do_activate(self, test_size, enforcement_mode):
        ...         # Record parameters for assertions
        ...         pass
        ...
        >>> blocker = FakeSleepBlocker()
        >>> assert blocker.state == BlockerState.INACTIVE
        >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        >>> assert blocker.state == BlockerState.ACTIVE

    See Also:
        - TestTimer: Similar state machine pattern in types.py
        - NetworkBlockerPort: Similar pattern in ports/network.py
        - SleepPatchingBlocker: Production adapter
        - FakeSleepBlocker: Test adapter

    """

    model_config = {'arbitrary_types_allowed': True}

    state: BlockerState = BlockerState.INACTIVE
    violation_callback: object | None = None

    @require(lambda self: self.state == BlockerState.INACTIVE, 'Blocker must be INACTIVE to activate')
    @ensure(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE after activation')
    def activate(self, test_size: TestSize, enforcement_mode: EnforcementMode) -> None:
        """Activate sleep blocking for a test.

        Transitions the blocker from INACTIVE to ACTIVE state. Once active,
        the blocker will intercept sleep call attempts and handle
        them according to the enforcement mode and test size restrictions.

        Args:
            test_size: The size category of the current test. Determines
                what sleep calls are allowed:
                - SMALL: Block all sleep calls
                - MEDIUM: Allow all sleep calls
                - LARGE/XLARGE: Allow all sleep calls
            enforcement_mode: How to handle violations:
                - STRICT: Raise SleepViolationError
                - WARN: Emit warning, allow sleep
                - OFF: No enforcement

        Raises:
            icontract.ViolationError: If blocker is not in INACTIVE state.

        Example:
            >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
            >>> # Now any time.sleep() call will be intercepted

        """
        self._do_activate(test_size, enforcement_mode)
        self.state = BlockerState.ACTIVE

    @abstractmethod
    def _do_activate(self, test_size: TestSize, enforcement_mode: EnforcementMode) -> None:
        """Perform adapter-specific activation logic.

        Subclasses implement this to perform adapter-specific activation.
        State transition is handled by the base class.

        Args:
            test_size: The size category of the current test.
            enforcement_mode: How to handle violations.

        """

    @require(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE to deactivate')
    @ensure(lambda self: self.state == BlockerState.INACTIVE, 'Blocker must be INACTIVE after deactivation')
    def deactivate(self) -> None:
        """Deactivate sleep blocking, restoring normal behavior.

        Transitions the blocker from ACTIVE to INACTIVE state. This should
        be called in a finally block to ensure sleep functions are restored
        even if the test fails.

        Raises:
            icontract.ViolationError: If blocker is not in ACTIVE state.

        Example:
            >>> try:
            ...     blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
            ...     # test runs
            ... finally:
            ...     blocker.deactivate()  # Always restore sleep functions

        """
        self._do_deactivate()
        self.state = BlockerState.INACTIVE

    @abstractmethod
    def _do_deactivate(self) -> None:
        """Perform adapter-specific deactivation logic.

        Subclasses implement this to perform adapter-specific deactivation.
        State transition is handled by the base class.

        """

    @require(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE to check sleep')
    def check_sleep_allowed(self, function: str, duration: float) -> bool:
        """Check if a sleep call is allowed.

        This method is called by the sleep interception mechanism to
        determine whether a sleep call should be permitted.

        The decision depends on:
        - The test size (set during activate())
        - SMALL tests cannot use any sleep functions
        - MEDIUM/LARGE/XLARGE tests can use sleep functions

        Args:
            function: The sleep function name (e.g., 'time.sleep', 'asyncio.sleep').
            duration: The sleep duration in seconds.

        Returns:
            True if the sleep is allowed, False if it should be blocked.

        Raises:
            icontract.ViolationError: If blocker is not in ACTIVE state.

        Example:
            >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
            >>> blocker.check_sleep_allowed('time.sleep', 0.1)
            False  # Small tests cannot use sleep
            >>> blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)
            >>> blocker.check_sleep_allowed('time.sleep', 1.0)
            True   # Medium tests can use sleep

        """
        return self._do_check_sleep_allowed(function, duration)

    @abstractmethod
    def _do_check_sleep_allowed(self, function: str, duration: float) -> bool:
        """Determine if a sleep call is allowed.

        Subclasses implement this to determine if a sleep is allowed.

        Args:
            function: The sleep function name.
            duration: The sleep duration in seconds.

        Returns:
            True if the sleep is allowed, False if it should be blocked.

        """

    @require(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE to handle violations')
    def on_violation(self, function: str, duration: float, test_nodeid: str) -> None:
        """Handle a sleep violation.

        Called when a test attempts a sleep call that is not allowed
        according to its size category restrictions.

        The response depends on the enforcement mode (set during activate()):
        - STRICT: Raise SleepViolationError
        - WARN: Emit warning via pytest's warning system
        - OFF: Do nothing (should not be called in OFF mode)

        Args:
            function: The sleep function name.
            duration: The sleep duration in seconds.
            test_nodeid: The pytest node ID of the violating test.

        Raises:
            SleepViolationError: If enforcement mode is STRICT.
            icontract.ViolationError: If blocker is not in ACTIVE state.

        Example:
            >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
            >>> blocker.on_violation('time.sleep', 0.1, 'test_mod::test_fn')
            SleepViolationError: Small tests cannot use time.sleep()...

        """
        self._do_on_violation(function, duration, test_nodeid)

    @abstractmethod
    def _do_on_violation(self, function: str, duration: float, test_nodeid: str) -> None:
        """Handle violations according to enforcement mode.

        Subclasses implement this to handle violations according to enforcement mode.

        Args:
            function: The sleep function name.
            duration: The sleep duration in seconds.
            test_nodeid: The pytest node ID of the violating test.

        """

    def reset(self) -> None:
        """Reset blocker to initial INACTIVE state.

        This is a convenience method for cleanup and testing. Unlike
        deactivate(), this does not require the blocker to be in ACTIVE
        state - it unconditionally resets to INACTIVE.

        Subclasses should override to perform any additional cleanup
        (e.g., restoring patched sleep functions).

        Example:
            >>> blocker.reset()  # Safe to call regardless of current state
            >>> assert blocker.state == BlockerState.INACTIVE

        """
        self.state = BlockerState.INACTIVE
