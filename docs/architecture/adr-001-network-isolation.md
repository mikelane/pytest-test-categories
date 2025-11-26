# ADR-001: Network Isolation Mechanism for Small Tests

## Status

Proposed

## Context

Small tests, as defined by Google's "Software Engineering at Google" best practices, must be **hermetic** - they should run entirely in memory with no external dependencies. This makes them:

- **Fast**: No I/O latency from network operations
- **Deterministic**: No dependency on external service state or availability
- **Parallelizable**: No resource contention with other tests
- **Reliable**: No flaky failures due to network timeouts, DNS issues, or service outages

Currently, pytest-test-categories enforces only timing constraints (1 second for small tests). However, a test can pass the timing constraint while still making network requests that happen to complete quickly. This violates the hermetic principle and creates fragile tests that may fail intermittently in CI environments.

We need a mechanism to:

1. Detect network access attempts during small test execution
2. Block or warn about these attempts based on configuration
3. Provide clear error messages with remediation guidance

### Existing Architecture Context

The plugin follows **hexagonal architecture** (ports and adapters):

- **Ports**: Abstract interfaces defining contracts (`TestTimer`, `TestItemPort`, `OutputWriterPort`, `WarningSystemPort`)
- **Production Adapters**: Real implementations (`WallTimer`, `PytestItemAdapter`, `TerminalReporterAdapter`)
- **Test Adapters**: Controllable test doubles (`FakeTimer`, `FakeTestItem`, `StringBufferWriter`)

This pattern enables:
- Unit tests to be fast and deterministic (using fake adapters)
- Integration tests to validate real behavior (using production adapters)
- Easy extensibility for new resource types

### Research: Existing Solutions

**pytest-socket** provides network blocking through:
- Patching `socket.socket` with a `GuardedSocket` class
- Custom exceptions: `SocketBlockedError`, `SocketConnectBlockedError`
- Integration via pytest hooks (`pytest_runtest_setup`, `pytest_runtest_teardown`)
- Configuration via markers, fixtures, and CLI flags
- Host allowlisting for selective blocking

Key insights from pytest-socket:
1. Socket-level patching is the most reliable interception point
2. Connection blocking (vs socket creation blocking) allows more granular control
3. Host resolution caching improves performance
4. Layered configuration (fixture > marker > CLI > global) provides flexibility

## Decision

We will implement network isolation using a **socket patching approach** following the hexagonal architecture pattern.

### 1. Port Interface: `NetworkBlockerPort`

Define an abstract interface for network blocking:

```python
class NetworkBlockerPort(ABC):
    """Port defining network blocking behavior.

    Implementations control whether network access is permitted during
    test execution. The port follows a state machine pattern:
    INACTIVE -> ACTIVE -> INACTIVE
    """

    @abstractmethod
    def activate(self, test_size: TestSize, enforcement_mode: EnforcementMode) -> None:
        """Activate network blocking for a test.

        Args:
            test_size: The size category of the current test.
            enforcement_mode: Whether to raise or warn on violations.
        """

    @abstractmethod
    def deactivate(self) -> None:
        """Deactivate network blocking, restoring normal socket behavior."""

    @abstractmethod
    def check_connection_allowed(self, host: str, port: int) -> bool:
        """Check if a connection to host:port is allowed.

        Args:
            host: The target hostname or IP address.
            port: The target port number.

        Returns:
            True if connection is allowed, False otherwise.
        """

    @abstractmethod
    def on_violation(self, host: str, port: int, test_nodeid: str) -> None:
        """Handle a network access violation.

        Args:
            host: The attempted target hostname.
            port: The attempted target port.
            test_nodeid: The pytest node ID of the violating test.

        Raises:
            HermeticityViolationError: If enforcement mode is STRICT.
        """
```

### 2. Production Adapter: `SocketPatchingBlocker`

Implements `NetworkBlockerPort` by:
- Storing reference to original `socket.socket`
- Replacing with `GuardedSocket` that intercepts `connect()` calls
- Delegating violation handling based on enforcement mode
- Restoring original socket on deactivation

### 3. Test Adapter: `FakeNetworkBlocker`

Provides controllable test double:
- Tracks activation/deactivation calls
- Records connection attempts for assertion
- Configurable allowed hosts list
- No actual socket patching

### 4. Exception Hierarchy

```python
class HermeticityViolationError(Exception):
    """Base exception for test hermeticity violations.

    Raised when a test violates its size category's resource restrictions.
    """
    pass

class NetworkAccessViolationError(HermeticityViolationError):
    """Raised when a test makes an unauthorized network request.

    Attributes:
        test_size: The test's size category.
        host: The attempted destination host.
        port: The attempted destination port.
        remediation: Suggested fixes for the violation.
    """
    pass
```

### 5. Enforcement Modes

```python
class EnforcementMode(StrEnum):
    """Controls how resource violations are handled."""

    STRICT = 'strict'   # Raise exception, fail test immediately
    WARN = 'warn'       # Emit warning, allow test to continue
    OFF = 'off'         # No enforcement (for gradual adoption)
```

### 6. Configuration Schema

Support configuration via `pyproject.toml`:

