# ADR-005: Sleep Isolation for Small Tests

## Status

Accepted

> **Implementation Progress**: The core interfaces (`SleepBlockerPort`, `SleepViolationError`,
> `EnforcementMode`) and adapters (`SleepPatchingBlocker`, `FakeSleepBlocker`) are implemented.
> Track progress in Issue #114.

## Context

Small tests, as defined by Google's "Software Engineering at Google" best practices, must be **hermetic** - they should run entirely in memory with no dependencies on wall-clock time. This makes them:

- **Fast**: No waiting for sleep durations
- **Deterministic**: No dependency on system timing or clock precision
- **Parallelizable**: No timing conflicts with other tests
- **Reliable**: No flaky failures due to timing variations across machines

Currently, pytest-test-categories enforces timing constraints (1 second for small tests). However, a test can pass the timing constraint while still using `time.sleep()` or `asyncio.sleep()` for short durations. This violates the hermetic principle because:

1. **Sleep indicates improper synchronization**: Tests should use proper synchronization primitives (e.g., `threading.Event`, `asyncio.Event`) instead of arbitrary delays
2. **Sleep creates flaky tests**: Timing assumptions vary across machines, CI environments, and system load
3. **Sleep hides race conditions**: Tests that "work" with sleep may fail intermittently without it

We need a mechanism to:

1. Detect sleep call attempts during small test execution
2. Block or warn about these attempts based on configuration
3. Provide clear error messages with remediation guidance

### Existing Architecture Context

The plugin follows **hexagonal architecture** (ports and adapters):

- **Ports**: Abstract interfaces defining contracts (`TestTimer`, `NetworkBlockerPort`, `SleepBlockerPort`)
- **Production Adapters**: Real implementations (`WallTimer`, `SocketPatchingBlocker`, `SleepPatchingBlocker`)
- **Test Adapters**: Controllable test doubles (`FakeTimer`, `FakeNetworkBlocker`, `FakeSleepBlocker`)

This pattern enables:
- Unit tests to be fast and deterministic (using fake adapters)
- Integration tests to validate real behavior (using production adapters)
- Easy extensibility for new resource types

### Research: Common Sleep Patterns in Tests

Tests commonly use sleep for:

1. **Waiting for async operations**: Should use proper synchronization (`Event.wait()`, `await condition`)
2. **Rate limiting simulation**: Should use mock time or time abstraction
3. **Polling patterns**: Should use condition-based waiting with timeout
4. **Debouncing**: Should use controllable clock abstraction

All these patterns have proper alternatives that are faster and more reliable.

## Decision

We will implement sleep isolation using a **function patching approach** following the hexagonal architecture pattern.

### 1. Port Interface: `SleepBlockerPort`

Define an abstract interface for sleep blocking:

```python
class SleepBlockerPort(ABC):
    """Port defining sleep blocking behavior.

    Implementations control whether sleep calls are permitted during
    test execution. The port follows a state machine pattern:
    INACTIVE -> ACTIVE -> INACTIVE
    """

    @abstractmethod
    def activate(self, test_size: TestSize, enforcement_mode: EnforcementMode) -> None:
        """Activate sleep blocking for a test.

        Args:
            test_size: The size category of the current test.
            enforcement_mode: Whether to raise or warn on violations.
        """

    @abstractmethod
    def deactivate(self) -> None:
        """Deactivate sleep blocking, restoring normal behavior."""

    @abstractmethod
    def check_sleep_allowed(self, function: str, duration: float) -> bool:
        """Check if a sleep call is allowed.

        Args:
            function: The sleep function name (e.g., 'time.sleep').
            duration: The sleep duration in seconds.

        Returns:
            True if sleep is allowed, False otherwise.
        """

    @abstractmethod
    def on_violation(self, function: str, duration: float, test_nodeid: str) -> None:
        """Handle a sleep violation.

        Args:
            function: The sleep function name.
            duration: The sleep duration in seconds.
            test_nodeid: The pytest node ID of the violating test.

        Raises:
            SleepViolationError: If enforcement mode is STRICT.
        """
```

### 2. Production Adapter: `SleepPatchingBlocker`

Implements `SleepBlockerPort` by:
- Storing references to original `time.sleep` and `asyncio.sleep`
- Replacing with wrapper functions that intercept calls
- Checking permissions before delegating to original functions
- Restoring original functions on deactivation

### 3. Test Adapter: `FakeSleepBlocker`

Provides controllable test double:
- Tracks activation/deactivation calls
- Records sleep attempts for assertion
- Implements same permission logic as production adapter
- No actual function patching

### 4. Exception: `SleepViolationError`

```python
class SleepViolationError(HermeticityViolationError):
    """Raised when a test calls time.sleep() or similar blocking functions.

    Attributes:
        test_size: The test's size category.
        test_nodeid: The pytest node ID of the violating test.
        function: The sleep function that was called.
        duration: The sleep duration in seconds.
    """
```

### 5. Intercepted Entry Points

