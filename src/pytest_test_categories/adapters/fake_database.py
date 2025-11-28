"""Fake database blocker adapter for testing.

This module provides a test double for the DatabaseBlockerPort that allows
controllable simulation of database blocking without actual patching.
This enables fast, deterministic unit tests.

The FakeDatabaseBlocker follows hexagonal architecture principles:
- Implements the DatabaseBlockerPort interface (port)
- Provides controllable behavior for testing
- Records connection attempts and method invocations
- No actual database patching

Example:
    >>> blocker = FakeDatabaseBlocker()
    >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
    >>> blocker.check_connection_allowed('sqlite3', ':memory:')
    False
    >>> assert len(blocker.connection_attempts) == 1

See Also:
    - DatabaseBlockerPort: The abstract interface in ports/database.py
    - DatabasePatchingBlocker: Production adapter in adapters/database.py
    - FakeNetworkBlocker: Similar test double pattern for network blocking

"""

from __future__ import annotations

from pydantic import Field

from pytest_test_categories.exceptions import DatabaseViolationError
from pytest_test_categories.ports.database import (
    DatabaseAccessAttempt,
    DatabaseBlockerPort,
)
from pytest_test_categories.ports.network import EnforcementMode
from pytest_test_categories.types import TestSize


class FakeDatabaseBlocker(DatabaseBlockerPort):
    """Test double for database blocking that records attempts without real patching.

    This adapter is designed for unit testing code that uses database blocking.
    It tracks all method calls and connection attempts for verification in tests.

    Attributes:
        state: Current blocker state (inherited from DatabaseBlockerPort).
        current_test_size: The test size set during activation.
        current_enforcement_mode: The enforcement mode set during activation.
        connection_attempts: List of recorded database connection attempts.
        warnings: List of warning messages generated in WARN mode.
        activate_count: Number of times activate() was called.
        deactivate_count: Number of times deactivate() was called.
        check_count: Number of times check_connection_allowed() was called.

    Example:
        >>> blocker = FakeDatabaseBlocker()
        >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        >>> assert blocker.check_connection_allowed('sqlite3', ':memory:') is False
        >>> assert blocker.check_count == 1

    """

    current_test_size: TestSize | None = Field(default=None, description='Test size')
    current_enforcement_mode: EnforcementMode | None = Field(default=None, description='Enforcement mode')
    connection_attempts: list[DatabaseAccessAttempt] = Field(default_factory=list, description='Connection attempts')
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

    def _do_check_connection_allowed(self, library: str, connection_string: str) -> bool:
        """Check if database connection is allowed and record the attempt.

        Returns whether connection would be allowed based on the test size:
        - SMALL: Block all database connections
        - MEDIUM/LARGE/XLARGE: Allow all database connections

        Args:
            library: The database library name.
            connection_string: The connection string or database path.

        Returns:
            True if the connection is allowed, False if it should be blocked.

        """
        self.check_count += 1

        allowed = self._is_connection_allowed()

        self.connection_attempts.append(
            DatabaseAccessAttempt(
                library=library,
                connection_string=connection_string,
                test_nodeid='',
                allowed=allowed,
            )
        )

        return allowed

    def _is_connection_allowed(self) -> bool:
        """Determine if database connection is allowed based on test size.

        Returns:
            True if allowed, False otherwise.

        """
        return self.current_test_size != TestSize.SMALL

    def _do_on_violation(
        self,
        library: str,
        connection_string: str,
        test_nodeid: str,
    ) -> None:
        """Handle a database access violation based on enforcement mode.

        Behavior:
        - STRICT: Raise DatabaseViolationError
        - WARN: Record warning message
        - OFF: Do nothing

        Args:
            library: The database library name.
            connection_string: The connection string or database path.
            test_nodeid: The pytest node ID of the violating test.

        Raises:
            DatabaseViolationError: If enforcement mode is STRICT.

        """
        if self.current_enforcement_mode == EnforcementMode.STRICT:
            raise DatabaseViolationError(
                test_size=self.current_test_size,  # type: ignore[arg-type]
                test_nodeid=test_nodeid,
                library=library,
                connection_string=connection_string,
            )

        if self.current_enforcement_mode == EnforcementMode.WARN:
            warning_msg = f'Database access: {library} connection to {connection_string} in {test_nodeid}'
            self.warnings.append(warning_msg)

    def reset(self) -> None:
        """Reset blocker to initial state, clearing all recorded data.

        This is safe to call regardless of current state.

        """
        super().reset()
        self.current_test_size = None
        self.current_enforcement_mode = None
        self.connection_attempts = []
        self.warnings = []
