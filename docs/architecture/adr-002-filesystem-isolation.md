# ADR-002: Filesystem Isolation Mechanism for Small Tests

## Status

Proposed

> **Implementation Progress**: This ADR documents the design for filesystem isolation.
> Implementation will follow in Issue #92 (port interface), Issue #93 (adapters),
> and Issue #94 (pytest integration). Track progress in Epic #34.

## Context

Small tests, as defined by Google's "Software Engineering at Google" best practices, must be **hermetic** - they should run entirely in memory with no external dependencies. Filesystem access in small tests creates several problems:

- **Side effects**: Tests that write files can affect other tests running in parallel
- **State leakage**: Files created by one test may be read by another, causing non-deterministic behavior
- **Race conditions**: Parallel test execution with filesystem access leads to flaky tests
- **Non-hermeticity**: Tests depend on filesystem state rather than being self-contained
- **Slow execution**: Disk I/O is orders of magnitude slower than memory operations

Currently, pytest-test-categories enforces timing constraints and network isolation (v0.4.0). However, a test can still access the filesystem, creating tests that are not truly hermetic.

We need a mechanism to:

1. Detect filesystem access attempts during small test execution
2. Allow access to safe paths (temp directories, pytest fixtures)
3. Block or warn about other access based on configuration
4. Provide clear error messages with remediation guidance

### Existing Architecture Context

The plugin follows **hexagonal architecture** (ports and adapters):

- **Ports**: Abstract interfaces defining contracts (`TestTimer`, `NetworkBlockerPort`, etc.)
- **Production Adapters**: Real implementations (`WallTimer`, `SocketPatchingNetworkBlocker`)
- **Test Adapters**: Controllable test doubles (`FakeTimer`, `FakeNetworkBlocker`)

This pattern enables:
- Unit tests to be fast and deterministic (using fake adapters)
- Integration tests to validate real behavior (using production adapters)
- Easy extensibility for new resource types

The network isolation implementation (ADR-001) established patterns we will follow:
- Port interface with state machine (INACTIVE -> ACTIVE -> INACTIVE)
- Design-by-contract with icontract preconditions/postconditions
- Pydantic models for configuration and data transfer
- Clear exception hierarchy with actionable error messages

### Research: Filesystem Operation Categories

Python provides multiple ways to access the filesystem:

**Built-in Functions:**
- `open()` - Primary file open function
- `exec()`, `execfile()` - Execute files

**os Module:**
- `os.open()`, `os.read()`, `os.write()`, `os.close()` - Low-level file operations
- `os.mkdir()`, `os.makedirs()`, `os.rmdir()`, `os.removedirs()` - Directory operations
- `os.remove()`, `os.unlink()` - File deletion
- `os.rename()`, `os.replace()` - File renaming
- `os.link()`, `os.symlink()`, `os.readlink()` - Link operations
- `os.stat()`, `os.lstat()`, `os.access()` - File metadata
- `os.listdir()`, `os.scandir()` - Directory listing
- `os.getcwd()`, `os.chdir()` - Working directory (read-only is safe)
- `os.chmod()`, `os.chown()` - Permission changes

**pathlib Module:**
- `Path.open()` - Open file
- `Path.read_text()`, `Path.read_bytes()` - Read operations
- `Path.write_text()`, `Path.write_bytes()` - Write operations
- `Path.mkdir()`, `Path.rmdir()`, `Path.unlink()` - Directory/file operations
- `Path.touch()`, `Path.chmod()` - File modification
- `Path.rename()`, `Path.replace()` - Renaming
- `Path.symlink_to()`, `Path.hardlink_to()` - Links
- `Path.stat()`, `Path.exists()`, `Path.is_file()`, `Path.is_dir()` - Metadata (mostly read-only)

**shutil Module:**
- `shutil.copy()`, `shutil.copy2()`, `shutil.copytree()` - Copy operations
- `shutil.move()` - Move operations
- `shutil.rmtree()` - Recursive delete

**tempfile Module:**
- `tempfile.TemporaryFile()`, `tempfile.NamedTemporaryFile()` - Temp files
- `tempfile.mkdtemp()`, `tempfile.mkstemp()` - Create temp directories/files

**io Module:**
- `io.open()` - Alias for built-in open
- `io.FileIO` - Low-level file I/O

### Research: Allowed Paths for Small Tests

