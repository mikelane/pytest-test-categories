# Hexagonal Architecture

pytest-test-categories follows the **Hexagonal Architecture** pattern (also known as Ports and Adapters). This document explains how the pattern is applied and why it matters for testability.

## What is Hexagonal Architecture?

Hexagonal Architecture, introduced by Alistair Cockburn, separates an application into three layers:

```
                     ┌───────────────────────────────────────┐
                     │           Application Core            │
                     │         (Business Logic)              │
                     │                                       │
    ┌────────┐       │  ┌─────────────────────────────┐     │       ┌────────┐
    │External│◄──────┼──┤         Port              ├─────┼──────►│External│
    │ System │       │  │      (Interface)          │     │       │ System │
    │(Input) │───────┼──►                           ◄─────┼───────│(Output)│
    └────────┘       │  └─────────────────────────────┘     │       └────────┘
                     │              ▲                       │
                     │              │                       │
                     │       ┌──────┴──────┐               │
                     │       │   Adapter   │               │
                     │       │(Implementation)             │
                     │       └─────────────┘               │
                     └───────────────────────────────────────┘
```

The key concepts:

1. **Ports**: Abstract interfaces that define how the core interacts with the outside world
2. **Adapters**: Concrete implementations of ports for specific technologies
3. **Core**: Business logic that depends only on ports, never on adapters

## Why Use Hexagonal Architecture?

### Testability

The primary benefit is testability. Consider testing a timer that measures test duration:

**Without Hexagonal Architecture:**
```python
class Timer:
    def start(self):
        self._start_time = time.perf_counter()

    def stop(self):
        self._end_time = time.perf_counter()

    def duration(self):
        return self._end_time - self._start_time

# Test is slow and flaky
def test_timer_measures_duration():
    timer = Timer()
    timer.start()
    time.sleep(0.1)  # Slow! And might be 0.09s or 0.11s
    timer.stop()
    assert 0.09 < timer.duration() < 0.12  # Imprecise assertion
```

**With Hexagonal Architecture:**
```python
# Port (interface)
class TestTimer(ABC):
    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def duration(self) -> float: ...

# Test adapter - controllable time
class FakeTimer(TestTimer):
    def __init__(self):
        self._current_time = 0.0
        self._start_time = None
        self._end_time = None

    def advance(self, seconds: float):
        self._current_time += seconds

    def start(self):
        self._start_time = self._current_time

    def stop(self):
        self._end_time = self._current_time

    def duration(self):
        return self._end_time - self._start_time

# Test is fast and deterministic
def test_timer_measures_duration():
    timer = FakeTimer()
    timer.start()
    timer.advance(0.1)  # Instant! Exactly 0.1s
    timer.stop()
    assert timer.duration() == 0.1  # Precise assertion
```

### Separation of Concerns

The pattern enforces clean separation:

- **Business logic** knows nothing about pytest, sockets, or filesystems
- **Adapters** handle all technology-specific details
- **Ports** define the contract between them

This makes the codebase easier to understand and maintain.

## Ports in pytest-test-categories

The codebase defines several ports in `src/pytest_test_categories/types.py` and `src/pytest_test_categories/ports/`:

### TestTimer Port

The foundational example of hexagonal architecture in the codebase:

```python
# From src/pytest_test_categories/types.py

class TimerState(StrEnum):
    """Represents the possible states of a timer."""
    READY = 'ready'
    RUNNING = 'running'
    STOPPED = 'stopped'

class TestTimer(BaseModel, ABC):
    """Abstract base class defining the timer interface."""

    state: TimerState = TimerState.READY

    @require(lambda self: self.state == TimerState.READY,
             'Timer must be in READY state to start')
    @ensure(lambda self: self.state == TimerState.RUNNING,
            'Timer must be in RUNNING state after starting')
    def start(self) -> None:
        """Start timing a test."""
        self.state = TimerState.RUNNING

    @require(lambda self: self.state == TimerState.RUNNING,
             'Timer must be in RUNNING state to stop')
    @ensure(lambda self: self.state == TimerState.STOPPED,
            'Timer must be in STOPPED state after stopping')
    def stop(self) -> None:
        """Stop timing a test."""
        self.state = TimerState.STOPPED

    @require(lambda self: self.state == TimerState.STOPPED,
             'Timer must be in STOPPED state to get duration')
    @ensure(lambda result: result > 0, 'Duration must be positive')
    @abstractmethod
    def duration(self) -> float:
        """Get the duration of the test in seconds."""
```

Key features:
- **State machine**: `READY -> RUNNING -> STOPPED`
- **Design by contract**: `icontract` decorators enforce state transitions
- **Abstract method**: `duration()` must be implemented by adapters

### NetworkBlockerPort

Blocks network access for hermetic tests:

```python
# From src/pytest_test_categories/ports/network.py

class NetworkBlockerPort(ABC):
    """Port defining network blocking behavior."""

    @abstractmethod
    def activate(self, test_size: TestSize, enforcement_mode: EnforcementMode) -> None:
        """Activate network blocking for a test."""

    @abstractmethod
    def deactivate(self) -> None:
        """Deactivate network blocking, restoring normal socket behavior."""

    @abstractmethod
    def check_connection_allowed(self, host: str, port: int) -> bool:
        """Check if a connection to host:port is allowed."""

    @abstractmethod
    def on_violation(self, host: str, port: int, test_nodeid: str) -> None:
        """Handle a network access violation."""
```

### Other Ports

The codebase also defines:

| Port | Purpose | Location |
|------|---------|----------|
| `TestItemPort` | Abstract pytest.Item | `types.py` |
| `OutputWriterPort` | Terminal output | `types.py` |
| `WarningSystemPort` | Warning emission | `types.py` |
| `ConfigStatePort` | Plugin state access | `types.py` |
| `FilesystemBlockerPort` | Filesystem access control | `ports/filesystem.py` |
| `ProcessBlockerPort` | Subprocess blocking | `ports/process.py` |
| `DatabaseBlockerPort` | Database connection blocking | `ports/database.py` |
| `SleepBlockerPort` | Sleep call blocking | `ports/sleep.py` |

## Adapters in pytest-test-categories

Each port has at least two adapters: one for production and one for testing.

### Timer Adapters

Located in `src/pytest_test_categories/timers.py`:

```python
class WallTimer(TestTimer):
    """Production adapter using wall clock time.

    Uses time.perf_counter() for high-resolution timing.
    """

    start_time: float | None = None
    end_time: float | None = None

    def start(self) -> None:
        super().start()  # State machine check
        self.start_time = time.perf_counter()

    def stop(self) -> None:
        self.end_time = time.perf_counter()
        super().stop()  # State machine check

    def duration(self) -> float:
        return self.end_time - self.start_time


class FakeTimer(TestTimer):
    """Test adapter with controllable time.

    Allows explicit time advancement for deterministic testing.
    """

    current_time: float = 0.0
    start_time: float | None = None
    end_time: float | None = None

    def advance(self, seconds: float) -> None:
        """Advance the simulated clock."""
        self.current_time += seconds

    def start(self) -> None:
        super().start()
        self.start_time = self.current_time

    def stop(self) -> None:
        self.end_time = self.current_time
        super().stop()

    def duration(self) -> float:
        return self.end_time - self.start_time
```

### Network Blocker Adapters

Located in `src/pytest_test_categories/adapters/network.py`:

```python
class SocketPatchingNetworkBlocker(NetworkBlockerPort):
    """Production adapter that patches socket.socket.

    Intercepts socket.connect() calls and blocks based on test size.
    """

    def activate(self, test_size: TestSize, enforcement_mode: EnforcementMode) -> None:
        # Store original socket class
        self._original_socket = socket.socket
        # Replace with guarded version
        socket.socket = self._create_guarded_socket()

    def deactivate(self) -> None:
        # Restore original
        socket.socket = self._original_socket


class FakeNetworkBlocker(NetworkBlockerPort):
    """Test adapter that records connection attempts.

    Does not patch sockets - just tracks calls for verification.
    """

    connection_attempts: list[tuple[str, int]] = []

    def check_connection_allowed(self, host: str, port: int) -> bool:
        self.connection_attempts.append((host, port))
        return self._should_allow(host, port)
```

### Adapter Summary

| Port | Production Adapter | Test Adapter |
|------|-------------------|--------------|
| `TestTimer` | `WallTimer` | `FakeTimer` |
| `NetworkBlockerPort` | `SocketPatchingNetworkBlocker` | `FakeNetworkBlocker` |
| `FilesystemBlockerPort` | `FilesystemPatchingBlocker` | `FakeFilesystemBlocker` |
| `ProcessBlockerPort` | `SubprocessPatchingBlocker` | `FakeProcessBlocker` |
| `DatabaseBlockerPort` | `DatabasePatchingBlocker` | `FakeDatabaseBlocker` |
| `SleepBlockerPort` | `SleepPatchingBlocker` | `FakeSleepBlocker` |
| `TestItemPort` | `PytestItemAdapter` | `FakeTestItem` |
| `OutputWriterPort` | `TerminalReporterAdapter` | `StringBufferWriter` |
| `WarningSystemPort` | `PytestWarningAdapter` | `FakeWarningSystem` |

## Dependency Injection

The plugin uses dependency injection to select adapters at runtime.

### Timer Factory Pattern

The `PluginState` class holds a timer factory:

```python
# From src/pytest_test_categories/types.py

class PluginState(BaseModel):
    """Plugin state for a test session."""

    # Timer factory for dependency injection
    timer_factory: type[TestTimer] | None = None

    def __init__(self, **data):
        super().__init__(**data)
        # Default to production adapter
        if self.timer_factory is None:
            from pytest_test_categories.timers import WallTimer
            self.timer_factory = WallTimer
```

