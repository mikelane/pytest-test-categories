# ADR-004: Database Isolation Mechanism for Small Tests

## Status

Implemented

> **Implementation Progress**: The core implementation is complete in PR #110.
> This includes `DatabaseBlockerPort` interface, `DatabasePatchingBlocker` adapter,
> `FakeDatabaseBlocker` test adapter, and `DatabaseViolationError` exception.
> Track progress in Issue #102.

## Context

Small tests, as defined by Google's "Software Engineering at Google" best practices, must be **hermetic** and run **entirely in memory**. Database connections in small tests create several problems:

- **External state**: Databases maintain state outside the test process
- **I/O overhead**: Database connections involve network or file I/O
- **Non-determinism**: Shared databases can cause test interference
- **Timing variability**: Connection establishment and query times vary
- **Environment coupling**: Tests become dependent on database availability

Currently, pytest-test-categories enforces timing constraints (v0.1.0), network isolation (v0.4.0), filesystem isolation (v0.5.0), and process isolation (v0.6.0). However, a test can still connect to databases, violating the hermeticity constraint for small tests.

We need a mechanism to:

1. Detect database connection attempts during small test execution
2. Block connections and provide clear error messages
3. Allow connections for medium/large/xlarge tests where database access is appropriate

### Existing Architecture Context

The plugin follows **hexagonal architecture** (ports and adapters):

- **Ports**: Abstract interfaces defining contracts (`TestTimer`, `NetworkBlockerPort`, `FilesystemBlockerPort`, `ProcessBlockerPort`)
- **Production Adapters**: Real implementations (`WallTimer`, `SocketPatchingNetworkBlocker`, `FilesystemPatchingBlocker`, `SubprocessPatchingBlocker`)
- **Test Adapters**: Controllable test doubles (`FakeTimer`, `FakeNetworkBlocker`, `FakeFilesystemBlocker`, `FakeProcessBlocker`)

This pattern enables:
- Unit tests to be fast and deterministic (using fake adapters)
- Integration tests to validate real behavior (using production adapters)
- Easy extensibility for new resource types

The existing isolation mechanisms (ADR-001, ADR-002, ADR-003) established patterns we follow:
- Port interface with state machine (INACTIVE -> ACTIVE -> INACTIVE)
- Design-by-contract with icontract preconditions/postconditions
- Pydantic models for configuration and data transfer
- Clear exception hierarchy with actionable error messages

### Research: Database Entry Points in Python

Python provides multiple ways to connect to databases:

**Standard Library:**
- `sqlite3.connect` - SQLite database connections (including `:memory:`)

**Popular Database Libraries (Optional):**
- `psycopg2.connect` / `psycopg.connect` - PostgreSQL
- `pymysql.connect` - MySQL
- `pymongo.MongoClient` - MongoDB
- `redis.Redis` / `redis.StrictRedis` - Redis
- `sqlalchemy.create_engine` - SQLAlchemy ORM

### Research: Interception Strategy

We intercept database connections at the library-specific connection functions:

1. **sqlite3.connect**: Standard library - always available
2. **Optional libraries**: Only patched if installed (graceful ImportError handling)

Note: In-memory SQLite (`:memory:`) is also blocked for small tests. While it doesn't perform file I/O, it still represents database usage that should be avoided in small tests for consistency and to encourage pure unit testing patterns.

## Decision

We will implement database isolation using a **database patching approach** following the hexagonal architecture pattern established in ADR-001, ADR-002, and ADR-003.

### 1. Port Interface: `DatabaseBlockerPort`

Define an abstract interface for database blocking:

```python
class DatabaseBlockerPort(BaseModel, ABC):
    """Port defining database blocking behavior.

    Implementations control whether database connections are permitted during
    test execution. The port follows a state machine pattern:
    INACTIVE -> ACTIVE -> INACTIVE

    This mirrors the ProcessBlockerPort and other blocker patterns.

    Attributes:
        state: Current blocker state (INACTIVE or ACTIVE).

    """

    state: BlockerState = BlockerState.INACTIVE

    @require(lambda self: self.state == BlockerState.INACTIVE, 'Blocker must be INACTIVE to activate')
    @ensure(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE after activation')
    def activate(self, test_nodeid: str, test_size: TestSize, enforcement_mode: EnforcementMode) -> None:
        """Activate database blocking for a test."""

    @require(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE to deactivate')
    @ensure(lambda self: self.state == BlockerState.INACTIVE, 'Blocker must be INACTIVE after deactivation')
    def deactivate(self) -> None:
        """Deactivate database blocking, restoring normal behavior."""

    @require(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE to check connections')
    def check_connection_allowed(self, library: str, connection_string: str) -> bool:
        """Check if a database connection is allowed."""

    @require(lambda self: self.state == BlockerState.ACTIVE, 'Blocker must be ACTIVE to handle violations')
    def on_violation(
        self,
        library: str,
        connection_string: str,
        test_nodeid: str,
    ) -> None:
        """Handle a database connection violation."""
```

### 2. Database Access Attempt Record

```python
class DatabaseAccessAttempt(BaseModel, frozen=True):
    """Immutable record of a database access attempt.

    Attributes:
        library: The database library used (e.g., 'sqlite3', 'psycopg2').
        connection_string: The connection string or database path.
        test_nodeid: The pytest node ID of the test.
        allowed: Whether the connection was permitted.

    """

    library: str
    connection_string: str
    test_nodeid: str
    allowed: bool
```

### 3. Production Adapter: `DatabasePatchingBlocker`

Implements `DatabaseBlockerPort` by:

1. **Patching Strategy** - Patch at library-specific entry points:
   - `sqlite3.connect` - Always patched (standard library)
   - Optional libraries patched only if installed

2. **Optional Dependency Handling**:
   - Try importing each library at activation time
   - Skip patching for uninstalled libraries
   - No hard dependencies on database libraries

3. **Violation Handling**:
   - STRICT mode: Raise `DatabaseViolationError`
   - WARN mode: Log warning, allow connection
   - OFF mode: No enforcement

```python
class DatabasePatchingBlocker(DatabaseBlockerPort):
    """Production adapter that patches database libraries to block connections.

    This adapter intercepts database connections by patching:
    - sqlite3.connect (always)
    - psycopg2.connect, psycopg.connect (if installed)
    - pymysql.connect (if installed)
    - pymongo.MongoClient (if installed)
    - redis.Redis, redis.StrictRedis (if installed)
    - sqlalchemy.create_engine (if installed)

    The patching is reversible - deactivate() restores originals.

    """
```

### 4. Test Adapter: `FakeDatabaseBlocker`

Provides controllable test double:

```python
class FakeDatabaseBlocker(DatabaseBlockerPort):
    """Test double for database blocking without actual patching.

    Tracks all method calls and connection attempts for verification.

    Attributes:
        connection_attempts: List of recorded connection attempts.
        warnings: List of warning messages (WARN mode).
        activate_count: Number of activate() calls.
        deactivate_count: Number of deactivate() calls.

    """
```

### 5. Exception Class

```python
class DatabaseViolationError(HermeticityViolationError):
    """Raised when a test attempts to connect to a database.

    Attributes:
        library: The database library used.
        connection_string: The connection string attempted.

    """
```

### 6. Integration Points

The database blocker integrates via pytest hooks:

1. **`pytest_configure`**: Create blocker instance, store in plugin state
2. **`pytest_runtest_call`** (wrapper): Activate blocking before test, deactivate after
3. **`pytest_runtest_teardown`**: Ensure blocking is deactivated

### 7. Error Message Format

Violation errors provide actionable guidance:

```
============================================================
HermeticityViolationError
============================================================
Test: test_user_repository (tests/test_repos.py:42)
Category: SMALL
Violation: Database connection attempted

Details:
  Attempted sqlite3.connect: :memory:

Small tests have restricted resource access. Options:
  1. Use an in-memory fake/stub instead of a real database
  2. Mock the database connection using pytest-mock
  3. Use dependency injection to provide a fake repository
  4. Change test category to @pytest.mark.medium (if database is required)

Documentation: See docs/architecture/adr-004-database-isolation.md
============================================================
```