Certain paths should be allowed even for small tests:

1. **pytest's tmp_path fixture**: Provided by pytest, isolated per-test
2. **pytest's tmp_path_factory**: Session-scoped temp directories
3. **System temp directory**: `tempfile.gettempdir()` and subdirectories
4. **Package resources**: `importlib.resources` for reading bundled data
5. **User-configured paths**: Custom allowlist via configuration

### Research: Existing Solutions

**pyfakefs** provides filesystem isolation through:
- Patching all filesystem modules (`os`, `pathlib`, `io`, `open`, `shutil`, etc.)
- Providing a fake in-memory filesystem
- Supporting allowlisted paths that pass through to real filesystem

Key insights from pyfakefs:
1. Comprehensive patching is required (many entry points)
2. Allow-listing is essential for pytest fixtures
3. Real filesystem access must remain available for specific paths
4. Module patching order matters (patch before imports in test code)

## Decision

We will implement filesystem isolation using a **comprehensive patching approach** following the hexagonal architecture pattern established in ADR-001.

### 1. Port Interface: `FilesystemBlockerPort`

Define an abstract interface for filesystem blocking:

```python
class FilesystemBlockerPort(BaseModel, ABC):
    """Port defining filesystem blocking behavior.

    Implementations control whether filesystem access is permitted during
    test execution. The port follows a state machine pattern:
    INACTIVE -> ACTIVE -> INACTIVE

    This mirrors the NetworkBlockerPort pattern for consistency.

    Attributes:
        state: Current blocker state (INACTIVE or ACTIVE).

    """

    state: BlockerState = BlockerState.INACTIVE

    @require(lambda self: self.state == BlockerState.INACTIVE, 'Blocker must be INACTIVE to activate')
    @ensure(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE after activation')
    def activate(
        self,
        test_size: TestSize,
        enforcement_mode: EnforcementMode,
        allowed_paths: frozenset[Path],
    ) -> None:
        """Activate filesystem blocking for a test.

        Args:
            test_size: The size category of the current test.
            enforcement_mode: Whether to raise or warn on violations.
            allowed_paths: Paths that are always allowed (e.g., tmp_path).

        """

    @abstractmethod
    def _do_activate(
        self,
        test_size: TestSize,
        enforcement_mode: EnforcementMode,
        allowed_paths: frozenset[Path],
    ) -> None:
        """Perform adapter-specific activation logic."""

    @require(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE to deactivate')
    @ensure(lambda self: self.state == BlockerState.INACTIVE, 'Blocker must be INACTIVE after deactivation')
    def deactivate(self) -> None:
        """Deactivate filesystem blocking, restoring normal behavior."""

    @abstractmethod
    def _do_deactivate(self) -> None:
        """Perform adapter-specific deactivation logic."""

    @require(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE to check access')
    def check_access_allowed(self, path: Path, operation: FilesystemOperation) -> bool:
        """Check if a filesystem operation on path is allowed.

        Args:
            path: The target path (resolved to absolute).
            operation: The type of operation (READ, WRITE, DELETE, etc.).

        Returns:
            True if the operation is allowed, False otherwise.

        """

    @abstractmethod
    def _do_check_access_allowed(self, path: Path, operation: FilesystemOperation) -> bool:
        """Determine if filesystem access is allowed."""

    @require(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE to handle violations')
    def on_violation(
        self,
        path: Path,
        operation: FilesystemOperation,
        test_nodeid: str,
    ) -> None:
        """Handle a filesystem access violation.

        Args:
            path: The attempted path.
            operation: The attempted operation type.
            test_nodeid: The pytest node ID of the violating test.

        Raises:
            FilesystemAccessViolationError: If enforcement mode is STRICT.

        """

    @abstractmethod
    def _do_on_violation(
        self,
        path: Path,
        operation: FilesystemOperation,
        test_nodeid: str,
    ) -> None:
        """Handle violations according to enforcement mode."""

    def reset(self) -> None:
        """Reset blocker to initial INACTIVE state."""
```

### 2. Filesystem Operation Enum