```toml
[tool.pytest-test-categories]
# Global enforcement mode (default: warn)
enforcement = "strict"

# Network-specific settings
[tool.pytest-test-categories.network]
# Per-size restrictions
small = "block"      # Block all network (default for small)
medium = "localhost" # Allow only localhost (default for medium)
large = "allow"      # Allow all (default for large/xlarge)

# Allowlist for specific hosts (applies to all sizes)
allowed_hosts = [
    "localhost",
    "127.0.0.1",
    "::1",
]
```

And CLI options:

```bash
pytest --network-enforcement=strict|warn|off
pytest --allow-network-hosts=host1,host2
```

And per-test markers:

```python
@pytest.mark.small
@pytest.mark.allow_network  # Override: allow network for this test
def test_special_case():
    ...
```

### 7. Integration Points

The network blocker integrates via pytest hooks:

1. **`pytest_configure`**: Read configuration, create blocker instance
2. **`pytest_runtest_setup`**: Activate blocking based on test size and markers
3. **`pytest_runtest_teardown`**: Deactivate blocking, restore socket
4. **`pytest_terminal_summary`**: Report network violation statistics

### 8. Error Message Format

Violation errors provide actionable guidance:

```
================== HermeticityViolationError ==================
Test: test_fetch_user_profile (tests/test_users.py:42)
Category: SMALL
Violation: Network access attempted

Details:
  Attempted connection to: api.example.com:443

Small tests cannot access the network. Options:
  1. Mock the network call using responses, httpretty, or respx
  2. Use dependency injection to provide a fake HTTP client
  3. Change test category to @pytest.mark.medium (if network is required)

Documentation: https://pytest-test-categories.readthedocs.io/resource-isolation/
==============================================================
```

## Consequences

### Benefits

1. **Consistent Architecture**: Follows established hexagonal architecture pattern
2. **Testability**: Fake adapter enables fast, deterministic unit tests
3. **Flexibility**: Multiple configuration layers (CLI, config file, markers)
4. **Gradual Adoption**: Warn mode allows incremental enforcement
5. **Clear Feedback**: Actionable error messages guide developers
6. **Extensibility**: Port pattern enables future resource types (filesystem, subprocess)

### Trade-offs

1. **Socket-Level Only**: Won't catch higher-level network abstractions that bypass socket (rare)
2. **Global Patching**: Socket replacement affects entire process during test
3. **Performance**: Minor overhead from connection interception (microseconds)
4. **Complexity**: Adds configuration surface area

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Conflicts with pytest-socket | Document interaction, test compatibility |
| Thread safety issues | Use thread-local state for blocking context |
| Async socket operations | Test with asyncio, aiohttp to ensure coverage |
| DNS resolution bypass | Block at socket level (before DNS resolution) |

## Alternatives Considered

### Alternative 1: Import Hook Blocking

**Approach**: Use import hooks to prevent importing network-related modules (`socket`, `urllib`, `requests`).

**Pros**:
- Catches network usage at module level
- No runtime overhead during test execution

**Cons**:
- Too coarse-grained (blocks all use, not just during tests)
- Breaks test setup/teardown that needs network
- Requires tracking all network-related modules
- Module already imported before test runs in many cases

**Verdict**: Rejected - too inflexible for test-specific enforcement.

### Alternative 2: Context Manager Wrapping

**Approach**: Wrap test execution in a context manager that patches socket temporarily.

**Pros**:
- Clean scope control
- Explicit entry/exit points

**Cons**:
- Requires modifying how pytest calls tests
- Complex interaction with fixtures
- Doesn't integrate cleanly with pytest hooks

**Verdict**: Rejected - socket patching via hooks achieves same goal with better pytest integration.

### Alternative 3: Network Namespace Isolation (Linux)

**Approach**: Run tests in isolated network namespaces.

**Pros**:
- True kernel-level isolation
- Cannot be bypassed

**Cons**:
- Linux-only
- Requires root or CAP_NET_ADMIN
- Significant performance overhead
- Complex setup

**Verdict**: Rejected - platform-specific and heavy-weight for unit test isolation.

### Alternative 4: Proxy-Based Blocking

**Approach**: Force all traffic through a local proxy that rejects requests.

**Pros**:
- Can log all traffic
- Works with any network library

**Cons**:
- Requires proxy configuration
- SSL/TLS certificate issues
- Performance overhead
- Complex setup

**Verdict**: Rejected - too complex for test isolation use case.

## Implementation Notes

### Phase 1: Core Infrastructure (This Design)
- Define `NetworkBlockerPort` interface
- Define `HermeticityViolationError` exception hierarchy
- Define configuration schema
- Document test strategy

### Phase 2: Implementation (Future Issue)
- Implement `SocketPatchingBlocker` adapter
- Implement `FakeNetworkBlocker` test adapter
- Integrate with pytest hooks
- Add CLI options and configuration parsing

### Phase 3: Testing and Documentation (Future Issue)
- Unit tests with `FakeNetworkBlocker`
- Integration tests with real socket blocking
- End-to-end tests with pytester
- User documentation

## References

- [Google's Software Engineering at Google - Testing](https://abseil.io/resources/swe-book/html/ch11.html)
- [pytest-socket](https://github.com/miketheman/pytest-socket) - Prior art for socket blocking
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/) - Ports and adapters pattern
- [pytest-test-categories Planning Doc](../planning/resource-isolation-feature.md)
