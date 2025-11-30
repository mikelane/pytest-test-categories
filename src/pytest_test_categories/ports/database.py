"""Database blocking port interface for hermetic test enforcement.

This module defines the abstract interface (port) for database access control
during test execution. Following hexagonal architecture, this port defines
WHAT operations are available, while adapters define HOW they are implemented.

The pattern enables:
- Production adapter (`DatabasePatchingBlocker`): Patches database connection
  functions (sqlite3.connect, and optionally psycopg2, pymysql, etc.) to
  intercept real database access
- Test adapter (`FakeDatabaseBlocker`): Controllable test double that records
  connection attempts without actual patching

Database connections are blocked in small tests because:
- In-memory databases (:memory:) still require I/O operations for the SQLite engine
- Database connections introduce external state dependencies
- Even local databases can cause non-deterministic behavior
- Small tests should run entirely in-process without any I/O

Example:
    Production usage (via plugin hooks):
    >>> blocker = DatabasePatchingBlocker()
    >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
    >>> # Test runs, any database connection raises DatabaseViolationError
    >>> blocker.deactivate()

    Test usage:
    >>> blocker = FakeDatabaseBlocker()
    >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
    >>> assert blocker.is_active
    >>> blocker.check_connection_allowed('sqlite3', ':memory:')
    >>> assert len(blocker.connection_attempts) == 1

See Also:
    - NetworkBlockerPort: Similar pattern in ports/network.py
    - FilesystemBlockerPort: Similar pattern in ports/filesystem.py
    - ProcessBlockerPort: Similar pattern in ports/process.py

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
from pydantic import (
    BaseModel,
    Field,
)

from pytest_test_categories.ports.network import (
    BlockerState,
    EnforcementMode,
    ViolationCallback,
)

if TYPE_CHECKING:
    from pytest_test_categories.types import TestSize


class DatabaseAccessAttempt(BaseModel, frozen=True):
    """Immutable record of a database connection attempt.

    Used for tracking and reporting connection attempts during test execution.
    This is useful for diagnostics and for test adapters that need to record
    what database connections were attempted.

    Attributes:
        library: The database library name (e.g., 'sqlite3', 'psycopg2').
        connection_string: The connection string or database path.
        test_nodeid: The pytest node ID of the test that made the attempt.
        allowed: Whether the connection was permitted.

    Example:
        >>> attempt = DatabaseAccessAttempt(
        ...     library='sqlite3',
        ...     connection_string=':memory:',
        ...     test_nodeid='test_module.py::test_function',
        ...     allowed=False
        ... )

    """

    library: str
    connection_string: str
    test_nodeid: str
    allowed: bool


class DatabaseBlockerPort(BaseModel, ABC):
    """Abstract port defining database blocking behavior.

    This port defines the contract for database access control during test
    execution. Implementations (adapters) provide the actual blocking
    mechanism.

    Following hexagonal architecture:
    - This port defines WHAT operations are available
    - Adapters define HOW they are implemented
    - Production adapter: DatabasePatchingBlocker (patches database connect functions)
    - Test adapter: FakeDatabaseBlocker (records attempts, no real patching)

    The blocker follows a state machine pattern:
    - INACTIVE: Not intercepting connections (initial state)
    - ACTIVE: Intercepting and potentially blocking connections

    State transitions are guarded by icontract preconditions/postconditions,
    following the same pattern as TestTimer, NetworkBlockerPort, and other ports.

    Attributes:
        state: Current blocker state (INACTIVE or ACTIVE).

    Example:
        >>> class FakeDatabaseBlocker(DatabaseBlockerPort):
        ...     def _do_activate(self, test_size, enforcement_mode):
        ...         # Record parameters for assertions
        ...         pass
        ...
        >>> blocker = FakeDatabaseBlocker()
        >>> assert blocker.state == BlockerState.INACTIVE
        >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        >>> assert blocker.state == BlockerState.ACTIVE

    See Also:
        - TestTimer: Similar state machine pattern in types.py
        - NetworkBlockerPort: Similar pattern in ports/network.py
        - DatabasePatchingBlocker: Production adapter
        - FakeDatabaseBlocker: Test adapter

    """

    model_config = {'arbitrary_types_allowed': True}

    state: BlockerState = BlockerState.INACTIVE
    violation_callback: ViolationCallback | None = Field(default=None, description='Callback for violation tracking')

    @require(lambda self: self.state == BlockerState.INACTIVE, 'Blocker must be INACTIVE to activate')
    @ensure(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE after activation')
    def activate(self, test_size: TestSize, enforcement_mode: EnforcementMode) -> None:
        """Activate database blocking for a test.

        Transitions the blocker from INACTIVE to ACTIVE state. Once active,
        the blocker will intercept database connection attempts and handle
        them according to the enforcement mode and test size restrictions.

        Args:
            test_size: The size category of the current test. Determines
                what connections are allowed:
                - SMALL: Block all database connections (including :memory:)
                - MEDIUM: Allow all database connections
                - LARGE/XLARGE: Allow all database connections
            enforcement_mode: How to handle violations:
                - STRICT: Raise DatabaseViolationError
                - WARN: Emit warning, allow connection
                - OFF: No enforcement

        Raises:
            icontract.ViolationError: If blocker is not in INACTIVE state.

        Example:
            >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
            >>> # Now any database connect() call will be intercepted

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
        """Deactivate database blocking, restoring normal behavior.

        Transitions the blocker from ACTIVE to INACTIVE state. This should
        be called in a finally block to ensure database functions are restored
        even if the test fails.

        Raises:
            icontract.ViolationError: If blocker is not in ACTIVE state.

        Example:
            >>> try:
            ...     blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
            ...     # test runs
            ... finally:
            ...     blocker.deactivate()  # Always restore database functions

        """
        self._do_deactivate()
        self.state = BlockerState.INACTIVE

    @abstractmethod
    def _do_deactivate(self) -> None:
        """Perform adapter-specific deactivation logic.

        Subclasses implement this to perform adapter-specific deactivation.
        State transition is handled by the base class.

        """

    @require(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE to check connections')
    def check_connection_allowed(self, library: str, connection_string: str) -> bool:
        """Check if a database connection is allowed.

        This method is called by the database interception mechanism to
        determine whether a connection should be permitted.

        The decision depends on:
        - The test size (set during activate())
        - The database library being used

        Args:
            library: The database library name (e.g., 'sqlite3', 'psycopg2').
            connection_string: The connection string or database path.

        Returns:
            True if the connection is allowed, False if it should be blocked.

        Raises:
            icontract.ViolationError: If blocker is not in ACTIVE state.

        Example:
            >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
            >>> blocker.check_connection_allowed('sqlite3', ':memory:')
            False  # Small tests cannot access any database
            >>> blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)
            >>> blocker.check_connection_allowed('sqlite3', ':memory:')
            True   # Medium tests can access databases

        """
        return self._do_check_connection_allowed(library, connection_string)

    @abstractmethod
    def _do_check_connection_allowed(self, library: str, connection_string: str) -> bool:
        """Determine if a database connection is allowed.

        Subclasses implement this to determine if a connection is allowed.

        Args:
            library: The database library name.
            connection_string: The connection string or database path.

        Returns:
            True if the connection is allowed, False if it should be blocked.

        """

    @require(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE to handle violations')
    def on_violation(self, library: str, connection_string: str, test_nodeid: str) -> None:
        """Handle a database access violation.

        Called when a test attempts a database connection that is not allowed
        according to its size category restrictions.

        The response depends on the enforcement mode (set during activate()):
        - STRICT: Raise DatabaseViolationError
        - WARN: Emit warning via pytest's warning system
        - OFF: Do nothing (should not be called in OFF mode)

        If a violation_callback is set, it will be called to record the
        violation for JSON report tracking.

        Args:
            library: The database library name.
            connection_string: The connection string or database path.
            test_nodeid: The pytest node ID of the violating test.

        Raises:
            DatabaseViolationError: If enforcement mode is STRICT.
            icontract.ViolationError: If blocker is not in ACTIVE state.

        Example:
            >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
            >>> blocker.on_violation('sqlite3', ':memory:', 'test_mod::test_fn')
            DatabaseViolationError: Small tests cannot access databases...

        """
        if self.violation_callback is not None:
            from pytest_test_categories.violations import ViolationType  # noqa: PLC0415

            self.violation_callback(test_nodeid, ViolationType.DATABASE)
        self._do_on_violation(library, connection_string, test_nodeid)

    @abstractmethod
    def _do_on_violation(self, library: str, connection_string: str, test_nodeid: str) -> None:
        """Handle violations according to enforcement mode.

        Subclasses implement this to handle violations according to enforcement mode.

        Args:
            library: The database library name.
            connection_string: The connection string or database path.
            test_nodeid: The pytest node ID of the violating test.

        """

    def reset(self) -> None:
        """Reset blocker to initial INACTIVE state.

        This is a convenience method for cleanup and testing. Unlike
        deactivate(), this does not require the blocker to be in ACTIVE
        state - it unconditionally resets to INACTIVE.

        Subclasses should override to perform any additional cleanup
        (e.g., restoring patched database functions).

        Example:
            >>> blocker.reset()  # Safe to call regardless of current state
            >>> assert blocker.state == BlockerState.INACTIVE

        """
        self.state = BlockerState.INACTIVE
