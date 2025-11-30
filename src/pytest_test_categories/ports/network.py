"""Network blocking port interface for hermetic test enforcement.

This module defines the abstract interface (port) for network access control
during test execution. Following hexagonal architecture, this port defines
WHAT operations are available, while adapters define HOW they are implemented.

The pattern enables:
- Production adapter (`SocketPatchingBlocker`): Patches socket.socket to intercept
  real network connections
- Test adapter (`FakeNetworkBlocker`): Controllable test double that records
  connection attempts without actual socket manipulation

Example:
    Production usage (via plugin hooks):
    >>> blocker = SocketPatchingBlocker()
    >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
    >>> # Test runs, any socket.connect() raises HermeticityViolationError
    >>> blocker.deactivate()

    Test usage:
    >>> blocker = FakeNetworkBlocker()
    >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
    >>> assert blocker.is_active
    >>> blocker.simulate_connection('api.example.com', 443)
    >>> assert blocker.connection_attempts == [('api.example.com', 443)]

See Also:
    - ADR-001: docs/architecture/adr-001-network-isolation.md
    - Planning: docs/planning/resource-isolation-feature.md
    - Timer port pattern: src/pytest_test_categories/types.py (TestTimer)

"""

from __future__ import annotations

from abc import (
    ABC,
    abstractmethod,
)
from collections.abc import Callable
from enum import StrEnum
from typing import (
    TYPE_CHECKING,
    Any,
)

from icontract import (
    ensure,
    require,
)
from pydantic import (
    BaseModel,
    Field,
)

if TYPE_CHECKING:
    from pytest_test_categories.types import TestSize

# Define ViolationCallback at runtime for Pydantic compatibility
# Using Any to avoid circular imports while still providing type hints
ViolationCallback = Callable[[str, Any], None]


class EnforcementMode(StrEnum):
    """Controls how resource violations are handled during test execution.

    The enforcement mode determines the plugin's response when a test
    violates its size category's resource restrictions.

    Attributes:
        STRICT: Raise exception immediately, failing the test.
        WARN: Emit a warning but allow the test to continue.
        OFF: No enforcement (useful for gradual adoption).

    Example:
        >>> mode = EnforcementMode.STRICT
        >>> if mode == EnforcementMode.STRICT:
        ...     raise HermeticityViolationError('Network access blocked')

    """

    STRICT = 'strict'
    WARN = 'warn'
    OFF = 'off'


class BlockerState(StrEnum):
    """Represents the possible states of a network blocker.

    The blocker follows a simple state machine:
    INACTIVE -> ACTIVE -> INACTIVE

    State transitions:
    - INACTIVE -> ACTIVE: via activate()
    - ACTIVE -> INACTIVE: via deactivate()

    Attributes:
        INACTIVE: Blocker is not intercepting connections.
        ACTIVE: Blocker is actively intercepting connections.

    """

    INACTIVE = 'inactive'
    ACTIVE = 'active'


class ConnectionAttempt(BaseModel, frozen=True):
    """Immutable record of a network connection attempt.

    Used for tracking and reporting connection attempts during test execution.
    This is useful for diagnostics and for test adapters that need to record
    what connections were attempted.

    Attributes:
        host: The target hostname or IP address.
        port: The target port number.
        test_nodeid: The pytest node ID of the test that made the attempt.
        allowed: Whether the connection was permitted.

    Example:
        >>> attempt = ConnectionAttempt(
        ...     host='api.example.com',
        ...     port=443,
        ...     test_nodeid='test_module.py::test_function',
        ...     allowed=False
        ... )

    """

    host: str
    port: int
    test_nodeid: str
    allowed: bool