```python
class FilesystemOperation(StrEnum):
    """Categories of filesystem operations for access control.

    Different test sizes may allow different operation types:
    - SMALL: No operations allowed (except on allowed paths)
    - MEDIUM: All operations allowed
    - LARGE/XLARGE: All operations allowed

    """

    READ = 'read'           # open() for reading, Path.read_text(), etc.
    WRITE = 'write'         # open() for writing, Path.write_text(), etc.
    DELETE = 'delete'       # os.remove(), Path.unlink(), shutil.rmtree()
    CREATE = 'create'       # mkdir(), touch(), open() with 'x' mode
    MODIFY = 'modify'       # chmod(), chown(), rename()
    STAT = 'stat'           # stat(), exists(), is_file() - may be allowed for path resolution
    LIST = 'list'           # listdir(), scandir(), iterdir()
```

### 3. Access Attempt Record

```python
class FilesystemAccessAttempt(BaseModel, frozen=True):
    """Immutable record of a filesystem access attempt.

    Used for tracking and reporting access attempts during test execution.

    Attributes:
        path: The target path (resolved to absolute).
        operation: The type of filesystem operation.
        test_nodeid: The pytest node ID of the test.
        allowed: Whether the access was permitted.

    """

    path: Path
    operation: FilesystemOperation
    test_nodeid: str
    allowed: bool
```

### 4. Production Adapter: `FilesystemPatchingBlocker`

Implements `FilesystemBlockerPort` by:

1. **Patching Strategy** - Patch at the lowest practical level:
   - `builtins.open` - Intercepts all high-level file opens
   - `io.open` - Alias used by some code
   - `os.open` - Low-level file opens
   - `pathlib.Path.open` - pathlib file access
   - `pathlib.Path.read_text`, `Path.read_bytes` - Direct read methods
   - `pathlib.Path.write_text`, `Path.write_bytes` - Direct write methods

2. **Path Resolution** - Before checking permissions:
   - Resolve relative paths to absolute
   - Resolve symlinks to real paths
   - Normalize path (remove `.`, `..`, trailing slashes)
   - Handle both string paths and Path objects

3. **Allowed Path Checking** - Path is allowed if:
   - It is under an allowed path (parent check)
   - It matches a user-configured pattern
   - Operation type is STAT and configured to allow metadata reads

4. **Violation Handling**:
   - STRICT mode: Raise `FilesystemAccessViolationError`
   - WARN mode: Emit warning via pytest, allow operation
   - OFF mode: No enforcement

```python
class FilesystemPatchingBlocker(FilesystemBlockerPort):
    """Production adapter that patches filesystem operations.

    This adapter intercepts filesystem access by patching:
    - builtins.open
    - io.open
    - os.open, os.mkdir, os.remove, etc.
    - pathlib.Path.open, Path.read_text, etc.

    The patching is reversible - deactivate() restores originals.

    Warning:
        This adapter modifies global state. Always use in a try/finally
        block to ensure cleanup.

    """

    current_test_size: TestSize | None = None
    current_enforcement_mode: EnforcementMode | None = None
    current_allowed_paths: frozenset[Path] = frozenset()
    current_test_nodeid: str = ''

    def _do_activate(
        self,
        test_size: TestSize,
        enforcement_mode: EnforcementMode,
        allowed_paths: frozenset[Path],
    ) -> None:
        """Install filesystem wrappers to intercept operations."""
        # Store originals before patching
        # Patch builtins.open, io.open, os.open, pathlib methods
        # Wrappers check _is_path_allowed() before delegating

    def _do_deactivate(self) -> None:
        """Restore original filesystem functions."""

    def _is_path_allowed(self, path: Path, operation: FilesystemOperation) -> bool:
        """Check if path is in allowed set or user allowlist.

        Path resolution:
        1. Convert to Path if string
        2. Resolve to absolute path
        3. Resolve symlinks (handle dangling symlinks gracefully)
        4. Check if path is under any allowed path

        """
```

### 5. Test Adapter: `FakeFilesystemBlocker`

Provides controllable test double:

```python
class FakeFilesystemBlocker(FilesystemBlockerPort):
    """Test double for filesystem blocking without actual patching.

    Tracks all method calls and access attempts for verification.

    Attributes:
        access_attempts: List of recorded access attempts.
        warnings: List of warning messages (WARN mode).
        activate_count: Number of activate() calls.
        deactivate_count: Number of deactivate() calls.

    Example:
        >>> blocker = FakeFilesystemBlocker()
        >>> blocker.activate(TestSize.SMALL, EnforcementMode.STRICT, frozenset())
        >>> blocker.check_access_allowed(Path('/etc/passwd'), FilesystemOperation.READ)
        False

    """

    access_attempts: list[FilesystemAccessAttempt] = Field(default_factory=list)
    # ... similar to FakeNetworkBlocker
```

