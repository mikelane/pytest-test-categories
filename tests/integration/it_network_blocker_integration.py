"""Integration tests for the network blocker production adapter.

These tests verify that SocketPatchingNetworkBlocker correctly intercepts
real network connections using actual socket operations.

All tests use @pytest.mark.medium since they involve real socket operations
but do not require external network access.
"""

from __future__ import annotations

import socket

import pytest

from pytest_test_categories.adapters.network import SocketPatchingNetworkBlocker
from pytest_test_categories.exceptions import NetworkAccessViolationError
from pytest_test_categories.ports.network import EnforcementMode
from pytest_test_categories.types import TestSize


@pytest.mark.medium
class DescribeSocketPatchingNetworkBlockerIntegration:
    """Integration tests for SocketPatchingNetworkBlocker with real sockets."""

    def it_blocks_real_socket_connection_for_small_test(self) -> None:
        """Verify real socket.connect() is blocked for small tests in STRICT mode."""
        blocker = SocketPatchingNetworkBlocker()

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

            # Create a real socket and attempt to connect
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)

            with pytest.raises(NetworkAccessViolationError) as exc_info:
                # This should be intercepted and raise before actually connecting
                sock.connect(('example.com', 80))

            assert exc_info.value.host == 'example.com'
            assert exc_info.value.port == 80
            assert exc_info.value.test_size == TestSize.SMALL

        finally:
            blocker.reset()
            sock.close()

    def it_blocks_localhost_connection_for_small_test(self) -> None:
        """Verify even localhost is blocked for small tests."""
        blocker = SocketPatchingNetworkBlocker()

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)

            with pytest.raises(NetworkAccessViolationError) as exc_info:
                sock.connect(('localhost', 8080))

            assert exc_info.value.host == 'localhost'

        finally:
            blocker.reset()
            sock.close()

    def it_allows_localhost_connection_for_medium_test(self) -> None:
        """Verify localhost connections are allowed for medium tests.

        Note: We cannot actually connect since there's no server listening,
        but the blocker should not raise NetworkAccessViolationError.
        Instead, we should get a connection refused or similar socket error.
        """
        blocker = SocketPatchingNetworkBlocker()

        try:
            blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)

            # The blocker should NOT raise NetworkAccessViolationError
            # We expect a socket error instead (connection refused, timeout, etc.)
            with pytest.raises((ConnectionRefusedError, OSError, TimeoutError)):
                sock.connect(('127.0.0.1', 59999))  # Use a port unlikely to be in use

        finally:
            blocker.reset()
            sock.close()

    def it_blocks_external_connection_for_medium_test(self) -> None:
        """Verify external connections are blocked for medium tests."""
        blocker = SocketPatchingNetworkBlocker()

        try:
            blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)

            with pytest.raises(NetworkAccessViolationError) as exc_info:
                sock.connect(('external.example.com', 443))

            assert exc_info.value.host == 'external.example.com'

        finally:
            blocker.reset()
            sock.close()

    def it_intercepts_connect_ex(self) -> None:
        """Verify connect_ex() is also intercepted."""
        blocker = SocketPatchingNetworkBlocker()

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)

            with pytest.raises(NetworkAccessViolationError) as exc_info:
                sock.connect_ex(('example.com', 80))

            assert exc_info.value.host == 'example.com'

        finally:
            blocker.reset()
            sock.close()

    def it_restores_socket_after_deactivation(self) -> None:
        """Verify socket.socket is fully restored after deactivation."""
        original_socket_class = socket.socket
        blocker = SocketPatchingNetworkBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        # Socket should be patched
        assert socket.socket is not original_socket_class

        blocker.deactivate()

        # Socket should be restored
        assert socket.socket is original_socket_class

    def it_handles_multiple_activate_deactivate_cycles(self) -> None:
        """Verify blocker works correctly through multiple cycles."""
        original_socket_class = socket.socket
        blocker = SocketPatchingNetworkBlocker()

        # First cycle
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        assert socket.socket is not original_socket_class
        blocker.deactivate()
        assert socket.socket is original_socket_class

        # Second cycle with different settings
        blocker.activate(TestSize.MEDIUM, EnforcementMode.WARN)
        assert socket.socket is not original_socket_class
        blocker.deactivate()
        assert socket.socket is original_socket_class

    def it_handles_ipv6_localhost(self) -> None:
        """Verify IPv6 localhost (::1) is correctly handled for medium tests."""
        blocker = SocketPatchingNetworkBlocker()

        try:
            blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

            # IPv6 socket
            sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            sock.settimeout(0.5)

            # ::1 should be allowed for medium tests
            # We expect a socket error, not NetworkAccessViolationError
            with pytest.raises((ConnectionRefusedError, OSError, TimeoutError)):
                sock.connect(('::1', 59999))

        finally:
            blocker.reset()
            sock.close()