class NetworkBlockerPort(BaseModel, ABC):
    """Abstract port defining network blocking behavior.

    This port defines the contract for network access control during test
    execution. Implementations (adapters) provide the actual blocking
    mechanism.

    Following hexagonal architecture:
    - This port defines WHAT operations are available
    - Adapters define HOW they are implemented
    - Production adapter: SocketPatchingBlocker (patches socket.socket)
    - Test adapter: FakeNetworkBlocker (records attempts, no real patching)

    The blocker follows a state machine pattern:
    - INACTIVE: Not intercepting connections (initial state)
    - ACTIVE: Intercepting and potentially blocking connections

    State transitions are guarded by icontract preconditions/postconditions,
    following the same pattern as TestTimer. The base class provides public
    methods with contracts that delegate to abstract _do_* methods.

    Attributes:
        state: Current blocker state (INACTIVE or ACTIVE).
        violation_callback: Optional callback invoked when a violation occurs.
            The callback receives (test_nodeid, ViolationType) for tracking.

    Example:
        >>> class FakeNetworkBlocker(NetworkBlockerPort):
        ...     def _do_activate(self, test_size, enforcement_mode):
        ...         # Record parameters for assertions
        ...         pass
        ...
        >>> blocker = FakeNetworkBlocker()
        >>> assert blocker.state == BlockerState.INACTIVE
        >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
        >>> assert blocker.state == BlockerState.ACTIVE

    See Also:
        - TestTimer: Similar state machine pattern in types.py
        - SocketPatchingBlocker: Production adapter (to be implemented)
        - FakeNetworkBlocker: Test adapter (to be implemented)

    """

    model_config = {'arbitrary_types_allowed': True}

    state: BlockerState = BlockerState.INACTIVE
    violation_callback: ViolationCallback | None = Field(default=None, description='Callback for violation tracking')

    @require(lambda self: self.state == BlockerState.INACTIVE, 'Blocker must be INACTIVE to activate')
    @ensure(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE after activation')
    def activate(self, test_size: TestSize, enforcement_mode: EnforcementMode) -> None:
        """Activate network blocking for a test.

        Transitions the blocker from INACTIVE to ACTIVE state. Once active,
        the blocker will intercept network connection attempts and handle
        them according to the enforcement mode and test size restrictions.

        Args:
            test_size: The size category of the current test. Determines
                what connections are allowed:
                - SMALL: Block all network access
                - MEDIUM: Allow localhost only
                - LARGE/XLARGE: Allow all connections
            enforcement_mode: How to handle violations:
                - STRICT: Raise HermeticityViolationError
                - WARN: Emit warning, allow connection
                - OFF: No enforcement

        Raises:
            icontract.ViolationError: If blocker is not in INACTIVE state.

        Example:
            >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
            >>> # Now any socket.connect() call will be intercepted

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
        """Deactivate network blocking, restoring normal socket behavior.

        Transitions the blocker from ACTIVE to INACTIVE state. This should
        be called in a finally block to ensure sockets are restored even
        if the test fails.

        Raises:
            icontract.ViolationError: If blocker is not in ACTIVE state.

        Example:
            >>> try:
            ...     blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
            ...     # test runs
            ... finally:
            ...     blocker.deactivate()  # Always restore sockets

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
    def check_connection_allowed(self, host: str, port: int) -> bool:
        """Check if a connection to host:port is allowed.

        This method is called by the socket interception mechanism to
        determine whether a connection should be permitted.

        The decision depends on:
        - The test size (set during activate())
        - The host being connected to
        - Any configured allowlists

        Args:
            host: The target hostname or IP address.
            port: The target port number.

        Returns:
            True if the connection is allowed, False if it should be blocked.

        Raises:
            icontract.ViolationError: If blocker is not in ACTIVE state.

        Example:
            >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
            >>> blocker.check_connection_allowed('localhost', 8080)
            False  # Small tests cannot access any network
            >>> blocker.activate(TestSize.MEDIUM, EnforcementMode.STRICT)
            >>> blocker.check_connection_allowed('localhost', 8080)
            True   # Medium tests can access localhost
            >>> blocker.check_connection_allowed('api.example.com', 443)
            False  # Medium tests cannot access external hosts

        """
        return self._do_check_connection_allowed(host, port)

    @abstractmethod
    def _do_check_connection_allowed(self, host: str, port: int) -> bool:
        """Determine if a connection to host:port is allowed.

        Subclasses implement this to determine if a connection is allowed.

        Args:
            host: The target hostname or IP address.
            port: The target port number.

        Returns:
            True if the connection is allowed, False if it should be blocked.

        """

    @require(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE to handle violations')
    def on_violation(self, host: str, port: int, test_nodeid: str) -> None:
        """Handle a network access violation.

        Called when a test attempts a connection that is not allowed
        according to its size category restrictions.

        The response depends on the enforcement mode (set during activate()):
        - STRICT: Raise HermeticityViolationError
        - WARN: Emit warning via pytest's warning system
        - OFF: Do nothing (should not be called in OFF mode)

        If a violation_callback is set, it will be called to record the
        violation for JSON report tracking.

        Args:
            host: The attempted destination host.
            port: The attempted destination port.
            test_nodeid: The pytest node ID of the violating test.

        Raises:
            HermeticityViolationError: If enforcement mode is STRICT.
            icontract.ViolationError: If blocker is not in ACTIVE state.

        Example:
            >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT)
            >>> blocker.on_violation('api.example.com', 443, 'test_mod::test_fn')
            HermeticityViolationError: Small tests cannot access the network...

        """
        if self.violation_callback is not None:
            from pytest_test_categories.violations import ViolationType  # noqa: PLC0415

            self.violation_callback(test_nodeid, ViolationType.NETWORK)
        self._do_on_violation(host, port, test_nodeid)

    @abstractmethod
    def _do_on_violation(self, host: str, port: int, test_nodeid: str) -> None:
        """Handle violations according to enforcement mode.

        Subclasses implement this to handle violations according to enforcement mode.

        Args:
            host: The attempted destination host.
            port: The attempted destination port.
            test_nodeid: The pytest node ID of the violating test.

        """

    def reset(self) -> None:
        """Reset blocker to initial INACTIVE state.

        This is a convenience method for cleanup and testing. Unlike
        deactivate(), this does not require the blocker to be in ACTIVE
        state - it unconditionally resets to INACTIVE.

        Subclasses should override to perform any additional cleanup
        (e.g., restoring patched sockets).

        Example:
            >>> blocker.reset()  # Safe to call regardless of current state
            >>> assert blocker.state == BlockerState.INACTIVE

        """
        self.state = BlockerState.INACTIVE
