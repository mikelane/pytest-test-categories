"""Filesystem blocking port interface for hermetic test enforcement.

This module defines the abstract interface (port) for filesystem access control
during test execution. Following hexagonal architecture, this port defines
WHAT operations are available, while adapters define HOW they are implemented.

The pattern enables:
- Production adapter (`FilesystemPatchingBlocker`): Patches filesystem operations
  (builtins.open, pathlib.Path, os module) to intercept real filesystem access
- Test adapter (`FakeFilesystemBlocker`): Controllable test double that records
  access attempts without actual patching

Example:
    Production usage (via plugin hooks):
    >>> blocker = FilesystemPatchingBlocker()
    >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())
    >>> # Test runs, any file access raises HermeticityViolationError
    >>> blocker.deactivate()

    Test usage:
    >>> blocker = FakeFilesystemBlocker()
    >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())
    >>> assert blocker.is_active
    >>> blocker.check_access_allowed(Path('/etc/passwd'), FilesystemOperation.READ)
    >>> assert len(blocker.access_attempts) == 1

See Also:
    - ADR-002: docs/architecture/adr-002-filesystem-isolation.md
    - NetworkBlockerPort: Similar pattern in ports/network.py
    - Planning: docs/planning/resource-isolation-feature.md

"""

from __future__ import annotations

from abc import (
    ABC,
    abstractmethod,
)
from enum import StrEnum
from pathlib import Path  # noqa: TC003 - Required at runtime for Pydantic
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


class FilesystemOperation(StrEnum):
    """Categories of filesystem operations for access control.

    Different test sizes may allow different operation types:
    - SMALL: No operations allowed (except on allowed paths)
    - MEDIUM: All operations allowed
    - LARGE/XLARGE: All operations allowed

    Note: STAT operations (exists(), is_file(), etc.) are treated the same
    as other operations - they are blocked on non-allowed paths and permitted
    on allowed paths. There is no special exemption for read-only metadata
    operations, as they still create dependencies on external filesystem state
    and violate hermeticity.

    Attributes:
        READ: Reading file contents (open() for reading, Path.read_text(), etc.)
        WRITE: Writing file contents (open() for writing, Path.write_text(), etc.)
        DELETE: Deleting files/directories (os.remove(), Path.unlink(), shutil.rmtree())
        CREATE: Creating files/directories (mkdir(), touch(), open() with 'x' mode)
        MODIFY: Modifying file metadata (chmod(), chown(), rename())
        STAT: Reading file metadata (stat(), exists(), is_file() - blocked on non-allowed paths)
        LIST: Listing directory contents (listdir(), scandir(), iterdir())

    """

    READ = 'read'
    WRITE = 'write'
    DELETE = 'delete'
    CREATE = 'create'
    MODIFY = 'modify'
    STAT = 'stat'
    LIST = 'list'


class FilesystemAccessAttempt(BaseModel, frozen=True):
    """Immutable record of a filesystem access attempt.

    Used for tracking and reporting access attempts during test execution.
    This is useful for diagnostics and for test adapters that need to record
    what filesystem operations were attempted.

    Attributes:
        path: The target path (resolved to absolute).
        operation: The type of filesystem operation.
        test_nodeid: The pytest node ID of the test that made the attempt.
        allowed: Whether the access was permitted.

    Example:
        >>> attempt = FilesystemAccessAttempt(
        ...     path=Path('/home/user/project/data.json'),
        ...     operation=FilesystemOperation.READ,
        ...     test_nodeid='test_module.py::test_function',
        ...     allowed=False
        ... )

    """

    path: Path
    operation: FilesystemOperation
    test_nodeid: str
    allowed: bool


