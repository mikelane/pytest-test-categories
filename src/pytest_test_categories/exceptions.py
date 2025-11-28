"""Exception classes for pytest-test-categories.

This module defines the exception hierarchy for resource isolation violations.
These exceptions are raised when tests violate their size category's
resource restrictions.

Exception Hierarchy:
    HermeticityViolationError (base)
    +-- NetworkAccessViolationError
    +-- FilesystemAccessViolationError
    +-- SubprocessViolationError (future)
    +-- SleepViolationError (future)

The base HermeticityViolationError provides common functionality:
- Test context (size, nodeid)
- Remediation guidance
- Formatted error messages

Example:
    >>> raise NetworkAccessViolationError(
    ...     test_size=TestSize.SMALL,
    ...     test_nodeid='test_module.py::test_function',
    ...     host='api.example.com',
    ...     port=443
    ... )
    NetworkAccessViolationError: Small tests cannot access the network.
    Test attempted to connect to: api.example.com:443

See Also:
    - ADR-001: docs/architecture/adr-001-network-isolation.md
    - ADR-002: docs/architecture/adr-002-filesystem-isolation.md
    - TimingViolationError: Existing exception in types.py (similar pattern)

"""

from __future__ import annotations

__all__ = [
    'FilesystemAccessViolationError',
    'HermeticityViolationError',
    'NetworkAccessViolationError',
]

from typing import TYPE_CHECKING

from pytest_test_categories.types import TestSize

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_test_categories.ports.filesystem import FilesystemOperation as FsOp


class HermeticityViolationError(Exception):
    """Base exception for test hermeticity violations.

    Raised when a test violates its size category's resource restrictions.
    This is the base class for all resource violation exceptions.

    Subclasses should provide:
    - Specific violation details (host, path, command, etc.)
    - Appropriate remediation suggestions
    - Formatted error message

    Attributes:
        test_size: The test's size category.
        test_nodeid: The pytest node ID of the violating test.
        violation_type: A short description of the violation type.
        details: Specific details about the violation.
        remediation: List of suggestions for fixing the violation.

    Example:
        >>> class CustomViolation(HermeticityViolationError):
        ...     _adr_reference = 'docs/architecture/adr-003-custom-isolation.md'
        ...     def __init__(self, test_size, test_nodeid, custom_detail):
        ...         super().__init__(
        ...             test_size=test_size,
        ...             test_nodeid=test_nodeid,
        ...             violation_type='Custom resource access',
        ...             details=f'Accessed: {custom_detail}',
        ...             remediation=['Fix suggestion 1', 'Fix suggestion 2']
        ...         )

    """

    _adr_reference: str = 'docs/architecture/adr-001-network-isolation.md'

    def __init__(
        self,
        test_size: TestSize,
        test_nodeid: str,
        violation_type: str,
        details: str,
        remediation: list[str] | None = None,
    ) -> None:
        """Initialize a hermeticity violation error.

        Args:
            test_size: The test's size category.
            test_nodeid: The pytest node ID of the violating test.
            violation_type: A short description of the violation type.
            details: Specific details about the violation.
            remediation: List of suggestions for fixing the violation.

        """
        self.test_size = test_size
        self.test_nodeid = test_nodeid
        self.violation_type = violation_type
        self.details = details
        self.remediation = remediation or []

        message = self._format_message()
        super().__init__(message)

    def _format_message(self) -> str:
        """Format the error message with full context.

        Returns:
            A formatted multi-line error message.

        """
        lines = [
            '',
            '=' * 60,
            'HermeticityViolationError',
            '=' * 60,
            f'Test: {self.test_nodeid}',
            f'Category: {self.test_size.name}',
            f'Violation: {self.violation_type}',
            '',
            'Details:',
            f'  {self.details}',
            '',
        ]

        if self.remediation:
            lines.append(f'{self.test_size.name.capitalize()} tests have restricted resource access. Options:')
            for i, suggestion in enumerate(self.remediation, 1):
                lines.append(f'  {i}. {suggestion}')
            lines.append('')

        lines.append(f'Documentation: See {self._adr_reference}')
        lines.append('=' * 60)

        return '\n'.join(lines)


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

    Example:
        >>> raise NetworkAccessViolationError(
        ...     test_size=TestSize.SMALL,
        ...     test_nodeid='tests/test_api.py::test_fetch_user',
        ...     host='api.example.com',
        ...     port=443
        ... )

    The error message includes:
    - Test identification (nodeid, size category)
    - Connection details (host:port)
    - Remediation suggestions (mocking, DI, size change)

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

        super().__init__(
            test_size=test_size,
            test_nodeid=test_nodeid,
            violation_type='Network access attempted',
            details=f'Attempted connection to: {host}:{port}',
            remediation=remediation,
        )

    @staticmethod
    def _get_remediation(test_size: TestSize) -> list[str]:
        """Get remediation suggestions based on test size.

        Args:
            test_size: The test's size category.

        Returns:
            List of remediation suggestions.

        """
        if test_size == TestSize.SMALL:
            return [
                'Mock the network call using responses, httpretty, or respx',
                'Use dependency injection to provide a fake HTTP client',
                'Change test category to @pytest.mark.medium (if network is required)',
            ]
        if test_size == TestSize.MEDIUM:
            return [
                'Use localhost for the service (e.g., run a local mock server)',
                'Mock the external service call',
                'Change test category to @pytest.mark.large (if external network is required)',
            ]
        return []  # Large/XLarge tests have no network restrictions