The following sleep functions are intercepted:

| Function | Module | Notes |
|----------|--------|-------|
| `time.sleep` | `time` | Standard synchronous sleep |
| `asyncio.sleep` | `asyncio` | Async coroutine sleep |

**Not intercepted** (intentionally):
- `threading.Event.wait()`: Has legitimate synchronization uses
- `select.select()`: Too low-level, used for I/O multiplexing
- `signal.pause()`: Platform-specific, rare in tests

### 6. Enforcement Modes

```python
class EnforcementMode(StrEnum):
    """Controls how resource violations are handled."""

    STRICT = 'strict'   # Raise exception, fail test immediately
    WARN = 'warn'       # Emit warning, allow test to continue
    OFF = 'off'         # No enforcement (for gradual adoption)
```

### 7. Size-Based Rules

| Test Size | Sleep Allowed | Rationale |
|-----------|---------------|-----------|
| SMALL | No | Must be hermetic, no timing dependencies |
| MEDIUM | Yes | May need timing for integration scenarios |
| LARGE | Yes | Full system tests may require real timing |
| XLARGE | Yes | Same as LARGE |

### 8. Error Message Format

Violation errors provide actionable guidance:

```
============================================================
HermeticityViolationError
============================================================
Test: test_module.py::test_function
Category: SMALL
Violation: Sleep call attempted

Details:
  Called: time.sleep(0.1)

Small tests have restricted resource access. Options:
  1. Use proper synchronization instead of sleep (e.g., threading.Event)
  2. Use condition-based waiting with polling and timeout
  3. Mock time.sleep using pytest-mock (mocker.patch)
  4. Use a FakeTimer or controllable time abstraction
  5. Change test category to @pytest.mark.medium (if timing is required)

Documentation: See docs/architecture/adr-005-sleep-isolation.md
============================================================
```

## Consequences

### Positive

1. **Faster Tests**: Eliminates unnecessary waiting in small tests
2. **More Reliable Tests**: Removes timing-based flakiness
3. **Better Design**: Encourages proper synchronization patterns
4. **Consistent Architecture**: Follows established hexagonal architecture pattern
5. **Testability**: Fake adapter enables fast, deterministic unit tests
6. **Clear Feedback**: Actionable error messages guide developers to proper solutions

### Negative

1. **Learning Curve**: Developers must learn proper synchronization patterns
2. **Migration Effort**: Existing tests using sleep need refactoring
3. **False Positives**: Some legitimate short sleeps may be flagged (rare)
4. **Global Patching**: Function replacement affects entire process during test

### Trade-offs

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Scope | `time.sleep` + `asyncio.sleep` only | Covers 99% of cases, avoids over-complexity |
| threading.Event | Not blocked | Legitimate synchronization use |
| Enforcement | Configurable (STRICT/WARN/OFF) | Enables gradual adoption |

## Implementation Notes

### State Machine

The blocker follows a strict state machine:

```
                 activate()
    INACTIVE ─────────────────> ACTIVE
        ^                          │
        │                          │
        └──────────────────────────┘
                 deactivate()
```

State transitions are enforced via `icontract` preconditions/postconditions.

### Thread Safety

The current implementation patches global functions, which affects all threads. For thread-local blocking, future work could use `threading.local()` to store per-thread state.

### Async Compatibility

`asyncio.sleep` is handled by wrapping the coroutine function. The wrapper checks permissions before delegating to the original coroutine.

## Alternatives Considered

### Alternative 1: Time Mocking (freezegun/time-machine)

**Approach**: Use libraries like `freezegun` or `time-machine` to mock time instead of blocking sleep.

**Pros**:
- Tests can "sleep" without waiting
- Useful for testing time-dependent logic

**Cons**:
- Doesn't prevent bad patterns (tests still use sleep)
- Requires explicit integration with mocking library
- Not all sleep uses are about testing time logic

**Verdict**: Complementary approach, but doesn't solve the core problem of encouraging proper synchronization.

### Alternative 2: Import Hook Blocking

**Approach**: Use import hooks to prevent importing `time` module.

**Pros**:
- Catches usage at module level

**Cons**:
- Too coarse-grained (blocks `time.time()`, `time.perf_counter()`)
- Breaks legitimate time-related code
- Can't allow sleep in some tests but not others

**Verdict**: Rejected - too restrictive.

### Alternative 3: AST Analysis

**Approach**: Analyze test code AST to detect sleep calls statically.

**Pros**:
- No runtime overhead
- Catches issues before tests run

**Cons**:
- Complex to implement
- Misses dynamic calls (`getattr(time, 'sleep')(1)`)
- Can't distinguish test code from helper code

**Verdict**: Rejected - too complex, incomplete coverage.

## References

- [Google's Software Engineering at Google - Testing](https://abseil.io/resources/swe-book/html/ch11.html)
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/) - Ports and adapters pattern
- [pytest-test-categories Network Isolation](./adr-001-network-isolation.md) - Similar pattern for network blocking
