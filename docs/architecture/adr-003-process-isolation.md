# ADR-003: Process Isolation Mechanism for Small Tests

## Status

**Implemented** (v0.7.0)

> **Implementation Complete**: All components are fully implemented and production-ready:
> - `ProcessBlockerPort` interface with state machine
> - `SubprocessPatchingBlocker` production adapter
> - `FakeProcessBlocker` test adapter
> - `SubprocessViolationError` exception with remediation guidance
> - Pytest hook integration with enforcement modes

### No Override Markers - By Design

This plugin intentionally provides **no per-test override markers** (e.g., `@pytest.mark.allow_subprocess`).
This is a deliberate architectural decision, not a missing feature.

**Rationale:**
- Small tests must be hermetic and single-process. Period. No escape hatches.
- If a test needs to spawn subprocesses, it should be `@pytest.mark.medium`, not a small test with an exception.
- Override markers would undermine the entire philosophy and make enforcement meaningless.
- The correct remediation is to mock subprocess calls or upgrade the test category.

**If you need subprocess access in a test, change `@pytest.mark.small` to `@pytest.mark.medium`.**

## Context

Small tests, as defined by Google's "Software Engineering at Google" best practices, must be **hermetic** and run in a **single process**. Subprocess spawning in small tests creates several problems:

- **Non-determinism**: External processes have their own state and behavior
- **I/O overhead**: Process creation involves system calls and resource allocation
- **Timing variability**: Process startup times vary, causing flaky tests
- **Resource leakage**: Spawned processes may outlive tests if not properly cleaned up
- **Environment coupling**: Subprocesses inherit environment variables and may behave differently across systems

Currently, pytest-test-categories enforces timing constraints (v0.1.0), network isolation (v0.4.0), and filesystem isolation (v0.5.0). However, a test can still spawn subprocesses, violating the single-process constraint for small tests.

We need a mechanism to:

1. Detect subprocess spawn attempts during small test execution
2. Block spawns and provide clear error messages
3. Allow spawns for medium/large/xlarge tests where subprocess use is appropriate

### Existing Architecture Context

The plugin follows **hexagonal architecture** (ports and adapters):

- **Ports**: Abstract interfaces defining contracts (`TestTimer`, `NetworkBlockerPort`, `FilesystemBlockerPort`)
- **Production Adapters**: Real implementations (`WallTimer`, `SocketPatchingNetworkBlocker`, `FilesystemPatchingBlocker`)
- **Test Adapters**: Controllable test doubles (`FakeTimer`, `FakeNetworkBlocker`, `FakeFilesystemBlocker`)

This pattern enables:
- Unit tests to be fast and deterministic (using fake adapters)
- Integration tests to validate real behavior (using production adapters)
- Easy extensibility for new resource types

The network isolation (ADR-001) and filesystem isolation (ADR-002) established patterns we follow:
- Port interface with state machine (INACTIVE -> ACTIVE -> INACTIVE)
- Design-by-contract with icontract preconditions/postconditions
- Pydantic models for configuration and data transfer
- Clear exception hierarchy with actionable error messages

### Research: Subprocess Entry Points in Python

Python provides multiple ways to spawn processes:

**subprocess Module (Primary)**:
- `subprocess.Popen` - Base class for all subprocess operations
- `subprocess.run` - High-level convenience function (Python 3.5+)
- `subprocess.call` - Run command, return exit code
- `subprocess.check_call` - Run command, raise on non-zero exit
- `subprocess.check_output` - Run command, return stdout

**os Module**:
- `os.system` - Run command in shell, return exit code
- `os.popen` - Open pipe to/from command (deprecated but still used)
- `os.spawn*` family - Low-level process spawning (spawnl, spawnle, spawnlp, etc.)
- `os.exec*` family - Replace current process (execl, execle, execlp, etc.)

**multiprocessing Module**:
- `multiprocessing.Process` - Spawn new Python interpreter process

### Research: Interception Strategy

We can intercept subprocess spawning at multiple levels:

1. **subprocess.Popen**: Base class - all convenience functions use this
2. **Convenience functions**: Direct patching of run, call, check_call, check_output
3. **os functions**: Patch os.system, os.popen
4. **multiprocessing**: Patch Process.start()

Note: The `os.spawn*` and `os.exec*` families are rarely used in modern Python code and are not intercepted in the initial implementation. They can be added if needed based on user feedback.

## Decision

We will implement process isolation using a **subprocess patching approach** following the hexagonal architecture pattern established in ADR-001 and ADR-002.

### 1. Port Interface: `ProcessBlockerPort`

Define an abstract interface for process blocking:

