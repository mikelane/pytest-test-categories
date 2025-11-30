"""Process blocking port interface for hermetic test enforcement.

This module defines the abstract interface (port) for subprocess/process control
during test execution. Following hexagonal architecture, this port defines
WHAT operations are available, while adapters define HOW they are implemented.

The pattern enables:
- Production adapter (`SubprocessPatchingBlocker`): Patches subprocess and os modules
  to intercept real process spawning
- Test adapter (`FakeProcessBlocker`): Controllable test double that records
  spawn attempts without actual patching

Example:
    Production usage (via plugin hooks):
    >>> blocker = SubprocessPatchingBlocker()
    >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
    >>> # Test runs, any subprocess.run() raises SubprocessViolationError
    >>> blocker.deactivate()

    Test usage:
    >>> blocker = FakeProcessBlocker()
    >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
    >>> assert blocker.is_active
    >>> blocker.check_spawn_allowed('python', ['script.py'])
    >>> assert len(blocker.spawn_attempts) == 1

See Also:
    - NetworkBlockerPort: Similar pattern in ports/network.py
    - FilesystemBlockerPort: Similar pattern in ports/filesystem.py
    - Planning: docs/planning/resource-isolation-feature.md

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


class SpawnAttempt(BaseModel, frozen=True):
    """Immutable record of a process spawn attempt.

    Used for tracking and reporting spawn attempts during test execution.
    This is useful for diagnostics and for test adapters that need to record
    what process spawns were attempted.

    Attributes:
        command: The command or executable being spawned.
        args: Arguments passed to the command.
        test_nodeid: The pytest node ID of the test that made the attempt.
        allowed: Whether the spawn was permitted.
        method: The method used to spawn (e.g., 'subprocess.run', 'os.system').

    Example:
        >>> attempt = SpawnAttempt(
        ...     command='python',
        ...     args=['script.py', '--verbose'],
        ...     test_nodeid='test_module.py::test_function',
        ...     allowed=False,
        ...     method='subprocess.run'
        ... )

    """

    command: str
    args: tuple[str, ...]
    test_nodeid: str
    allowed: bool
    method: str


class ProcessBlockerPort(BaseModel, ABC):
    """Abstract port defining process/subprocess blocking behavior.

    This port defines the contract for process spawning control during test
    execution. Implementations (adapters) provide the actual blocking
    mechanism.

    Following hexagonal architecture:
    - This port defines WHAT operations are available
    - Adapters define HOW they are implemented
    - Production adapter: SubprocessPatchingBlocker (patches subprocess, os)
    - Test adapter: FakeProcessBlocker (records attempts, no real patching)

    The blocker follows a state machine pattern:
    - INACTIVE: Not intercepting process spawns (initial state)
    - ACTIVE: Intercepting and potentially blocking process spawns

    State transitions are guarded by icontract preconditions/postconditions,
    following the same pattern as NetworkBlockerPort and FilesystemBlockerPort.
    The base class provides public methods with contracts that delegate to
    abstract _do_* methods.

    Process Blocking Rules by Test Size:
    - SMALL: Block all subprocess/process spawning
    - MEDIUM: Allow subprocess spawning (needed for pytester, etc.)
    - LARGE/XLARGE: Allow all process spawning

    Attributes:
        state: Current blocker state (INACTIVE or ACTIVE).

    Example:
        >>> class FakeProcessBlocker(ProcessBlockerPort):
        ...     def _do_activate(self, test_size, enforcement_mode):
        ...         # Record parameters for assertions
        ...         pass
        ...
        >>> blocker = FakeProcessBlocker()
        >>> assert blocker.state == BlockerState.INACTIVE
        >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        >>> assert blocker.state == BlockerState.ACTIVE

    See Also:
        - NetworkBlockerPort: Similar pattern in ports/network.py
        - FilesystemBlockerPort: Similar pattern in ports/filesystem.py
        - SubprocessPatchingBlocker: Production adapter
        - FakeProcessBlocker: Test adapter

    """

    model_config = {'arbitrary_types_allowed': True}

    state: BlockerState = BlockerState.INACTIVE
    violation_callback: object | None = None

    @require(lambda self: self.state == BlockerState.INACTIVE, 'Blocker must be INACTIVE to activate')
    @ensure(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE after activation')
    def activate(self, test_size: TestSize, enforcement_mode: EnforcementMode) -> None:
        """Activate process blocking for a test.

        Transitions the blocker from INACTIVE to ACTIVE state. Once active,
        the blocker will intercept process spawn attempts and handle
        them according to the enforcement mode and test size restrictions.

        Args:
            test_size: The size category of the current test. Determines
                what process spawning is allowed:
                - SMALL: Block all process spawning
                - MEDIUM/LARGE/XLARGE: Allow process spawning
            enforcement_mode: How to handle violations:
                - STRICT: Raise SubprocessViolationError
                - WARN: Emit warning, allow spawn
                - OFF: No enforcement

        Raises:
            icontract.ViolationError: If blocker is not in INACTIVE state.

        Example:
            >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
            >>> # Now any subprocess.run() call will be intercepted

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
        """Deactivate process blocking, restoring normal behavior.

        Transitions the blocker from ACTIVE to INACTIVE state. This should
        be called in a finally block to ensure process spawning is
        restored even if the test fails.

        Raises:
            icontract.ViolationError: If blocker is not in ACTIVE state.

        Example:
            >>> try:
            ...     blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
            ...     # test runs
            ... finally:
            ...     blocker.deactivate()  # Always restore process spawning

        """
        self._do_deactivate()
        self.state = BlockerState.INACTIVE

    @abstractmethod
    def _do_deactivate(self) -> None:
        """Perform adapter-specific deactivation logic.

        Subclasses implement this to perform adapter-specific deactivation.
        State transition is handled by the base class.

        """

    @require(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE to check spawns')
    def check_spawn_allowed(self, command: str, args: tuple[str, ...]) -> bool:
        """Check if spawning a process with command and args is allowed.

        This method is called by the subprocess interception mechanism to
        determine whether a process spawn should be permitted.

        The decision depends on:
        - The test size (set during activate())
        - SMALL tests cannot spawn any processes
        - MEDIUM/LARGE/XLARGE tests can spawn processes

        Args:
            command: The command or executable to spawn.
            args: Arguments to pass to the command.

        Returns:
            True if the spawn is allowed, False if it should be blocked.

        Raises:
            icontract.ViolationError: If blocker is not in ACTIVE state.

        Example:
            >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
            >>> blocker.check_spawn_allowed('python', ('script.py',))
            False  # Small tests cannot spawn processes
            >>> blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)
            >>> blocker.check_spawn_allowed('pytest', ('tests/',))
            True   # Medium tests can spawn processes

        """
        return self._do_check_spawn_allowed(command, args)

    @abstractmethod
    def _do_check_spawn_allowed(self, command: str, args: tuple[str, ...]) -> bool:
        """Determine if spawning a process is allowed.

        Subclasses implement this to determine if a spawn is allowed.

        Args:
            command: The command or executable to spawn.
            args: Arguments to pass to the command.

        Returns:
            True if the spawn is allowed, False if it should be blocked.

        """

    @require(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE to handle violations')
    def on_violation(
        self,
        command: str,
        args: tuple[str, ...],
        test_nodeid: str,
        method: str,
    ) -> None:
        """Handle a process spawn violation.

        Called when a test attempts to spawn a process that is not allowed
        according to its size category restrictions.

        The response depends on the enforcement mode (set during activate()):
        - STRICT: Raise SubprocessViolationError
        - WARN: Emit warning via pytest's warning system
        - OFF: Do nothing (should not be called in OFF mode)

        Args:
            command: The attempted command.
            args: The attempted arguments.
            test_nodeid: The pytest node ID of the violating test.
            method: The spawn method used (e.g., 'subprocess.run').

        Raises:
            SubprocessViolationError: If enforcement mode is STRICT.
            icontract.ViolationError: If blocker is not in ACTIVE state.

        Example:
            >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
            >>> blocker.on_violation('python', ('script.py',), 'test::fn', 'subprocess.run')
            SubprocessViolationError: Small tests cannot spawn subprocesses...

        """
        self._do_on_violation(command, args, test_nodeid, method)

    @abstractmethod
    def _do_on_violation(
        self,
        command: str,
        args: tuple[str, ...],
        test_nodeid: str,
        method: str,
    ) -> None:
        """Handle violations according to enforcement mode.

        Subclasses implement this to handle violations according to enforcement mode.

        Args:
            command: The attempted command.
            args: The attempted arguments.
            test_nodeid: The pytest node ID of the violating test.
            method: The spawn method used.

        """

    def reset(self) -> None:
        """Reset blocker to initial INACTIVE state.

        This is a convenience method for cleanup and testing. Unlike
        deactivate(), this does not require the blocker to be in ACTIVE
        state - it unconditionally resets to INACTIVE.

        Subclasses should override to perform any additional cleanup
        (e.g., restoring patched subprocess functions).

        Example:
            >>> blocker.reset()  # Safe to call regardless of current state
            >>> assert blocker.state == BlockerState.INACTIVE

        """
        self.state = BlockerState.INACTIVE
