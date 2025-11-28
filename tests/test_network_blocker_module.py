"""Test the network blocker adapters.

This module tests both the FakeNetworkBlocker (test adapter) and
SocketPatchingNetworkBlocker (production adapter) implementations.

The network blockers follow hexagonal architecture:
- NetworkBlockerPort is the Port (interface)
- FakeNetworkBlocker is a Test Adapter (test double)
- SocketPatchingNetworkBlocker is a Production Adapter (real implementation)

This follows the same pattern as the timer module (TestTimer/FakeTimer/WallTimer).
"""

from __future__ import annotations

import pytest
from icontract import ViolationError

from pytest_test_categories.adapters.fake_network import FakeNetworkBlocker
from pytest_test_categories.adapters.network import SocketPatchingNetworkBlocker
from pytest_test_categories.exceptions import NetworkAccessViolationError
from pytest_test_categories.ports.network import (
    BlockerState,
    ConnectionAttempt,
    EnforcementMode,
)
from pytest_test_categories.types import (
    NetworkMode,
    TestSize,
)


@pytest.mark.small
class DescribeFakeNetworkBlocker:
    """Tests for the FakeNetworkBlocker test double."""

    def it_starts_in_inactive_state(self) -> None:
        """Verify the blocker initializes in INACTIVE state."""
        blocker = FakeNetworkBlocker()

        assert blocker.state == BlockerState.INACTIVE

    def it_transitions_to_active_on_activate(self) -> None:
        """Verify activate() transitions from INACTIVE to ACTIVE."""
        blocker = FakeNetworkBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert blocker.state == BlockerState.ACTIVE

    def it_transitions_to_inactive_on_deactivate(self) -> None:
        """Verify deactivate() transitions from ACTIVE to INACTIVE."""
        blocker = FakeNetworkBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        blocker.deactivate()

        assert blocker.state == BlockerState.INACTIVE

    def it_fails_to_activate_when_already_active(self) -> None:
        """Verify activate() raises when already ACTIVE."""
        blocker = FakeNetworkBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        with pytest.raises(ViolationError, match='INACTIVE'):
            blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

    def it_fails_to_deactivate_when_inactive(self) -> None:
        """Verify deactivate() raises when already INACTIVE."""
        blocker = FakeNetworkBlocker()

        with pytest.raises(ViolationError, match='ACTIVE'):
            blocker.deactivate()

    def it_records_activation_parameters(self) -> None:
        """Verify the blocker records test size and enforcement mode."""
        blocker = FakeNetworkBlocker()

        blocker.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        assert blocker.current_test_size == TestSize.MEDIUM
        assert blocker.current_enforcement_mode == EnforcementMode.WARN

    def it_blocks_all_connections_for_small_tests(self) -> None:
        """Verify small tests cannot access any network."""
        blocker = FakeNetworkBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert blocker.check_connection_allowed('localhost', 8080) is False
        assert blocker.check_connection_allowed('127.0.0.1', 80) is False
        assert blocker.check_connection_allowed('api.example.com', 443) is False

    def it_allows_localhost_for_medium_tests(self) -> None:
        """Verify medium tests can access localhost only."""
        blocker = FakeNetworkBlocker()
        blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

        assert blocker.check_connection_allowed('localhost', 8080) is True
        assert blocker.check_connection_allowed('127.0.0.1', 80) is True
        assert blocker.check_connection_allowed('::1', 443) is True
        assert blocker.check_connection_allowed('api.example.com', 443) is False

    def it_allows_all_connections_for_large_tests(self) -> None:
        """Verify large tests can access any network."""
        blocker = FakeNetworkBlocker()
        blocker.activate(TestSize.LARGE, EnforcementMode.STRICT)

        assert blocker.check_connection_allowed('localhost', 8080) is True
        assert blocker.check_connection_allowed('api.example.com', 443) is True
        assert blocker.check_connection_allowed('external.service.io', 9000) is True

    def it_allows_all_connections_for_xlarge_tests(self) -> None:
        """Verify xlarge tests can access any network."""
        blocker = FakeNetworkBlocker()
        blocker.activate(TestSize.XLARGE, EnforcementMode.STRICT)

        assert blocker.check_connection_allowed('localhost', 8080) is True
        assert blocker.check_connection_allowed('api.example.com', 443) is True

    def it_records_connection_attempts(self) -> None:
        """Verify the blocker tracks connection attempts."""
        blocker = FakeNetworkBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        blocker.check_connection_allowed('api.example.com', 443)
        blocker.check_connection_allowed('localhost', 8080)

        assert len(blocker.connection_attempts) == 2
        assert blocker.connection_attempts[0] == ConnectionAttempt(
            host='api.example.com',
            port=443,
            test_nodeid='',
            allowed=False,
        )
        assert blocker.connection_attempts[1] == ConnectionAttempt(
            host='localhost',
            port=8080,
            test_nodeid='',
            allowed=False,
        )

    def it_raises_on_violation_in_strict_mode(self) -> None:
        """Verify on_violation raises NetworkAccessViolationError in STRICT mode."""
        blocker = FakeNetworkBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        with pytest.raises(NetworkAccessViolationError) as exc_info:
            blocker.on_violation('api.example.com', 443, 'test_module.py::test_fn')

        assert exc_info.value.host == 'api.example.com'
        assert exc_info.value.port == 443
        assert exc_info.value.test_size == TestSize.SMALL

    def it_records_warning_in_warn_mode(self) -> None:
        """Verify on_violation records warning in WARN mode."""
        blocker = FakeNetworkBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.WARN)

        blocker.on_violation('api.example.com', 443, 'test_module.py::test_fn')

        assert len(blocker.warnings) == 1
        assert 'api.example.com:443' in blocker.warnings[0]

    def it_does_nothing_in_off_mode(self) -> None:
        """Verify on_violation does nothing in OFF mode."""
        blocker = FakeNetworkBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.OFF)

        # This should not raise
        blocker.on_violation('api.example.com', 443, 'test_module.py::test_fn')

        assert len(blocker.warnings) == 0

    def it_fails_check_connection_when_inactive(self) -> None:
        """Verify check_connection_allowed raises when INACTIVE."""
        blocker = FakeNetworkBlocker()

        with pytest.raises(ViolationError, match='ACTIVE'):
            blocker.check_connection_allowed('localhost', 8080)

    def it_fails_on_violation_when_inactive(self) -> None:
        """Verify on_violation raises when INACTIVE."""
        blocker = FakeNetworkBlocker()

        with pytest.raises(ViolationError, match='ACTIVE'):
            blocker.on_violation('localhost', 8080, 'test::fn')

    def it_resets_to_initial_state(self) -> None:
        """Verify reset() returns blocker to initial state."""
        blocker = FakeNetworkBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        blocker.check_connection_allowed('api.example.com', 443)

        blocker.reset()

        assert blocker.state == BlockerState.INACTIVE
        assert blocker.current_test_size is None
        assert blocker.current_enforcement_mode is None
        assert len(blocker.connection_attempts) == 0
        assert len(blocker.warnings) == 0

    def it_resets_even_when_active(self) -> None:
        """Verify reset() works regardless of current state."""
        blocker = FakeNetworkBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        # reset() should work even when ACTIVE (unlike deactivate)
        blocker.reset()

        assert blocker.state == BlockerState.INACTIVE

    def it_tracks_call_counts(self) -> None:
        """Verify the blocker tracks method invocation counts."""
        blocker = FakeNetworkBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        blocker.check_connection_allowed('host1', 80)
        blocker.check_connection_allowed('host2', 443)
        blocker.deactivate()

        assert blocker.activate_count == 1
        assert blocker.deactivate_count == 1
        assert blocker.check_count == 2


