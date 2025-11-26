"""Fake network blocker adapter for testing.

This module provides a test double for the NetworkBlockerPort that allows
controllable simulation of network blocking without actual socket patching.
This enables fast, deterministic unit tests.

The FakeNetworkBlocker follows hexagonal architecture principles:
- Implements the NetworkBlockerPort interface (port)
- Provides controllable behavior for testing
- Records connection attempts and method invocations
- No actual socket manipulation

Example:
    >>> blocker = FakeNetworkBlocker()
    >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
    >>> blocker.check_connection_allowed('api.example.com', 443)
    False
    >>> assert len(blocker.connection_attempts) == 1

See Also:
    - NetworkBlockerPort: The abstract interface in ports/network.py
    - SocketPatchingNetworkBlocker: Production adapter in adapters/network.py
    - FakeTimer: Similar test double pattern for timing

"""

from __future__ import annotations

from pydantic import Field

from pytest_test_categories.exceptions import NetworkAccessViolationError
from pytest_test_categories.ports.network import (
    ConnectionAttempt,
    EnforcementMode,
    NetworkBlockerPort,
)
from pytest_test_categories.types import TestSize

# Localhost identifiers for medium test allowlist
LOCALHOST_HOSTS = frozenset(
    {
        'localhost',
        '127.0.0.1',
        '::1',
        '0:0:0:0:0:0:0:1',
    }
)


def is_localhost(host: str) -> bool:
    """Check if a host is a localhost address.

    Args:
        host: The hostname or IP address to check.

    Returns:
        True if the host is a localhost address, False otherwise.

    """
    # Case-insensitive check for 'localhost'
    if host.lower() == 'localhost':
        return True

    # Check for 127.x.x.x range
    if host.startswith('127.'):
        return True

    # Check other localhost representations
    return host in LOCALHOST_HOSTS


class FakeNetworkBlocker(NetworkBlockerPort):
    """Test double for network blocking that records attempts without real socket patching.

    This adapter is designed for unit testing code that uses network blocking.
    It tracks all method calls and connection attempts for verification in tests.

    Attributes:
        state: Current blocker state (inherited from NetworkBlockerPort).
        current_test_size: The test size set during activation.
        current_enforcement_mode: The enforcement mode set during activation.
        connection_attempts: List of recorded connection attempts.
        warnings: List of warning messages generated in WARN mode.
        activate_count: Number of times activate() was called.
        deactivate_count: Number of times deactivate() was called.
        check_count: Number of times check_connection_allowed() was called.

    Example:
        >>> blocker = FakeNetworkBlocker()
        >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        >>> assert blocker.check_connection_allowed('localhost', 80) is False
        >>> assert blocker.check_count == 1

    """

    current_test_size: TestSize | None = Field(default=None, description='Test size')
    current_enforcement_mode: EnforcementMode | None = Field(default=None, description='Enforcement mode')
    connection_attempts: list[ConnectionAttempt] = Field(default_factory=list, description='Attempts')
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

    def _do_check_connection_allowed(self, host: str, port: int) -> bool:
        """Check if connection is allowed and record the attempt.

        Returns whether connection would be allowed based on the test size:
        - SMALL: Block all network access
        - MEDIUM: Allow localhost only
        - LARGE/XLARGE: Allow all connections

        Args:
            host: The target hostname or IP address.
            port: The target port number.

        Returns:
            True if the connection is allowed, False if it should be blocked.

        """
        self.check_count += 1

        # Determine if connection is allowed based on test size
        allowed = self._is_connection_allowed(host)

        # Record the attempt
        self.connection_attempts.append(
            ConnectionAttempt(
                host=host,
                port=port,
                test_nodeid='',  # Not tracked in fake, would come from pytest context
                allowed=allowed,
            )
        )

        return allowed

    def _is_connection_allowed(self, host: str) -> bool:
        """Determine if a connection is allowed based on test size.

        Args:
            host: The target hostname or IP address.

        Returns:
            True if allowed, False otherwise.

        """
        if self.current_test_size == TestSize.SMALL:
            # Small tests cannot access any network
            return False

        if self.current_test_size == TestSize.MEDIUM:
            # Medium tests can only access localhost
            return is_localhost(host)

        # Large and XLarge tests can access any network
        return True

    def _do_on_violation(self, host: str, port: int, test_nodeid: str) -> None:
        """Handle a network access violation based on enforcement mode.

        Behavior:
        - STRICT: Raise NetworkAccessViolationError
        - WARN: Record warning message
        - OFF: Do nothing

        Args:
            host: The attempted destination host.
            port: The attempted destination port.
            test_nodeid: The pytest node ID of the violating test.

        Raises:
            NetworkAccessViolationError: If enforcement mode is STRICT.

        """
        if self.current_enforcement_mode == EnforcementMode.STRICT:
            # test_size is guaranteed to be set when ACTIVE (checked by icontract)
            raise NetworkAccessViolationError(
                test_size=self.current_test_size,  # type: ignore[arg-type]
                test_nodeid=test_nodeid,
                host=host,
                port=port,
            )

        if self.current_enforcement_mode == EnforcementMode.WARN:
            warning_msg = f'Network access violation: {host}:{port} in test {test_nodeid}'
            self.warnings.append(warning_msg)

        # OFF mode: do nothing

    def reset(self) -> None:
        """Reset blocker to initial state, clearing all recorded data.

        This is safe to call regardless of current state.

        """
        super().reset()
        self.current_test_size = None
        self.current_enforcement_mode = None
        self.connection_attempts = []
        self.warnings = []
        # Note: We don't reset counters as they're useful for verification