class FilesystemAccessViolationError(HermeticityViolationError):
    """Raised when a test makes an unauthorized filesystem access.

    This exception is raised when a test attempts filesystem access
    that violates its size category's restrictions:
    - Small tests: No filesystem access (except allowed paths)
    - Medium/Large/XLarge: All filesystem access allowed

    Attributes:
        path: The attempted path.
        operation: The type of operation attempted.

    Example:
        >>> raise FilesystemAccessViolationError(
        ...     test_size=TestSize.SMALL,
        ...     test_nodeid='tests/test_file.py::test_save',
        ...     path=Path('/etc/passwd'),
        ...     operation=FilesystemOperation.READ
        ... )

    The error message includes:
    - Test identification (nodeid, size category)
    - Path and operation details
    - Remediation suggestions (tmp_path, mocking, size change)

    """

    _adr_reference: str = 'docs/architecture/adr-002-filesystem-isolation.md'

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
        # Import locally to avoid circular dependency

        self.path = path
        self.operation: FsOp = operation

        remediation = self._get_remediation(test_size, operation)

        super().__init__(
            test_size=test_size,
            test_nodeid=test_nodeid,
            violation_type='Filesystem access attempted',
            details=f'Attempted {operation.value} on: {path}',
            remediation=remediation,
        )

    @staticmethod
    def _get_remediation(test_size: TestSize, operation: FsOp) -> list[str]:
        """Get remediation suggestions based on test size and operation.

        Args:
            test_size: The test's size category.
            operation: The type of operation attempted.

        Returns:
            List of remediation suggestions.

        """
        # Import locally to avoid circular dependency
        from pytest_test_categories.ports.filesystem import FilesystemOperation as FsOp  # noqa: PLC0415

        if test_size == TestSize.SMALL:
            suggestions = [
                "Use pytest's tmp_path fixture for temporary files",
                'Mock file operations using pytest-mock (mocker fixture) or pyfakefs',
                'Use io.StringIO or io.BytesIO for in-memory file-like objects',
            ]
            if operation in (FsOp.READ, FsOp.STAT):
                suggestions.append('Embed test data as Python constants or use importlib.resources')
            suggestions.append('Change test category to @pytest.mark.medium (if filesystem access is required)')
            return suggestions
        return []  # Medium/Large/XLarge tests have no filesystem restrictions