@pytest.mark.small
class DescribeSocketPatchingNetworkBlocker:
    """Tests for the SocketPatchingNetworkBlocker production adapter."""

    def it_starts_in_inactive_state(self) -> None:
        """Verify the blocker initializes in INACTIVE state."""
        blocker = SocketPatchingNetworkBlocker()

        assert blocker.state == BlockerState.INACTIVE

    def it_transitions_to_active_on_activate(self) -> None:
        """Verify activate() transitions from INACTIVE to ACTIVE."""
        blocker = SocketPatchingNetworkBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert blocker.state == BlockerState.ACTIVE

        # Clean up
        blocker.deactivate()

    def it_transitions_to_inactive_on_deactivate(self) -> None:
        """Verify deactivate() transitions from ACTIVE to INACTIVE."""
        blocker = SocketPatchingNetworkBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        blocker.deactivate()

        assert blocker.state == BlockerState.INACTIVE

    def it_fails_to_activate_when_already_active(self) -> None:
        """Verify activate() raises when already ACTIVE."""
        blocker = SocketPatchingNetworkBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        try:
            with pytest.raises(ViolationError, match='INACTIVE'):
                blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        finally:
            blocker.reset()

    def it_fails_to_deactivate_when_inactive(self) -> None:
        """Verify deactivate() raises when already INACTIVE."""
        blocker = SocketPatchingNetworkBlocker()

        with pytest.raises(ViolationError, match='ACTIVE'):
            blocker.deactivate()

    def it_stores_activation_parameters(self) -> None:
        """Verify the blocker stores test size and enforcement mode."""
        blocker = SocketPatchingNetworkBlocker()

        blocker.activate(TestSize.MEDIUM, EnforcementMode.WARN)

        assert blocker.current_test_size == TestSize.MEDIUM
        assert blocker.current_enforcement_mode == EnforcementMode.WARN

        blocker.deactivate()

    def it_blocks_all_connections_for_small_tests(self) -> None:
        """Verify small tests cannot access any network."""
        blocker = SocketPatchingNetworkBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        assert blocker.check_connection_allowed('localhost', 8080) is False
        assert blocker.check_connection_allowed('127.0.0.1', 80) is False
        assert blocker.check_connection_allowed('api.example.com', 443) is False

        blocker.deactivate()

    def it_allows_localhost_for_medium_tests(self) -> None:
        """Verify medium tests can access localhost only."""
        blocker = SocketPatchingNetworkBlocker()
        blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

        assert blocker.check_connection_allowed('localhost', 8080) is True
        assert blocker.check_connection_allowed('127.0.0.1', 80) is True
        assert blocker.check_connection_allowed('::1', 443) is True
        assert blocker.check_connection_allowed('api.example.com', 443) is False

        blocker.deactivate()

    def it_allows_all_connections_for_large_tests(self) -> None:
        """Verify large tests can access any network."""
        blocker = SocketPatchingNetworkBlocker()
        blocker.activate(TestSize.LARGE, EnforcementMode.STRICT)

        assert blocker.check_connection_allowed('localhost', 8080) is True
        assert blocker.check_connection_allowed('api.example.com', 443) is True

        blocker.deactivate()

    def it_raises_on_violation_in_strict_mode(self) -> None:
        """Verify on_violation raises NetworkAccessViolationError in STRICT mode."""
        blocker = SocketPatchingNetworkBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        with pytest.raises(NetworkAccessViolationError) as exc_info:
            blocker.on_violation('api.example.com', 443, 'test_module.py::test_fn')

        assert exc_info.value.host == 'api.example.com'
        assert exc_info.value.port == 443

        blocker.deactivate()

    def it_resets_to_initial_state(self) -> None:
        """Verify reset() returns blocker to initial state."""
        blocker = SocketPatchingNetworkBlocker()
        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        blocker.reset()

        assert blocker.state == BlockerState.INACTIVE
        assert blocker.current_test_size is None
        assert blocker.current_enforcement_mode is None

    def it_patches_socket_on_activate(self) -> None:
        """Verify socket.socket is patched when activated."""
        import socket

        original_socket = socket.socket
        blocker = SocketPatchingNetworkBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)

        # The socket class should be patched
        assert socket.socket is not original_socket

        blocker.deactivate()

        # Should be restored after deactivate
        assert socket.socket is original_socket

    def it_restores_socket_on_deactivate(self) -> None:
        """Verify socket.socket is restored when deactivated."""
        import socket

        original_socket = socket.socket
        blocker = SocketPatchingNetworkBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        blocker.deactivate()

        assert socket.socket is original_socket

    def it_restores_socket_on_reset(self) -> None:
        """Verify socket.socket is restored on reset."""
        import socket

        original_socket = socket.socket
        blocker = SocketPatchingNetworkBlocker()

        blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        blocker.reset()

        assert socket.socket is original_socket