## Consequences

### Benefits

1. **Consistent Architecture**: Follows established hexagonal architecture pattern from ADR-001/002/003
2. **Testability**: Fake adapter enables fast, deterministic unit tests
3. **Gradual Adoption**: Warn mode allows incremental enforcement
4. **Clear Feedback**: Actionable error messages guide developers
5. **Optional Dependencies**: Graceful handling of uninstalled database libraries
6. **Hermeticity Enforcement**: Ensures small tests don't depend on databases

### Trade-offs

1. **Strict In-Memory Blocking**: Even `:memory:` SQLite is blocked (stricter interpretation)
2. **Global Patching**: Database patching affects entire process during test
3. **Library Coverage**: Only covers popular libraries; exotic databases not blocked
4. **Performance Overhead**: Minor overhead from connection interception (negligible)

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Missing library coverage | Start with popular libraries, add more based on feedback |
| pytest-xdist compatibility | Each worker has separate interpreter, patching is per-worker |
| Complex connection strings | Handle various formats gracefully |
| Optional dependency errors | Try/except ImportError for all optional libraries |

## Alternatives Considered

### Alternative 1: Network-Level Blocking

**Approach**: Block database connections via network isolation.

**Pros**:
- Already have network blocking in place
- Catches all TCP-based databases

**Cons**:
- Doesn't catch SQLite (file-based)
- Doesn't catch Unix socket connections
- Too coarse-grained for database-specific errors

**Verdict**: Rejected - incomplete coverage and poor error messages.

### Alternative 2: Import Hook Blocking

**Approach**: Prevent importing database modules in small tests.

**Pros**:
- Catches all usage at module level

**Cons**:
- Database modules often imported at application startup
- Breaks fixtures that legitimately use databases
- No runtime control

**Verdict**: Rejected - too inflexible.

### Alternative 3: Allow In-Memory Databases

**Approach**: Allow `:memory:` SQLite but block file-based.

**Pros**:
- In-memory databases are technically "in-memory"
- Less disruptive for existing tests

**Cons**:
- Still represents database usage pattern
- Inconsistent with "pure unit test" philosophy
- Harder to explain the distinction

**Verdict**: Rejected - stricter interpretation preferred for consistency.

## Implementation Notes

### Intercepted Entry Points

The following entry points are intercepted:

- `sqlite3.connect` (always)
- `psycopg2.connect` (if installed)
- `psycopg.connect` (if installed)
- `pymysql.connect` (if installed)
- `pymongo.MongoClient` (if installed)
- `redis.Redis` (if installed)
- `redis.StrictRedis` (if installed)
- `sqlalchemy.create_engine` (if installed)

### Thread Safety Considerations

For pytest-xdist parallel execution:

- Each worker process has its own Python interpreter
- Global patching affects only that worker's process
- Blocker state is stored in plugin state, which is per-worker

No special thread safety measures needed beyond standard pytest-xdist patterns.

## Test Strategy

### Unit Tests (Small, using FakeDatabaseBlocker)
- Port state machine transitions
- Connection permission rules
- Exception message formatting
- Warning recording

### Integration Tests (Medium, using DatabasePatchingBlocker)
- Actual sqlite3 connection interception
- Function restoration on deactivate
- Enforcement mode behavior

### End-to-End Tests (Medium, using pytester)
- Full test execution with enforcement
- Violation reporting in terminal

## References

- [Google's Software Engineering at Google - Testing](https://abseil.io/resources/swe-book/html/ch11.html)
- [ADR-001: Network Isolation](adr-001-network-isolation.md) - Established patterns
- [ADR-002: Filesystem Isolation](adr-002-filesystem-isolation.md) - Established patterns
- [ADR-003: Process Isolation](adr-003-process-isolation.md) - Established patterns
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/) - Ports and adapters pattern
- [Python sqlite3 documentation](https://docs.python.org/3/library/sqlite3.html)
