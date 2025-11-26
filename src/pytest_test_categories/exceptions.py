"""Exception classes for pytest-test-categories.

This module defines the exception hierarchy for resource isolation violations.
These exceptions are raised when tests violate their size category's
resource restrictions.

Exception Hierarchy:
    HermeticityViolationError (base)
    +-- NetworkAccessViolationError
    +-- FilesystemAccessViolationError (future)
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
    - TimingViolationError: Existing exception in types.py (similar pattern)

"""

from __future__ import annotations

from pytest_test_categories.types import TestSize


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
        ...     def __init__(self, test_size, test_nodeid, custom_detail):
        ...         super().__init__(
        ...             test_size=test_size,
        ...             test_nodeid=test_nodeid,
        ...             violation_type='Custom resource access',
        ...             details=f'Accessed: {custom_detail}',
        ...             remediation=['Fix suggestion 1', 'Fix suggestion 2']
        ...         )

    """

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

        lines.append('Documentation: https://pytest-test-categories.readthedocs.io/resource-isolation/')
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