### 6. Exception Class

```python
class FilesystemAccessViolationError(HermeticityViolationError):
    """Raised when a test makes an unauthorized filesystem access.

    This exception is raised when a test attempts filesystem access
    that violates its size category's restrictions:
    - Small tests: No filesystem access (except allowed paths)
    - Medium/Large/XLarge: All filesystem access allowed

    Attributes:
        path: The attempted path.
        operation: The type of operation attempted.

    """

    def __init__(
        self,
        test_size: TestSize,
        test_nodeid: str,
        path: Path,
        operation: FilesystemOperation,
    ) -> None:
        self.path = path
        self.operation = operation

        remediation = self._get_remediation(test_size, operation)

        super().__init__(
            test_size=test_size,
            test_nodeid=test_nodeid,
            violation_type='Filesystem access attempted',
            details=f'Attempted {operation.value} on: {path}',
            remediation=remediation,
        )

    @staticmethod
    def _get_remediation(test_size: TestSize, operation: FilesystemOperation) -> list[str]:
        """Get remediation suggestions based on test size and operation."""
        if test_size == TestSize.SMALL:
            suggestions = [
                'Use pytest\'s tmp_path fixture for temporary files',
                'Mock file operations using unittest.mock or pyfakefs',
                'Use io.StringIO or io.BytesIO for in-memory file-like objects',
            ]
            if operation in (FilesystemOperation.READ, FilesystemOperation.STAT):
                suggestions.append('Embed test data as Python constants or use importlib.resources')
            suggestions.append('Change test category to @pytest.mark.medium (if filesystem access is required)')
            return suggestions
        return []
```

### 7. Allowed Paths Detection

The plugin automatically detects and allows these paths:

```python
def get_default_allowed_paths(config: pytest.Config) -> frozenset[Path]:
    """Determine default allowed paths for filesystem isolation.

    Returns paths that are always safe to access during tests:
    1. System temp directory (tempfile.gettempdir())
    2. pytest's basetemp directory (--basetemp or default)
    3. User-configured additional paths

    Args:
        config: pytest Config object.

    Returns:
        Frozen set of allowed Path objects.

    """
    allowed: set[Path] = set()

    # System temp directory
    allowed.add(Path(tempfile.gettempdir()).resolve())

    # pytest's basetemp (where tmp_path is created)
    basetemp = config.getoption('basetemp', default=None)
    if basetemp:
        allowed.add(Path(basetemp).resolve())
    else:
        # Default pytest basetemp location
        allowed.add(Path(tempfile.gettempdir()).resolve() / 'pytest-of-{user}')

    # User-configured allowed paths from pytest.ini / pyproject.toml
    configured_paths = config.getini('test_categories_allowed_paths')
    for path_str in configured_paths:
        allowed.add(Path(path_str).expanduser().resolve())

    return frozenset(allowed)
```

For per-test allowed paths (tmp_path fixture):

```python
def get_test_allowed_paths(item: pytest.Item) -> frozenset[Path]:
    """Get allowed paths for a specific test item.

    Includes paths from fixtures like tmp_path that are test-specific.

    Args:
        item: pytest test item.

    Returns:
        Additional allowed paths for this specific test.

    """
    allowed: set[Path] = set()

    # If test uses tmp_path fixture, add that path
    # Note: This requires fixture resolution, which happens during setup
    # We may need to hook into pytest_fixture_post_process or similar

    return frozenset(allowed)
```

### 8. Configuration Schema

Support configuration via `pyproject.toml`:

```toml
[tool.pytest.ini_options]
# Global enforcement mode (applies to all resource types)
test_categories_enforcement = "strict"  # or "warn" or "off"

# Additional allowed paths for filesystem access (small tests)
test_categories_allowed_paths = [
    "tests/fixtures/",
    "src/mypackage/data/",
]

# Allow STAT operations for path resolution (default: true)
# This permits os.path.exists(), Path.is_file(), etc.
test_categories_allow_stat = true
```

CLI options (extend existing):

