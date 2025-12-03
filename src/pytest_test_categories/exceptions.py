"""Exception classes for pytest-test-categories.

This module defines the exception hierarchy for resource isolation violations.
These exceptions are raised when tests violate their size category's
resource restrictions.

Exception Hierarchy:
    HermeticityViolationError (base)
    +-- NetworkAccessViolationError
    +-- FilesystemAccessViolationError
    +-- SubprocessViolationError
    +-- DatabaseViolationError
    +-- SleepViolationError

All exceptions use the centralized error registry (errors.py) for:
- Consistent error codes (TC001-TC099)
- Standardized message format with "what happened", "why it matters", "how to fix"
- Documentation links for each error type

Example:
    >>> raise NetworkAccessViolationError(
    ...     test_size=TestSize.SMALL,
    ...     test_nodeid='test_module.py::test_function',
    ...     host='api.example.com',
    ...     port=443
    ... )
    [TC001] Network Access Violation
    Test: test_module.py::test_function
    Category: SMALL
    ...

See Also:
    - errors.py: Centralized error code registry
    - ADR-001: docs/architecture/adr-001-network-isolation.md
    - ADR-002: docs/architecture/adr-002-filesystem-isolation.md

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytest_test_categories.errors import (
    ERROR_CODES,
    format_error_message,
)
from pytest_test_categories.types import TestSize

__all__ = [
    'DatabaseViolationError',
    'FilesystemAccessViolationError',
    'HermeticityViolationError',
    'NetworkAccessViolationError',
    'SleepViolationError',
    'SubprocessViolationError',
]

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_test_categories.errors import ErrorCode
    from pytest_test_categories.ports.filesystem import FilesystemOperation as FsOp


class HermeticityViolationError(Exception):
    """Base exception for test hermeticity violations.

    Raised when a test violates its size category's resource restrictions.
    This is the base class for all resource violation exceptions.

    Subclasses should provide:
    - Specific violation details (host, path, command, etc.)
    - Appropriate remediation suggestions
    - Reference to the appropriate error code

    Attributes:
        test_size: The test's size category.
        test_nodeid: The pytest node ID of the violating test.
        error_code: The ErrorCode instance for this violation type.

    """

    def __init__(
        self,
        test_size: TestSize,
        test_nodeid: str,
        error_code: ErrorCode,
        what_happened: str,
        remediation: list[str],
    ) -> None:
        """Initialize a hermeticity violation error.

        Args:
            test_size: The test's size category.
            test_nodeid: The pytest node ID of the violating test.
            error_code: The ErrorCode instance for this violation type.
            what_happened: Description of the specific violation.
            remediation: List of suggestions for fixing the violation.

        """
        self.test_size = test_size
        self.test_nodeid = test_nodeid
        self.error_code = error_code
        self.what_happened = what_happened
        self.remediation = remediation

        message = format_error_message(
            error_code=error_code,
            what_happened=what_happened,
            remediation=remediation,
            test_nodeid=test_nodeid,
            test_size=test_size.name,
        )
        super().__init__(message)


class NetworkAccessViolationError(HermeticityViolationError):
    """Raised when a test makes an unauthorized network request.

    This exception is raised when a test attempts to make a network
    connection that violates its size category's restrictions:
    - Small tests: No network access allowed
    - Medium tests: Only localhost connections allowed
    - Large/XLarge tests: All network access allowed

    Attributes:
        host: The attempted destination host.
        port: The attempted destination port.

    """

    def __init__(
        self,
        test_size: TestSize,
        test_nodeid: str,
        host: str,
        port: int,
    ) -> None:
        """Initialize a network access violation error.

        Args:
            test_size: The test's size category.
            test_nodeid: The pytest node ID of the violating test.
            host: The attempted destination host.
            port: The attempted destination port.

        """
        self.host = host
        self.port = port

        remediation = self._get_remediation(test_size)
        what_happened = f'Attempted network connection to {host}:{port}'

        super().__init__(
            test_size=test_size,
            test_nodeid=test_nodeid,
            error_code=ERROR_CODES['network_violation'],
            what_happened=what_happened,
            remediation=remediation,
        )

    @staticmethod
    def _get_remediation(test_size: TestSize) -> list[str]:
        """Get remediation suggestions based on test size."""
        if test_size == TestSize.SMALL:
            return [
                'Mock the network call using responses, httpretty, or respx',
                'Use dependency injection to provide a fake HTTP client',
                'Change test category to @pytest.mark.medium (if network access is required)',
            ]
        if test_size == TestSize.MEDIUM:
            return [
                'Use localhost for the service (e.g., run a local mock server)',
                'Mock the external service call',
                'Change test category to @pytest.mark.large (if external network is required)',
            ]
        return []


class FilesystemAccessViolationError(HermeticityViolationError):
    """Raised when a test makes an unauthorized filesystem access.

    This exception is raised when a test attempts filesystem access
    that violates its size category's restrictions:
    - Small tests: No filesystem access (strict hermeticity - no escape hatches)
    - Medium/Large/XLarge: All filesystem access allowed

    Attributes:
        path: The attempted path.
        operation: The type of operation attempted.

    """

    def __init__(
        self,
        test_size: TestSize,
        test_nodeid: str,
        path: Path,
        operation: FsOp,
    ) -> None:
        """Initialize a filesystem access violation error.

        Args:
            test_size: The test's size category.
            test_nodeid: The pytest node ID of the violating test.
            path: The attempted path.
            operation: The type of operation attempted.

        """
        self.path = path
        self.operation: FsOp = operation

        remediation = self._get_remediation(test_size, operation)
        what_happened = f'Attempted {operation.value} on filesystem path: {path}'

        super().__init__(
            test_size=test_size,
            test_nodeid=test_nodeid,
            error_code=ERROR_CODES['filesystem_violation'],
            what_happened=what_happened,
            remediation=remediation,
        )

    @staticmethod
    def _get_remediation(test_size: TestSize, operation: FsOp) -> list[str]:
        """Get remediation suggestions based on test size and operation."""
        from pytest_test_categories.ports.filesystem import FilesystemOperation as FsOp  # noqa: PLC0415

        if test_size == TestSize.SMALL:
            suggestions = [
                'Use pyfakefs for comprehensive filesystem mocking (pip install pyfakefs)',
                'Use io.StringIO or io.BytesIO for in-memory file-like objects',
                'Mock file operations using pytest-mock (mocker.patch("builtins.open", ...))',
            ]
            if operation in (FsOp.READ, FsOp.STAT):
                suggestions.append('Embed test data as Python constants or use importlib.resources')
            suggestions.append('Change test category to @pytest.mark.medium (if filesystem access is required)')
            return suggestions
        return []


class SubprocessViolationError(HermeticityViolationError):
    """Raised when a test attempts to spawn a subprocess.

    This exception is raised when a test attempts to spawn a subprocess
    that violates its size category's restrictions:
    - Small tests: No subprocess spawning allowed
    - Medium/Large/XLarge: All subprocess spawning allowed

    Attributes:
        command: The command that was attempted.
        command_args: The arguments passed to the command.
        method: The method used to spawn (e.g., 'subprocess.run').

    """

    def __init__(
        self,
        test_size: TestSize,
        test_nodeid: str,
        command: str,
        command_args: tuple[str, ...],
        method: str,
    ) -> None:
        """Initialize a subprocess violation error.

        Args:
            test_size: The test's size category.
            test_nodeid: The pytest node ID of the violating test.
            command: The command that was attempted.
            command_args: The arguments passed to the command.
            method: The spawn method used (e.g., 'subprocess.run').

        """
        self.command = command
        self.command_args = command_args
        self.method = method

        args_str = ' '.join(command_args) if command_args else '(no args)'
        remediation = self._get_remediation(test_size, method)
        what_happened = f'Attempted {method}: {command} {args_str}'

        super().__init__(
            test_size=test_size,
            test_nodeid=test_nodeid,
            error_code=ERROR_CODES['subprocess_violation'],
            what_happened=what_happened,
            remediation=remediation,
        )

    @staticmethod
    def _get_remediation(test_size: TestSize, method: str) -> list[str]:
        """Get remediation suggestions based on test size and spawn method."""
        if test_size == TestSize.SMALL:
            suggestions = [
                f'Mock {method} using pytest-mock (mocker.patch)',
                'Use dependency injection to provide a fake command executor',
                'Test the logic that prepares subprocess arguments, not the spawn itself',
            ]
            if 'pytester' in method.lower() or method == 'subprocess.run':
                suggestions.append('Change test category to @pytest.mark.medium (pytester spawns subprocesses)')
            else:
                suggestions.append('Change test category to @pytest.mark.medium (if subprocess is required)')
            return suggestions
        return []


class DatabaseViolationError(HermeticityViolationError):
    """Raised when a test attempts to connect to a database.

    This exception is raised when a test attempts to make a database
    connection that violates its size category's restrictions:
    - Small tests: No database access allowed (including :memory:)
    - Medium/Large/XLarge: All database access allowed

    Attributes:
        library: The database library name (e.g., 'sqlite3', 'psycopg2').
        connection_string: The connection string or database path.

    """

    def __init__(
        self,
        test_size: TestSize,
        test_nodeid: str,
        library: str,
        connection_string: str,
    ) -> None:
        """Initialize a database violation error.

        Args:
            test_size: The test's size category.
            test_nodeid: The pytest node ID of the violating test.
            library: The database library name.
            connection_string: The connection string or database path.

        """
        self.library = library
        self.connection_string = connection_string

        remediation = self._get_remediation(test_size, library)
        what_happened = f'Attempted {library} database connection to: {connection_string}'

        super().__init__(
            test_size=test_size,
            test_nodeid=test_nodeid,
            error_code=ERROR_CODES['database_violation'],
            what_happened=what_happened,
            remediation=remediation,
        )

    @staticmethod
    def _get_remediation(test_size: TestSize, library: str) -> list[str]:
        """Get remediation suggestions based on test size and database library."""
        if test_size == TestSize.SMALL:
            suggestions = [
                f'Mock {library}.connect using pytest-mock (mocker.patch)',
                'Use dependency injection to provide a fake database/repository',
                'Use in-memory data structures (dict, list) for test data',
                'Test business logic separately from database operations',
            ]
            if library == 'sqlalchemy':
                suggestions.append('Consider using SQLAlchemy events or a fake engine')
            suggestions.append('Change test category to @pytest.mark.medium (if database access is required)')
            return suggestions
        return []


class SleepViolationError(HermeticityViolationError):
    """Raised when a test calls time.sleep() or similar blocking functions.

    This exception is raised when a test attempts to use sleep functions
    that violate its size category's restrictions:
    - Small tests: No sleep calls allowed (tests should be fast and deterministic)
    - Medium/Large/XLarge: All sleep calls allowed

    Attributes:
        function: The sleep function that was called (e.g., 'time.sleep').
        duration: The sleep duration in seconds.

    """

    def __init__(
        self,
        test_size: TestSize,
        test_nodeid: str,
        function: str,
        duration: float,
    ) -> None:
        """Initialize a sleep violation error.

        Args:
            test_size: The test's size category.
            test_nodeid: The pytest node ID of the violating test.
            function: The sleep function that was called.
            duration: The sleep duration in seconds.

        """
        self.function = function
        self.duration = duration

        remediation = self._get_remediation(test_size, function)
        what_happened = f'Called {function}({duration}) - attempted to sleep for {duration} seconds'

        super().__init__(
            test_size=test_size,
            test_nodeid=test_nodeid,
            error_code=ERROR_CODES['sleep_violation'],
            what_happened=what_happened,
            remediation=remediation,
        )

    @staticmethod
    def _get_remediation(test_size: TestSize, function: str) -> list[str]:
        """Get remediation suggestions based on test size and sleep function."""
        if test_size == TestSize.SMALL:
            suggestions = [
                'Use proper synchronization instead of sleep (e.g., threading.Event)',
                'Use condition-based waiting with polling and timeout',
                f'Mock {function} using pytest-mock (mocker.patch)',
                'Use a FakeTimer or controllable time abstraction',
            ]
            if 'asyncio' in function:
                suggestions.append('Use asyncio.wait_for() with proper conditions instead')
            suggestions.append('Change test category to @pytest.mark.medium (if timing is required)')
            return suggestions
        return []