@pytest.mark.small
class DescribeLocalhostDetection:
    """Tests for localhost detection logic."""

    @pytest.mark.parametrize(
        'host',
        [
            'localhost',
            'LOCALHOST',
            'LocalHost',
            '127.0.0.1',
            '127.0.0.255',
            '127.255.255.255',
            '::1',
            '0:0:0:0:0:0:0:1',
        ],
    )
    def it_recognizes_localhost_variants(self, host: str) -> None:
        """Verify various localhost representations are recognized."""
        blocker = FakeNetworkBlocker()
        blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

        assert blocker.check_connection_allowed(host, 80) is True

    @pytest.mark.parametrize(
        'host',
        [
            'example.com',
            '192.168.1.1',
            '10.0.0.1',
            '8.8.8.8',
            '::2',
            'localhost.localdomain',  # Not a standard localhost alias
        ],
    )
    def it_rejects_non_localhost_for_medium_tests(self, host: str) -> None:
        """Verify non-localhost hosts are blocked for medium tests."""
        blocker = FakeNetworkBlocker()
        blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)

        assert blocker.check_connection_allowed(host, 80) is False


@pytest.mark.small
class DescribeNetworkModeEnum:
    """Tests for the NetworkMode enum."""

    def it_has_block_all_value(self) -> None:
        """Verify BLOCK_ALL value is correct."""
        assert NetworkMode.BLOCK_ALL.value == 'block_all'

    def it_has_localhost_only_value(self) -> None:
        """Verify LOCALHOST_ONLY value is correct."""
        assert NetworkMode.LOCALHOST_ONLY.value == 'localhost'

    def it_has_allow_all_value(self) -> None:
        """Verify ALLOW_ALL value is correct."""
        assert NetworkMode.ALLOW_ALL.value == 'allow_all'


@pytest.mark.small
class DescribeTestSizeNetworkMode:
    """Tests for TestSize.network_mode property."""

    def it_maps_small_to_block_all(self) -> None:
        """Verify small tests map to BLOCK_ALL network mode."""
        assert TestSize.SMALL.network_mode == NetworkMode.BLOCK_ALL

    def it_maps_medium_to_localhost_only(self) -> None:
        """Verify medium tests map to LOCALHOST_ONLY network mode."""
        assert TestSize.MEDIUM.network_mode == NetworkMode.LOCALHOST_ONLY

    def it_maps_large_to_allow_all(self) -> None:
        """Verify large tests map to ALLOW_ALL network mode."""
        assert TestSize.LARGE.network_mode == NetworkMode.ALLOW_ALL

    def it_maps_xlarge_to_allow_all(self) -> None:
        """Verify xlarge tests map to ALLOW_ALL network mode."""
        assert TestSize.XLARGE.network_mode == NetworkMode.ALLOW_ALL
