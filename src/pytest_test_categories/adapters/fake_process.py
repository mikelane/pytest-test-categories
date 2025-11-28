"""Fake process blocker adapter for testing.

This module provides a test double for the ProcessBlockerPort that allows
controllable simulation of process blocking without actual patching.
This enables fast, deterministic unit tests.

The FakeProcessBlocker follows hexagonal architecture principles:
- Implements the ProcessBlockerPort interface (port)
- Provides controllable behavior for testing
- Records spawn attempts and method invocations
- No actual subprocess/os module patching

Example:
    >>> blocker = FakeProcessBlocker()
    >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
    >>> blocker.check_spawn_allowed('python', ('script.py',))
    False
    >>> assert len(blocker.spawn_attempts) == 1

See Also:
    - ProcessBlockerPort: The abstract interface in ports/process.py
    - SubprocessPatchingBlocker: Production adapter in adapters/process.py
    - FakeNetworkBlocker: Similar test double pattern for network blocking
    - FakeFilesystemBlocker: Similar test double pattern for filesystem blocking

"""

from __future__ import annotations

from pydantic import Field

from pytest_test_categories.exceptions import SubprocessViolationError
from pytest_test_categories.ports.network import EnforcementMode
from pytest_test_categories.ports.process import (
    ProcessBlockerPort,
    SpawnAttempt,
)
from pytest_test_categories.types import TestSize


class FakeProcessBlocker(ProcessBlockerPort):
    """Test double for process blocking that records attempts without real patching.

    This adapter is designed for unit testing code that uses process blocking.
    It tracks all method calls and spawn attempts for verification in tests.

    Attributes:
        state: Current blocker state (inherited from ProcessBlockerPort).
        current_test_size: The test size set during activation.
        current_enforcement_mode: The enforcement mode set during activation.
        spawn_attempts: List of recorded process spawn attempts.
        warnings: List of warning messages generated in WARN mode.
        activate_count: Number of times activate() was called.
        deactivate_count: Number of times deactivate() was called.
        check_count: Number of times check_spawn_allowed() was called.

    Example:
        >>> blocker = FakeProcessBlocker()
        >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        >>> assert blocker.check_spawn_allowed('python', ('script.py',)) is False
        >>> assert blocker.check_count == 1

    """

    current_test_size: TestSize | None = Field(default=None, description='Test size')
    current_enforcement_mode: EnforcementMode | None = Field(default=None, description='Enforcement mode')
    spawn_attempts: list[SpawnAttempt] = Field(default_factory=list, description='Spawn attempts')
    warnings: list[str] = Field(default_factory=list, description='Warning messages')
    activate_count: int = Field(default=0, description='Count of activate() calls')
    deactivate_count: int = Field(default=0, description='Count of deactivate() calls')
    check_count: int = Field(default=0, description='Count of check calls')

    def _do_activate(self, test_size: TestSize, enforcement_mode: EnforcementMode) -> None:
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

    def _do_check_spawn_allowed(self, command: str, args: tuple[str, ...]) -> bool:
        """Check if process spawn is allowed and record the attempt.

        Returns whether spawn would be allowed based on the test size:
        - SMALL: Block all process spawning
        - MEDIUM/LARGE/XLARGE: Allow all process spawning

        Args:
            command: The command or executable to spawn.
            args: Arguments to pass to the command.

        Returns:
            True if the spawn is allowed, False if it should be blocked.

        """
        self.check_count += 1

        allowed = self._is_spawn_allowed()

        self.spawn_attempts.append(
            SpawnAttempt(
                command=command,
                args=args,
                test_nodeid='',
                allowed=allowed,
                method='check_spawn_allowed',
            )
        )

        return allowed

    def _is_spawn_allowed(self) -> bool:
        """Determine if process spawn is allowed based on test size.

        Returns:
            True if allowed, False otherwise.

        """
        return self.current_test_size != TestSize.SMALL

    def _do_on_violation(
        self,
        command: str,
        args: tuple[str, ...],
        test_nodeid: str,
        method: str,
    ) -> None:
        """Handle a process spawn violation based on enforcement mode.

        Behavior:
        - STRICT: Raise SubprocessViolationError
        - WARN: Record warning message
        - OFF: Do nothing

        Args:
            command: The attempted command.
            args: The attempted arguments.
            test_nodeid: The pytest node ID of the violating test.
            method: The spawn method used.

        Raises:
            SubprocessViolationError: If enforcement mode is STRICT.

        """
        if self.current_enforcement_mode == EnforcementMode.STRICT:
            raise SubprocessViolationError(
                test_size=self.current_test_size,  # type: ignore[arg-type]
                test_nodeid=test_nodeid,
                command=command,
                command_args=args,
                method=method,
            )

        if self.current_enforcement_mode == EnforcementMode.WARN:
            args_str = ' '.join(args) if args else '(no args)'
            warning_msg = f'Subprocess violation: {method} {command} {args_str} in test {test_nodeid}'
            self.warnings.append(warning_msg)

    def reset(self) -> None:
        """Reset blocker to initial state, clearing all recorded data.

        This is safe to call regardless of current state.

        """
        super().reset()
        self.current_test_size = None
        self.current_enforcement_mode = None
        self.spawn_attempts = []
        self.warnings = []