class FilesystemBlockerPort(BaseModel, ABC):
    """Abstract port defining filesystem blocking behavior.

    This port defines the contract for filesystem access control during test
    execution. Implementations (adapters) provide the actual blocking
    mechanism.

    Following hexagonal architecture:
    - This port defines WHAT operations are available
    - Adapters define HOW they are implemented
    - Production adapter: FilesystemPatchingBlocker (patches builtins.open, pathlib, os)
    - Test adapter: FakeFilesystemBlocker (records attempts, no real patching)

    The blocker follows a state machine pattern:
    - INACTIVE: Not intercepting filesystem operations (initial state)
    - ACTIVE: Intercepting and potentially blocking filesystem operations

    State transitions are guarded by icontract preconditions/postconditions,
    following the same pattern as TestTimer and NetworkBlockerPort. The base
    class provides public methods with contracts that delegate to abstract
    _do_* methods.

    Attributes:
        state: Current blocker state (INACTIVE or ACTIVE).

    Example:
        >>> class FakeFilesystemBlocker(FilesystemBlockerPort):
        ...     def _do_activate(self, test_size, enforcement_mode, allowed_paths):
        ...         # Record parameters for assertions
        ...         pass
        ...
        >>> blocker = FakeFilesystemBlocker()
        >>> assert blocker.state == BlockerState.INACTIVE
        >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())
        >>> assert blocker.state == BlockerState.ACTIVE

    See Also:
        - TestTimer: Similar state machine pattern in types.py
        - NetworkBlockerPort: Similar pattern in ports/network.py
        - FilesystemPatchingBlocker: Production adapter (to be implemented)
        - FakeFilesystemBlocker: Test adapter (to be implemented)

    """

    state: BlockerState = BlockerState.INACTIVE

    @require(lambda self: self.state == BlockerState.INACTIVE, 'Blocker must be INACTIVE to activate')
    @ensure(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE after activation')
    def activate(
        self,
        test_size: TestSize,
        enforcement_mode: EnforcementMode,
        allowed_paths: frozenset[Path],
    ) -> None:
        """Activate filesystem blocking for a test.

        Transitions the blocker from INACTIVE to ACTIVE state. Once active,
        the blocker will intercept filesystem access attempts and handle
        them according to the enforcement mode and test size restrictions.

        Args:
            test_size: The size category of the current test. Determines
                what filesystem access is allowed:
                - SMALL: Block all filesystem access (except allowed paths)
                - MEDIUM/LARGE/XLARGE: Allow all filesystem access
            enforcement_mode: How to handle violations:
                - STRICT: Raise HermeticityViolationError
                - WARN: Emit warning, allow operation
                - OFF: No enforcement
            allowed_paths: Paths that are always allowed (e.g., tmp_path).
                Tests can access these paths even when blocking is active.

        Raises:
            icontract.ViolationError: If blocker is not in INACTIVE state.

        Example:
            >>> allowed = frozenset([Path('/tmp/pytest-of-user')])
            >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, allowed)
            >>> # Now any file operations will be intercepted

        """
        self._do_activate(test_size, enforcement_mode, allowed_paths)
        self.state = BlockerState.ACTIVE

    @abstractmethod
    def _do_activate(
        self,
        test_size: TestSize,
        enforcement_mode: EnforcementMode,
        allowed_paths: frozenset[Path],
    ) -> None:
        """Perform adapter-specific activation logic.

        Subclasses implement this to perform adapter-specific activation.
        State transition is handled by the base class.

        Args:
            test_size: The size category of the current test.
            enforcement_mode: How to handle violations.
            allowed_paths: Paths that are always allowed.

        """

    @require(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE to deactivate')
    @ensure(lambda self: self.state == BlockerState.INACTIVE, 'Blocker must be INACTIVE after deactivation')
    def deactivate(self) -> None:
        """Deactivate filesystem blocking, restoring normal behavior.

        Transitions the blocker from ACTIVE to INACTIVE state. This should
        be called in a finally block to ensure filesystem operations are
        restored even if the test fails.

        Raises:
            icontract.ViolationError: If blocker is not in ACTIVE state.

        Example:
            >>> try:
            ...     blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())
            ...     # test runs
            ... finally:
            ...     blocker.deactivate()  # Always restore filesystem access

        """
        self._do_deactivate()
        self.state = BlockerState.INACTIVE

    @abstractmethod
    def _do_deactivate(self) -> None:
        """Perform adapter-specific deactivation logic.

        Subclasses implement this to perform adapter-specific deactivation.
        State transition is handled by the base class.

        """

    @require(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE to check access')
    def check_access_allowed(self, path: Path, operation: FilesystemOperation) -> bool:
        """Check if a filesystem operation on path is allowed.

        This method is called by the filesystem interception mechanism to
        determine whether an operation should be permitted.

        The decision depends on:
        - The test size (set during activate())
        - The path being accessed
        - Whether the path is in the allowed set

        Args:
            path: The target path (should be resolved to absolute).
            operation: The type of operation (READ, WRITE, DELETE, etc.).

        Returns:
            True if the operation is allowed, False if it should be blocked.

        Raises:
            icontract.ViolationError: If blocker is not in ACTIVE state.

        Example:
            >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())
            >>> blocker.check_access_allowed(Path('/etc/passwd'), FilesystemOperation.READ)
            False  # Small tests cannot access filesystem (no allowed paths)
            >>> allowed = frozenset([Path('/tmp').resolve()])
            >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, allowed)
            >>> blocker.check_access_allowed(Path('/tmp/test.txt'), FilesystemOperation.WRITE)
            True   # /tmp is in allowed paths

        """
        return self._do_check_access_allowed(path, operation)

    @abstractmethod
    def _do_check_access_allowed(self, path: Path, operation: FilesystemOperation) -> bool:
        """Determine if a filesystem operation on path is allowed.

        Subclasses implement this to determine if an operation is allowed.

        Args:
            path: The target path (resolved to absolute).
            operation: The type of operation.

        Returns:
            True if the operation is allowed, False if it should be blocked.

        """

    @require(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE to handle violations')
    def on_violation(
        self,
        path: Path,
        operation: FilesystemOperation,
        test_nodeid: str,
    ) -> None:
        """Handle a filesystem access violation.

        Called when a test attempts a filesystem operation that is not allowed
        according to its size category restrictions.

        The response depends on the enforcement mode (set during activate()):
        - STRICT: Raise HermeticityViolationError
        - WARN: Emit warning via pytest's warning system
        - OFF: Do nothing (should not be called in OFF mode)

        Args:
            path: The attempted path.
            operation: The attempted operation type.
            test_nodeid: The pytest node ID of the violating test.

        Raises:
            HermeticityViolationError: If enforcement mode is STRICT.
            icontract.ViolationError: If blocker is not in ACTIVE state.

        Example:
            >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())
            >>> blocker.on_violation(Path('/etc/passwd'), FilesystemOperation.READ, 'test_mod::test_fn')
            HermeticityViolationError: Small tests cannot access the filesystem...

        """
        self._do_on_violation(path, operation, test_nodeid)

    @abstractmethod
    def _do_on_violation(
        self,
        path: Path,
        operation: FilesystemOperation,
        test_nodeid: str,
    ) -> None:
        """Handle violations according to enforcement mode.

        Subclasses implement this to handle violations according to enforcement mode.

        Args:
            path: The attempted path.
            operation: The attempted operation type.
            test_nodeid: The pytest node ID of the violating test.

        """

    def reset(self) -> None:
        """Reset blocker to initial INACTIVE state.

        This is a convenience method for cleanup and testing. Unlike
        deactivate(), this does not require the blocker to be in ACTIVE
        state - it unconditionally resets to INACTIVE.

        Subclasses should override to perform any additional cleanup
        (e.g., restoring patched filesystem operations).

        Example:
            >>> blocker.reset()  # Safe to call regardless of current state
            >>> assert blocker.state == BlockerState.INACTIVE

        """
        self.state = BlockerState.INACTIVE