```bash
# Already exists from v0.4.0
pytest --test-categories-enforcement=strict|warn|off

# New options for filesystem
pytest --test-categories-allowed-paths=path1,path2
pytest --test-categories-allow-stat=true|false
```

Per-test marker:

```python
@pytest.mark.small
@pytest.mark.allow_filesystem  # Override: allow filesystem for this test
def test_special_case():
    ...

@pytest.mark.small
@pytest.mark.allow_filesystem_paths('/specific/path')  # Allow specific paths
def test_with_fixture_file():
    ...
```

### 9. Integration Points

The filesystem blocker integrates via pytest hooks:

1. **`pytest_configure`**: Read configuration, create blocker instance, store in plugin state
2. **`pytest_runtest_setup`**: Determine test size and markers, compute allowed paths including tmp_path
3. **`pytest_runtest_call`** (wrapper): Activate blocking before test, deactivate after
4. **`pytest_runtest_teardown`**: Ensure blocking is deactivated
5. **`pytest_terminal_summary`**: Report filesystem violation statistics

Hook integration pattern (consistent with network blocker):

```python
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item: pytest.Item) -> Generator[None, None, None]:
    """Wrap test execution with filesystem blocking."""
    state = get_plugin_state(item.config)
    blocker = state.filesystem_blocker
    test_size = get_test_size(item)

    if test_size == TestSize.SMALL and state.enforcement_mode != EnforcementMode.OFF:
        # Compute allowed paths for this test
        allowed_paths = get_default_allowed_paths(item.config) | get_test_allowed_paths(item)

        try:
            blocker.activate(test_size, state.enforcement_mode, allowed_paths)
            yield
        finally:
            blocker.deactivate()
    else:
        yield
```

### 10. Error Message Format

Violation errors provide actionable guidance:

```
============================================================
HermeticityViolationError
============================================================
Test: test_save_report (tests/test_reports.py:87)
Category: SMALL
Violation: Filesystem access attempted

Details:
  Attempted write on: /home/user/project/output/report.txt

Small tests have restricted resource access. Options:
  1. Use pytest's tmp_path fixture for temporary files
  2. Mock file operations using unittest.mock or pyfakefs
  3. Use io.StringIO or io.BytesIO for in-memory file-like objects
  4. Change test category to @pytest.mark.medium (if filesystem access is required)

Documentation: See docs/architecture/adr-002-filesystem-isolation.md
============================================================
```

### 11. Thread Safety Considerations

For pytest-xdist parallel execution:

- Each worker process has its own Python interpreter
- Global patching affects only that worker's process
- Allowed paths are computed per-test, not shared between workers
- Blocker state is stored in plugin state, which is per-worker

No special thread safety measures needed beyond standard pytest-xdist patterns.

### 12. Performance Considerations

Minimize overhead by:

1. **Lazy path resolution**: Only resolve paths when checking (not on every operation)
2. **Path caching**: Cache resolved paths and allowed-path checks
3. **Fast path checks**: Use string prefix matching before full path resolution
4. **Minimal patching surface**: Patch only the most common entry points

Estimated overhead: <1ms per filesystem operation (dominated by actual I/O in production).

## Consequences

### Benefits

1. **Consistent Architecture**: Follows established hexagonal architecture pattern from ADR-001
2. **Testability**: Fake adapter enables fast, deterministic unit tests
3. **Flexibility**: Multiple configuration layers (CLI, config file, markers, fixtures)
4. **Gradual Adoption**: Warn mode allows incremental enforcement
5. **Clear Feedback**: Actionable error messages guide developers
6. **pytest Integration**: Works seamlessly with tmp_path and other fixtures
7. **Parallel Safe**: Compatible with pytest-xdist

### Trade-offs

1. **Patching Complexity**: Many entry points to patch (builtins, os, pathlib, io)
2. **Performance Overhead**: Minor overhead from path checking on every operation
3. **Incomplete Coverage**: Some obscure filesystem operations may not be intercepted
4. **Global Patching**: Affects entire process during test execution

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Incomplete patching | Start with common operations, add more based on user feedback |
| Path resolution edge cases | Comprehensive unit tests for path resolution logic |
| pytest fixture compatibility | Test with tmp_path, tmp_path_factory explicitly |
| Performance regression | Benchmark before/after, optimize hot paths |
| Conflicts with pyfakefs | Document interaction, test compatibility |

## Alternatives Considered