@pytest.mark.medium
class DescribeSocketPatchingNetworkBlockerEdgeCases:
    """Integration tests for edge cases and error scenarios."""

    def it_handles_socket_creation_after_activation(self) -> None:
        """Verify sockets created after activation are still intercepted."""
        blocker = SocketPatchingNetworkBlocker()

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

            # Create socket after activation
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)

            with pytest.raises(NetworkAccessViolationError):
                sock.connect(('example.com', 80))

        finally:
            blocker.reset()
            sock.close()

    def it_cleans_up_on_reset_even_if_active(self) -> None:
        """Verify reset() properly cleans up even when blocker is active."""
        original_socket_class = socket.socket
        blocker = SocketPatchingNetworkBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        # Reset without deactivating first
        blocker.reset()

        # Socket should still be restored
        assert socket.socket is original_socket_class

    def it_preserves_socket_functionality_for_allowed_connections(self) -> None:
        """Verify socket functionality is preserved when connections are allowed.

        This test uses large test size which allows all connections.
        We verify that the socket still works as expected (aside from the
        actual network connectivity which we cannot control in a unit test).
        """
        blocker = SocketPatchingNetworkBlocker()

        try:
            blocker.activate(TestSize.LARGE, EnforcementMode.STRICT)

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # Verify basic socket attributes still work
            assert sock.family == socket.AF_INET
            assert sock.type == socket.SOCK_STREAM

            # Set options should still work
            sock.settimeout(1.0)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        finally:
            blocker.reset()
            sock.close()


@pytest.mark.large
class DescribeSocketPatchingNetworkBlockerExternalNetworkTests:
    """Tests requiring external network access.

    These tests need to make actual network connections to verify
    the blocker allows connections in specific modes. They are marked
    large because medium tests are restricted to localhost only.
    """

    def it_allows_all_connections_for_large_test(self) -> None:
        """Verify all connections are allowed for large tests.

        Note: We cannot actually connect since the host may not exist,
        but the blocker should not raise NetworkAccessViolationError.
        """
        blocker = SocketPatchingNetworkBlocker()

        try:
            blocker.activate(TestSize.LARGE, EnforcementMode.STRICT)

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)

            # The blocker should NOT raise NetworkAccessViolationError
            # We expect a socket error instead (DNS failure, timeout, etc.)
            with pytest.raises((socket.gaierror, OSError, TimeoutError)):
                sock.connect(('nonexistent.invalid.example', 80))

        finally:
            blocker.reset()
            sock.close()

    def it_allows_connection_in_warn_mode(self) -> None:
        """Verify connections proceed in WARN mode (no exception raised)."""
        blocker = SocketPatchingNetworkBlocker()

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.WARN)

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)

            # In WARN mode, should NOT raise NetworkAccessViolationError
            # Should get a socket error instead since we're trying to connect
            # to a nonexistent host
            with pytest.raises((socket.gaierror, OSError, TimeoutError)):
                sock.connect(('nonexistent.invalid.example', 80))

        finally:
            blocker.reset()
            sock.close()

    def it_allows_connection_in_off_mode(self) -> None:
        """Verify connections proceed in OFF mode (no interception)."""
        blocker = SocketPatchingNetworkBlocker()

        try:
            blocker.activate(TestSize.SMALL, EnforcementMode.OFF)

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)

            # In OFF mode, should NOT raise NetworkAccessViolationError
            with pytest.raises((socket.gaierror, OSError, TimeoutError)):
                sock.connect(('nonexistent.invalid.example', 80))

        finally:
            blocker.reset()
            sock.close()