### Injecting Test Doubles

Tests can inject `FakeTimer`:

```python
# In a test file
from pytest_test_categories.timers import FakeTimer
from pytest_test_categories.types import PluginState

def test_timing_enforcement():
    state = PluginState(timer_factory=FakeTimer)
    timer = state.timer_factory()

    timer.start()
    timer.advance(2.0)  # Simulate 2 seconds
    timer.stop()

    assert timer.duration() == 2.0  # Exact, deterministic
```

### Blocker Factory Pattern

Similar patterns exist for blockers:

```python
# Production code
state = PluginState(
    network_blocker=SocketPatchingNetworkBlocker(),
    filesystem_blocker=FilesystemPatchingBlocker(),
    process_blocker=SubprocessPatchingBlocker(),
)

# Test code
state = PluginState(
    network_blocker=FakeNetworkBlocker(),
    filesystem_blocker=FakeFilesystemBlocker(),
    process_blocker=FakeProcessBlocker(),
)
```

## Code Organization

The hexagonal architecture is reflected in the directory structure:

```
src/pytest_test_categories/
├── types.py              # Core domain types + abstract ports
├── ports/                # Additional port definitions
│   ├── network.py        # NetworkBlockerPort
│   ├── filesystem.py     # FilesystemBlockerPort
│   ├── process.py        # ProcessBlockerPort
│   ├── database.py       # DatabaseBlockerPort
│   └── sleep.py          # SleepBlockerPort
├── adapters/             # Concrete implementations
│   ├── pytest_adapter.py # Pytest integration adapters
│   ├── network.py        # Network blocking adapters
│   ├── filesystem.py     # Filesystem blocking adapters
│   ├── process.py        # Process blocking adapters
│   ├── database.py       # Database blocking adapters
│   └── sleep.py          # Sleep blocking adapters
├── timers.py             # Timer adapters (WallTimer, FakeTimer)
├── services/             # Business logic services
│   ├── test_discovery.py
│   ├── timing_validation.py
│   └── distribution_validation.py
└── plugin.py             # Pytest hook orchestration
```

## The Plugin as Orchestrator

The `plugin.py` file is deliberately thin. It:

1. Registers pytest hooks
2. Creates adapters based on configuration
3. Delegates to services through ports

```python
# Simplified from src/pytest_test_categories/plugin.py

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item: pytest.Item) -> Generator[None, None, None]:
    """Wrap test execution with resource blocking."""
    state = get_plugin_state(item.config)
    test_size = get_test_size(item)

    # Activate all blockers through their ports
    with ExitStack() as stack:
        if should_block(test_size, state.enforcement_mode):
            stack.callback(state.network_blocker.deactivate)
            state.network_blocker.activate(test_size, state.enforcement_mode)

            stack.callback(state.filesystem_blocker.deactivate)
            state.filesystem_blocker.activate(test_size, state.enforcement_mode)

            # ... other blockers

        yield  # Run the test
```

The plugin knows nothing about sockets, files, or time - it just orchestrates ports.

## Benefits Realized

### 1. Fast Unit Tests

All plugin logic can be tested with fake adapters:

```python
# tests/test_timing_enforcement.py

@pytest.mark.small
def test_timing_violation_detected():
    timer = FakeTimer()
    timer.start()
    timer.advance(1.5)  # Exceed 1s limit
    timer.stop()

    # Test the validation logic, not the clock
    with pytest.raises(TimingViolationError):
        validate_timing(timer, TestSize.SMALL)
```

### 2. Integration Tests for Real Behavior

Real adapters are tested separately:

```python
# tests/it_wall_timer_integration.py

@pytest.mark.medium  # Uses real time
def test_wall_timer_measures_real_time():
    timer = WallTimer()
    timer.start()
    time.sleep(0.1)
    timer.stop()

    # Lenient assertion for real timing
    assert 0.08 < timer.duration() < 0.15
```

### 3. Easy Extension

Adding new isolation types follows the same pattern:

1. Define a new port interface
2. Implement production adapter (with patching)
3. Implement test adapter (with recording)
4. Wire into plugin orchestration

Each ADR (001-005) documents this process for network, filesystem, process, database, and sleep isolation.

## Further Reading

- [Alistair Cockburn's Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- [ADR-001: Network Isolation](adr-001-network-isolation.md) - First isolation mechanism
- [ADR-002: Filesystem Isolation](adr-002-filesystem-isolation.md) - Extends the pattern
- [ADR-003: Process Isolation](adr-003-process-isolation.md) - Subprocess blocking
- [ADR-004: Database Isolation](adr-004-database-isolation.md) - Database connection blocking
- [ADR-005: Sleep Isolation](adr-005-sleep-isolation.md) - Sleep call blocking