```python
class ProcessBlockerPort(BaseModel, ABC):
    """Port defining process blocking behavior.

    Implementations control whether subprocess spawning is permitted during
    test execution. The port follows a state machine pattern:
    INACTIVE -> ACTIVE -> INACTIVE

    This mirrors the NetworkBlockerPort and FilesystemBlockerPort patterns.

    Attributes:
        state: Current blocker state (INACTIVE or ACTIVE).

    """

    state: BlockerState = BlockerState.INACTIVE

    @require(lambda self: self.state == BlockerState.INACTIVE, 'Blocker must be INACTIVE to activate')
    @ensure(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE after activation')
    def activate(self, test_size: TestSize, enforcement_mode: EnforcementMode) -> None:
        """Activate process blocking for a test."""

    @require(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE to deactivate')
    @ensure(lambda self: self.state == BlockerState.INACTIVE, 'Blocker must be INACTIVE after deactivation')
    def deactivate(self) -> None:
        """Deactivate process blocking, restoring normal behavior."""

    @require(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE to check spawns')
    def check_spawn_allowed(self, command: str, args: tuple[str, ...]) -> bool:
        """Check if a process spawn is allowed."""

    @require(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE to handle violations')
    def on_violation(
        self,
        command: str,
        args: tuple[str, ...],
        test_nodeid: str,
        method: str,
    ) -> None:
        """Handle a subprocess spawn violation."""
```

### 2. Spawn Attempt Record

```python
class SpawnAttempt(BaseModel, frozen=True):
    """Immutable record of a subprocess spawn attempt.

    Attributes:
        command: The command or executable.
        args: Arguments to the command.
        test_nodeid: The pytest node ID of the test.
        allowed: Whether the spawn was permitted.
        method: The method used (e.g., 'subprocess.run').

    """

    command: str
    args: tuple[str, ...]
    test_nodeid: str
    allowed: bool
    method: str
```

### 3. Production Adapter: `SubprocessPatchingBlocker`

Implements `ProcessBlockerPort` by:

1. **Patching Strategy** - Patch at commonly used entry points:
   - `subprocess.Popen` - Intercepts base class
   - `subprocess.run`, `call`, `check_call`, `check_output` - Convenience functions
   - `os.system`, `os.popen` - Legacy OS-level spawning
   - `multiprocessing.Process` - Python multiprocessing

2. **Command Extraction** - Handle various input formats:
   - List/tuple: `['python', 'script.py']` -> command='python', args=('script.py',)
   - String: `'python script.py'` -> command='python script.py', args=()

3. **Violation Handling**:
   - STRICT mode: Raise `SubprocessViolationError`
   - WARN mode: Log warning, allow spawn
   - OFF mode: No enforcement

```python
class SubprocessPatchingBlocker(ProcessBlockerPort):
    """Production adapter that patches subprocess/os to block process spawning.

    This adapter intercepts process spawning by patching:
    - subprocess.Popen and convenience functions
    - os.system, os.popen
    - multiprocessing.Process

    The patching is reversible - deactivate() restores originals.

    """
```

### 4. Test Adapter: `FakeProcessBlocker`

Provides controllable test double:

```python
class FakeProcessBlocker(ProcessBlockerPort):
    """Test double for process blocking without actual patching.

    Tracks all method calls and spawn attempts for verification.

    Attributes:
        spawn_attempts: List of recorded spawn attempts.
        warnings: List of warning messages (WARN mode).
        activate_count: Number of activate() calls.
        deactivate_count: Number of deactivate() calls.
        check_count: Number of check_spawn_allowed() calls.

    """
```

### 5. Exception Class

```python
class SubprocessViolationError(HermeticityViolationError):
    """Raised when a test attempts to spawn a subprocess.

    Attributes:
        command: The command that was attempted.
        command_args: The arguments passed to the command.
        method: The spawn method used (e.g., 'subprocess.run').

    """
```

### 6. Integration Points

The process blocker integrates via pytest hooks:

1. **`pytest_configure`**: Create blocker instance, store in plugin state
2. **`pytest_runtest_call`** (wrapper): Activate blocking before test, deactivate after
3. **`pytest_runtest_teardown`**: Ensure blocking is deactivated
4. **`pytest_terminal_summary`**: Report subprocess violation statistics

### 7. Error Message Format

Violation errors provide actionable guidance:

