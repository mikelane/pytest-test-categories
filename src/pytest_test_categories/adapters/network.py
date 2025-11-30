"""Production network blocker adapter using socket patching.

This module provides the production implementation of NetworkBlockerPort that
actually intercepts network connections by patching the socket module.

The SocketPatchingNetworkBlocker follows hexagonal architecture principles:
- Implements the NetworkBlockerPort interface (port)
- Patches socket.socket to intercept connection attempts
- Raises NetworkAccessViolationError on unauthorized connections
- Restores original socket behavior on deactivation

Example:
    >>> blocker = SocketPatchingNetworkBlocker()
    >>> try:
    ...     blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
    ...     # Any socket.connect() call will now be intercepted
    ... finally:
    ...     blocker.deactivate()  # Restore original socket behavior

See Also:
    - NetworkBlockerPort: The abstract interface in ports/network.py
    - FakeNetworkBlocker: Test adapter in adapters/fake_network.py
    - WallTimer: Similar production adapter pattern for timing

"""

from __future__ import annotations

import socket

from pydantic import Field

from pytest_test_categories.adapters.fake_network import is_localhost
from pytest_test_categories.exceptions import NetworkAccessViolationError
from pytest_test_categories.ports.network import (
    EnforcementMode,
    NetworkBlockerPort,
)
from pytest_test_categories.types import TestSize


class SocketPatchingNetworkBlocker(NetworkBlockerPort):
    """Production adapter that patches socket.socket to block network access.

    This adapter intercepts socket connections by replacing socket.socket with
    a wrapper class that checks permissions before allowing connections.

    The patching is reversible - deactivate() restores the original socket class.

    Attributes:
        state: Current blocker state (inherited from NetworkBlockerPort).
        current_test_size: The test size set during activation.
        current_enforcement_mode: The enforcement mode set during activation.
        current_test_nodeid: The pytest node ID of the current test.

    Warning:
        This adapter modifies global state (socket.socket). Always use in a
        try/finally block or context manager to ensure cleanup.

    Example:
        >>> blocker = SocketPatchingNetworkBlocker()
        >>> try:
        ...     blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        ...     requests.get('https://example.com')  # Raises NetworkAccessViolationError
        ... finally:
        ...     blocker.deactivate()

    """

    current_test_size: TestSize | None = Field(default=None, description='Test size')
    current_enforcement_mode: EnforcementMode | None = Field(default=None, description='Enforcement mode')
    current_test_nodeid: str = Field(default='', description='Test node ID')

    def model_post_init(self, context: object, /) -> None:  # noqa: ARG002
        """Initialize post-Pydantic setup, storing reference to original socket."""
        # Store the original socket class as a private attribute (not a Pydantic field)
        # This ensures we can always restore it even if patched multiple times
        object.__setattr__(self, '_original_socket_class', None)

    def _do_activate(self, test_size: TestSize, enforcement_mode: EnforcementMode) -> None:
        """Install socket wrapper to intercept connection attempts.

        Installs a wrapper socket class that intercepts connect() calls
        and checks them against the test size restrictions.

        Args:
            test_size: The size category of the current test.
            enforcement_mode: How to handle violations.

        """
        self.current_test_size = test_size
        self.current_enforcement_mode = enforcement_mode

        # Store original socket class before patching
        object.__setattr__(self, '_original_socket_class', socket.socket)

        # Create and install the patched socket class
        socket.socket = self._create_patched_socket_class()  # type: ignore[misc,assignment]

    def _do_deactivate(self) -> None:
        """Restore the original socket.socket class.

        Restores the original socket.socket class that was saved during
        activation.

        """
        # Restore original socket class
        original = object.__getattribute__(self, '_original_socket_class')
        if original is not None:
            socket.socket = original  # type: ignore[misc]

    def _do_check_connection_allowed(self, host: str, port: int) -> bool:  # noqa: ARG002
        """Check if connection to host:port is allowed by test size rules.

        Rules applied:
        - SMALL: Block all network access
        - MEDIUM: Allow localhost only
        - LARGE/XLARGE: Allow all connections

        Args:
            host: The target hostname or IP address.
            port: The target port number.

        Returns:
            True if the connection is allowed, False if it should be blocked.

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
        - WARN: Log warning (future: integrate with pytest warning system)
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

        # WARN and OFF modes: future implementation will integrate with pytest
        # For now, these modes simply allow the connection to proceed

    def reset(self) -> None:
        """Reset blocker to initial state, restoring original socket.

        This is safe to call regardless of current state.

        """
        # Restore original socket if we have one stored
        original = object.__getattribute__(self, '_original_socket_class')
        if original is not None:
            socket.socket = original  # type: ignore[misc]
            object.__setattr__(self, '_original_socket_class', None)

        super().reset()
        self.current_test_size = None
        self.current_enforcement_mode = None
        self.current_test_nodeid = ''

    def _create_patched_socket_class(self) -> type:
        """Create a socket class that intercepts connections.

        Returns:
            A socket subclass that checks connections against blocker rules.

        """
        blocker = self
        original_socket = object.__getattribute__(self, '_original_socket_class')

        class BlockingSocket(original_socket):  # type: ignore[valid-type,misc]
            """Socket wrapper that enforces network blocking rules."""

            def connect(self, address: tuple[str, int] | object) -> None:
                """Check permissions then delegate to actual connect.

                Args:
                    address: The target address (host, port) tuple.

                Raises:
                    NetworkAccessViolationError: If connection is not allowed
                        and enforcement mode is STRICT.

                """
                # Extract host and port from address tuple (2 = min tuple length)
                if isinstance(address, tuple) and len(address) >= 2:  # noqa: PLR2004
                    host, port = address[0], address[1]

                    # Check if connection is allowed (accessing parent via closure)
                    if not blocker._do_check_connection_allowed(host, port):  # noqa: SLF001
                        blocker.on_violation(host, port, blocker.current_test_nodeid)

                # If we get here, either:
                # 1. Connection is allowed
                # 2. Enforcement mode is WARN or OFF
                # Proceed with the actual connection
                return super().connect(address)  # type: ignore[no-any-return]

            def connect_ex(self, address: tuple[str, int] | object) -> int:
                """Check permissions then delegate to actual connect_ex.

                Args:
                    address: The target address (host, port) tuple.

                Returns:
                    0 on success, or an error code.

                Raises:
                    NetworkAccessViolationError: If connection is not allowed
                        and enforcement mode is STRICT.

                """
                # Extract host and port from address tuple (2 = min tuple length)
                if isinstance(address, tuple) and len(address) >= 2:  # noqa: PLR2004
                    host, port = address[0], address[1]

                    # Check if connection is allowed (accessing parent via closure)
                    if not blocker._do_check_connection_allowed(host, port):  # noqa: SLF001
                        blocker.on_violation(host, port, blocker.current_test_nodeid)

                # If we get here, proceed with the actual connection
                return super().connect_ex(address)  # type: ignore[no-any-return]

        return BlockingSocket
