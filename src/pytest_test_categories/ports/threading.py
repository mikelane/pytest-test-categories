"""Thread monitoring port interface for small test enforcement.

This module defines the abstract interface (port) for thread creation monitoring
during test execution. Following hexagonal architecture, this port defines
WHAT operations are available, while adapters define HOW they are implemented.

Unlike other blockers (network, filesystem, process) that BLOCK operations,
the thread monitor WARNS when small tests use threading. This is because:
1. Many libraries use threading internally (logging, garbage collection)
2. Some test frameworks use threading
3. Blocking threading could break legitimate test infrastructure

The pattern enables:
- Production adapter (`ThreadPatchingMonitor`): Patches threading.Thread to intercept
  real thread creations and emit pytest warnings
- Test adapter (`FakeThreadMonitor`): Controllable test double that records
  thread creation attempts without actual patching

Example:
    Production usage (via plugin hooks):
    >>> monitor = ThreadPatchingMonitor()
    >>> monitor.activate(TestSize.SMALL, EnforcementMode.WARN)
    >>> # Test runs, any threading.Thread() emits PytestWarning
    >>> monitor.deactivate()

    Test usage:
    >>> monitor = FakeThreadMonitor()
    >>> monitor.activate(TestSize.SMALL, EnforcementMode.WARN)
    >>> assert monitor.is_monitoring
    >>> monitor.on_thread_creation('threading.Thread', 'test::fn')
    >>> assert len(monitor.warnings) == 1

See Also:
    - NetworkBlockerPort: Similar pattern in ports/network.py (but blocks)
    - ProcessBlockerPort: Similar pattern in ports/process.py (but blocks)
    - Google SWE Book: Test size definitions (small = single-threaded)

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


class ThreadCreationAttempt(BaseModel, frozen=True):
    """Immutable record of a thread creation attempt.

    Used for tracking and reporting thread creation attempts during test execution.
    This is useful for diagnostics and for test adapters that need to record
    what thread creations were attempted.

    Attributes:
        thread_type: The type of thread being created (e.g., 'threading.Thread').
        test_nodeid: The pytest node ID of the test that made the attempt.

    Example:
        >>> attempt = ThreadCreationAttempt(
        ...     thread_type='threading.Thread',
        ...     test_nodeid='test_module.py::test_function',
        ... )

    """

    thread_type: str
    test_nodeid: str


class ThreadMonitorPort(BaseModel, ABC):
    """Abstract port defining thread monitoring behavior.

    This port defines the contract for thread creation monitoring during test
    execution. Implementations (adapters) provide the actual monitoring
    mechanism.

    Following hexagonal architecture:
    - This port defines WHAT operations are available
    - Adapters define HOW they are implemented
    - Production adapter: ThreadPatchingMonitor (patches threading.Thread)
    - Test adapter: FakeThreadMonitor (records attempts, no real patching)

    The monitor follows a state machine pattern:
    - INACTIVE: Not intercepting thread creations (initial state)
    - ACTIVE: Intercepting and potentially warning on thread creations

    State transitions are guarded by icontract preconditions/postconditions,
    following the same pattern as NetworkBlockerPort. The base class provides
    public methods with contracts that delegate to abstract _do_* methods.

    Key Difference from Other Blockers:
    This monitor WARNS instead of blocking. Unlike network/filesystem/process
    blocking, threading is harder to completely block because many libraries
    use threading internally. Warnings allow detection while not breaking
    legitimate infrastructure.

    Monitoring Rules by Test Size:
    - SMALL: Warn on thread creation (tests should be single-threaded)
    - MEDIUM: No monitoring (threading allowed)
    - LARGE/XLARGE: No monitoring (threading allowed)

    Attributes:
        state: Current monitor state (INACTIVE or ACTIVE).

    Example:
        >>> class FakeThreadMonitor(ThreadMonitorPort):
        ...     def _do_activate(self, test_size, enforcement_mode):
        ...         # Record parameters for assertions
        ...         pass
        ...
        >>> monitor = FakeThreadMonitor()
        >>> assert monitor.state == BlockerState.INACTIVE
        >>> monitor.activate(TestSize.SMALL, EnforcementMode.WARN)
        >>> assert monitor.state == BlockerState.ACTIVE

    See Also:
        - NetworkBlockerPort: Similar pattern in ports/network.py
        - ThreadPatchingMonitor: Production adapter
        - FakeThreadMonitor: Test adapter

    """

    state: BlockerState = BlockerState.INACTIVE

    @property
    @abstractmethod
    def is_monitoring(self) -> bool:
        """Return True if the monitor is actively watching for thread creation.

        This is True only when the monitor is ACTIVE and the test size is SMALL.

        Returns:
            True if monitoring is active, False otherwise.

        """

    @require(lambda self: self.state == BlockerState.INACTIVE, 'Monitor must be INACTIVE to activate')
    @ensure(lambda self: self.state == BlockerState.ACTIVE, 'Monitor must be ACTIVE after activation')
    def activate(self, test_size: TestSize, enforcement_mode: EnforcementMode) -> None:
        """Activate thread monitoring for a test.

        Transitions the monitor from INACTIVE to ACTIVE state. Once active,
        the monitor will intercept thread creation attempts and warn
        according to the enforcement mode and test size restrictions.

        Args:
            test_size: The size category of the current test. Determines
                whether monitoring is active:
                - SMALL: Monitor thread creation, emit warnings
                - MEDIUM/LARGE/XLARGE: No monitoring
            enforcement_mode: How to handle detections:
                - WARN: Emit pytest warning (recommended)
                - OFF: No warnings

        Raises:
            icontract.ViolationError: If monitor is not in INACTIVE state.

        Example:
            >>> monitor.activate(TestSize.SMALL, EnforcementMode.WARN)
            >>> # Now any threading.Thread() call will emit a warning

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
            enforcement_mode: How to handle detections.

        """

    @require(lambda self: self.state == BlockerState.ACTIVE, 'Monitor must be ACTIVE to deactivate')
    @ensure(lambda self: self.state == BlockerState.INACTIVE, 'Monitor must be INACTIVE after deactivation')
    def deactivate(self) -> None:
        """Deactivate thread monitoring, restoring normal threading behavior.

        Transitions the monitor from ACTIVE to INACTIVE state. This should
        be called in a finally block to ensure threading is restored even
        if the test fails.

        Raises:
            icontract.ViolationError: If monitor is not in ACTIVE state.

        Example:
            >>> try:
            ...     monitor.activate(TestSize.SMALL, EnforcementMode.WARN)
            ...     # test runs
            ... finally:
            ...     monitor.deactivate()  # Always restore threading

        """
        self._do_deactivate()
        self.state = BlockerState.INACTIVE

    @abstractmethod
    def _do_deactivate(self) -> None:
        """Perform adapter-specific deactivation logic.

        Subclasses implement this to perform adapter-specific deactivation.
        State transition is handled by the base class.

        """

    @require(lambda self: self.state == BlockerState.ACTIVE, 'Monitor must be ACTIVE to handle thread creation')
    def on_thread_creation(self, thread_type: str, test_nodeid: str) -> None:
        """Handle a thread creation event.

        Called when a test creates a thread. For small tests with WARN mode,
        this emits a pytest warning indicating that the test uses threading.

        Args:
            thread_type: The type of thread being created (e.g., 'threading.Thread').
            test_nodeid: The pytest node ID of the test creating the thread.

        Raises:
            icontract.ViolationError: If monitor is not in ACTIVE state.

        Example:
            >>> monitor.activate(TestSize.SMALL, EnforcementMode.WARN)
            >>> monitor.on_thread_creation('threading.Thread', 'test_mod::test_fn')
            # Emits: PytestWarning: Small test 'test_mod::test_fn' uses threading.

        """
        self._do_on_thread_creation(thread_type, test_nodeid)

    @abstractmethod
    def _do_on_thread_creation(self, thread_type: str, test_nodeid: str) -> None:
        """Handle thread creation according to enforcement mode.

        Subclasses implement this to handle thread creation according to
        enforcement mode.

        Args:
            thread_type: The type of thread being created.
            test_nodeid: The pytest node ID of the test creating the thread.

        """

    def reset(self) -> None:
        """Reset monitor to initial INACTIVE state.

        This is a convenience method for cleanup and testing. Unlike
        deactivate(), this does not require the monitor to be in ACTIVE
        state - it unconditionally resets to INACTIVE.

        Subclasses should override to perform any additional cleanup
        (e.g., restoring patched threading classes).

        Example:
            >>> monitor.reset()  # Safe to call regardless of current state
            >>> assert monitor.state == BlockerState.INACTIVE

        """
        self.state = BlockerState.INACTIVE