```
============================================================
HermeticityViolationError
============================================================
Test: test_run_external_command (tests/test_cli.py:42)
Category: SMALL
Violation: Subprocess spawn attempted

Details:
  Attempted subprocess.run: python script.py --verbose

Small tests have restricted resource access. Options:
  1. Mock subprocess.run using pytest-mock (mocker.patch)
  2. Use dependency injection to provide a fake command executor
  3. Test the logic that prepares subprocess arguments, not the spawn itself
  4. Change test category to @pytest.mark.medium (if subprocess is required)

Documentation: See docs/architecture/adr-003-process-isolation.md
============================================================
```

## Consequences

### Benefits

1. **Consistent Architecture**: Follows established hexagonal architecture pattern from ADR-001/002
2. **Testability**: Fake adapter enables fast, deterministic unit tests
3. **Gradual Adoption**: Warn mode allows incremental enforcement
4. **Clear Feedback**: Actionable error messages guide developers
5. **Comprehensive Coverage**: Intercepts most common subprocess entry points
6. **Single-Process Enforcement**: Ensures small tests run in isolation

### Trade-offs

1. **Incomplete Coverage**: `os.spawn*` and `os.exec*` families not initially intercepted
2. **Global Patching**: Subprocess patching affects entire process during test
3. **Performance Overhead**: Minor overhead from spawn interception (negligible)
4. **Complexity**: Adds to configuration surface area

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Incomplete patching | Start with common operations, add more based on feedback |
| pytest-xdist compatibility | Each worker has separate interpreter, patching is per-worker |
| Complex command parsing | Handle string and list inputs gracefully |
| Multiprocessing edge cases | Intercept at Process.start(), not __init__ |

## Alternatives Considered

### Alternative 1: Import Hook Blocking

**Approach**: Use import hooks to prevent importing subprocess module.

**Pros**:
- Catches subprocess usage at module level
- No runtime overhead during test execution

**Cons**:
- Too coarse-grained (blocks all use, not test-specific)
- subprocess often imported before test runs
- Breaks test fixtures that legitimately need subprocess

**Verdict**: Rejected - too inflexible for test-specific enforcement.

### Alternative 2: Process Namespace Isolation (Linux)

**Approach**: Run tests in isolated PID namespaces.

**Pros**:
- True kernel-level isolation
- Cannot be bypassed

**Cons**:
- Linux-only
- Requires root or CAP_SYS_ADMIN
- Significant performance overhead
- Complex setup

**Verdict**: Rejected - platform-specific and heavy-weight.

### Alternative 3: Seccomp-based Blocking (Linux)

**Approach**: Use seccomp to block fork/exec syscalls.

**Pros**:
- Kernel-level enforcement
- Cannot be bypassed from Python

**Cons**:
- Linux-only
- Requires privileged operations
- Complex to configure correctly
- May affect pytest internals

**Verdict**: Rejected - platform-specific and too low-level.

## Implementation Notes

### Intercepted Entry Points

The following entry points are intercepted:

- `subprocess.Popen` (class replacement)
- `subprocess.run` (function wrapper)
- `subprocess.call` (function wrapper)
- `subprocess.check_call` (function wrapper)
- `subprocess.check_output` (function wrapper)
- `os.system` (function wrapper)
- `os.popen` (function wrapper)
- `multiprocessing.Process` (class replacement)

### Not Intercepted (Future Work)

The following are not intercepted in the initial implementation:

- `os.spawn*` family (spawnl, spawnle, spawnlp, spawnlpe, spawnv, spawnve, spawnvp, spawnvpe)
- `os.exec*` family (execl, execle, execlp, execlpe, execv, execve, execvp, execvpe)

These are rarely used in modern Python code. They can be added based on user feedback.

### Thread Safety Considerations

For pytest-xdist parallel execution:

- Each worker process has its own Python interpreter
- Global patching affects only that worker's process
- Blocker state is stored in plugin state, which is per-worker

No special thread safety measures needed beyond standard pytest-xdist patterns.

## Test Strategy

### Unit Tests (Small, using FakeProcessBlocker)
- Port state machine transitions
- Command/args extraction
- Spawn permission rules
- Exception message formatting
- Warning recording

### Integration Tests (Medium, using SubprocessPatchingBlocker)
- Actual subprocess interception
- subprocess.run, call, check_call, check_output blocking
- os.system, os.popen blocking
- multiprocessing.Process blocking
- Function restoration on deactivate

### End-to-End Tests (Medium, using pytester)
- Full test execution with enforcement
- CLI option handling
- Violation reporting in terminal

## References

- [Google's Software Engineering at Google - Testing](https://abseil.io/resources/swe-book/html/ch11.html)
- [ADR-001: Network Isolation](adr-001-network-isolation.md) - Established patterns
- [ADR-002: Filesystem Isolation](adr-002-filesystem-isolation.md) - Established patterns
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/) - Ports and adapters pattern
- [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html)