### Alternative 1: Use pyfakefs Directly

**Approach**: Depend on pyfakefs and use its patching infrastructure.

**Pros**:
- Mature, well-tested patching
- Comprehensive coverage of filesystem operations
- Active maintenance

**Cons**:
- Heavy dependency (adds in-memory filesystem we don't need)
- Different philosophy (faking vs blocking)
- May conflict with user's own pyfakefs usage

**Verdict**: Rejected - we want blocking with clear errors, not silent faking.

### Alternative 2: Environment Variable Isolation

**Approach**: Run tests in a chroot or container with restricted filesystem.

**Pros**:
- True isolation at OS level
- Cannot be bypassed

**Cons**:
- Requires root/admin privileges
- Complex setup
- Platform-specific
- Significant performance overhead

**Verdict**: Rejected - too heavy-weight for unit test isolation.

### Alternative 3: LD_PRELOAD/DLL Injection

**Approach**: Use dynamic library injection to intercept system calls.

**Pros**:
- Catches all filesystem access
- Works regardless of Python bindings

**Cons**:
- Platform-specific (Linux/macOS/Windows all different)
- Complex implementation
- Potential security concerns
- May conflict with other tools

**Verdict**: Rejected - too low-level and platform-specific.

### Alternative 4: Import Hook Only

**Approach**: Block importing of filesystem-related modules.

**Pros**:
- Simple implementation
- No runtime overhead

**Cons**:
- Too coarse-grained (blocks all use, not test-specific)
- Modules often imported before test runs
- Breaks test fixtures that need filesystem

**Verdict**: Rejected - too inflexible for test-specific enforcement.

## Implementation Plan

### Phase 1: Port Interface and Exceptions (Issue #92)
- Define `FilesystemBlockerPort` interface
- Define `FilesystemOperation` enum
- Define `FilesystemAccessAttempt` model
- Add `FilesystemAccessViolationError` to exception hierarchy
- Unit tests for port contract

### Phase 2: Adapters (Issue #93)
- Implement `FakeFilesystemBlocker` test adapter
- Implement `FilesystemPatchingBlocker` production adapter
- Start with `builtins.open` and `pathlib.Path.open`
- Add path resolution and allowed-path checking
- Unit tests with fake adapter
- Integration tests with production adapter

### Phase 3: Pytest Integration (Issue #94)
- Add `--test-categories-allowed-paths` CLI option
- Add `test_categories_allowed_paths` ini option
- Implement allowed path detection (tmp_path, basetemp)
- Add `@pytest.mark.allow_filesystem` marker
- Hook into `pytest_runtest_call`
- End-to-end tests with pytester

### Phase 4: Extended Operations (Issue #95)
- Patch `os.open`, `os.mkdir`, `os.remove`, etc.
- Patch `shutil.copy`, `shutil.rmtree`, etc.
- Patch `Path.write_text`, `Path.read_text`, etc.
- Add configuration for STAT operations
- Comprehensive operation coverage tests

### Phase 5: Documentation and Polish (Issue #96)
- User documentation with examples
- Migration guide for existing users
- Troubleshooting guide for common issues
- Update CLAUDE.md with new architecture

## Test Strategy

### Unit Tests (Small, using FakeFilesystemBlocker)
- Port state machine transitions
- Path resolution logic
- Allowed path matching
- Exception message formatting
- Configuration parsing

### Integration Tests (Medium, using FilesystemPatchingBlocker)
- Actual file operation interception
- Real path resolution
- tmp_path fixture compatibility
- Multiple operation types

### End-to-End Tests (Medium, using pytester)
- Full test execution with enforcement
- CLI option handling
- Configuration file parsing
- Marker handling
- Violation reporting in terminal

### Compatibility Tests (Medium)
- pytest-xdist parallel execution
- Different Python versions (3.11, 3.12, 3.13, 3.14)
- Different operating systems (Linux, macOS, Windows)

## References

- [Google's Software Engineering at Google - Testing](https://abseil.io/resources/swe-book/html/ch11.html)
- [pyfakefs](https://github.com/pytest-dev/pyfakefs) - Prior art for filesystem patching
- [ADR-001: Network Isolation](adr-001-network-isolation.md) - Established patterns
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/) - Ports and adapters pattern
- [pytest-test-categories Planning Doc](../planning/resource-isolation-feature.md)
