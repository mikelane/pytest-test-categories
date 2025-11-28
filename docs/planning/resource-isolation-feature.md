# Resource Isolation Feature Planning Document

## Overview

This document provides context and requirements for implementing resource isolation enforcement in pytest-test-categories. The goal is to ensure tests marked with specific size categories adhere to resource access restrictions, following Google's test size philosophy from "Software Engineering at Google."

## Background: Google's Test Size Philosophy

Google defines test sizes not just by execution time, but by resource access:

| Size | Time Limit | Network | Filesystem | Database | Sleep/Time | Subprocess |
|------|------------|---------|------------|----------|------------|------------|
| Small | 1s | No | No | No | No | No |
| Medium | 5min | localhost only | Yes | localhost only | Yes | Yes |
| Large | 15min | Yes | Yes | Yes | Yes | Yes |
| XLarge | 15min | Yes | Yes | Yes | Yes | Yes |

**Small tests must be hermetic** — they run entirely in memory with no external dependencies. This makes them:
- Fast (no I/O latency)
- Deterministic (no external state)
- Parallelizable (no resource contention)
- Reliable (no flaky network/disk issues)

## Feature Goals

### Primary Goal
Enforce resource restrictions based on test category. Tests that violate their category's restrictions should fail with a clear error message.

### Secondary Goal
Design the architecture to support future DI-based automatic resource faking (not in scope for this feature, but the design must not preclude it).

## Behaviors to Implement

### 1. Resource Restriction Registry

Create a registry that maps test sizes to their resource restrictions.

```python
# Conceptual structure
RESOURCE_RESTRICTIONS = {
    TestSize.SMALL: {
        'network': False,      # No network access
        'filesystem': False,   # No filesystem access
        'subprocess': False,   # No subprocess spawning
        'sleep': False,        # No time.sleep or blocking waits
        'database': False,     # No database connections
    },
    TestSize.MEDIUM: {
        'network': 'localhost',  # localhost only
        'filesystem': True,
        'subprocess': True,
        'sleep': True,
        'database': 'localhost',
    },
    TestSize.LARGE: {
        'network': True,
        'filesystem': True,
        'subprocess': True,
        'sleep': True,
        'database': True,
    },
    TestSize.XLARGE: {
        # Same as LARGE
    },
}
```

### 2. Network Access Enforcement

**Behavior:**
- Small tests: Block ALL socket operations
- Medium tests: Allow only localhost (127.0.0.1, ::1, localhost)
- Large/XLarge tests: Allow all network access

**Implementation approach:**
- Use socket blocking similar to `pytest-socket`
- Intercept `socket.socket()` creation
- Check test category and enforce restrictions
- Provide clear error: `NetworkAccessViolation: Small tests cannot access the network. Test attempted to connect to 'api.example.com:443'.`

**Edge cases:**
- DNS resolution (should be blocked for small tests)
- Unix domain sockets (localhost? filesystem? need to decide)
- Mock servers on localhost (allowed for medium)

### 3. Filesystem Access Enforcement

**Behavior:**
- Small tests: Block all filesystem operations except reading from package resources
- Medium/Large/XLarge tests: Allow filesystem access

**Implementation approach:**
- Intercept `open()`, `pathlib.Path` operations, `os.open()`, etc.
- Allow reading from:
  - Installed package resources (`importlib.resources`)
  - `__file__` directory (test file location) — configurable
- Block writing entirely for small tests
- Provide clear error: `FilesystemAccessViolation: Small tests cannot write to the filesystem. Test attempted to write to '/tmp/test_output.txt'.`

**Edge cases:**
- Temporary files (`tempfile.NamedTemporaryFile`) — block for small
- Memory-mapped files — block for small
- Reading test fixtures from disk — need configuration option

### 4. Subprocess Enforcement

**Behavior:**
- Small tests: Block all subprocess creation
- Medium/Large/XLarge tests: Allow subprocess creation

**Implementation approach:**
- Intercept `subprocess.Popen`, `subprocess.run`, `os.system`, `os.spawn*`, `os.exec*`
- Provide clear error: `SubprocessViolation: Small tests cannot spawn subprocesses. Test attempted to run 'git status'.`

### 5. Sleep/Blocking Enforcement

**Behavior:**
- Small tests: Block `time.sleep()` and similar blocking operations
- Medium/Large/XLarge tests: Allow sleeping

**Implementation approach:**
- Intercept `time.sleep()`
- Consider also: `threading.Event.wait()`, `asyncio.sleep()`, `select.select()` with timeout
- Provide clear error: `SleepViolation: Small tests cannot use time.sleep(). Use dependency injection to control time in tests.`

**Note:** This is where future DI integration becomes valuable — instead of blocking sleep, inject a fake timer.

### 6. Database Connection Enforcement

**Behavior:**
- Small tests: Block all database connections
- Medium tests: Allow localhost database connections only
- Large/XLarge tests: Allow all database connections

**Implementation approach:**
- This is harder to enforce generically (many DB libraries)
- Consider integration with popular libraries: `psycopg2`, `sqlalchemy`, `pymongo`, `redis`
- May need to be opt-in per library
- Provide clear error: `DatabaseAccessViolation: Small tests cannot connect to databases. Test attempted to connect to 'postgresql://localhost/mydb'.`

### 7. Configuration System

Users need to configure restrictions for their project.

```toml
# pyproject.toml
[tool.pytest-test-categories.restrictions]
# Override default restrictions
small.network = false
small.filesystem = false
small.subprocess = false
small.sleep = false

medium.network = "localhost"
medium.filesystem = true

# Allow reading test fixtures for small tests
small.filesystem_read_paths = [
    "tests/fixtures/",
    "src/*/test_data/",
]

# Exempt specific tests from enforcement (escape hatch)
exempt_tests = [
    "tests/legacy/test_old_integration.py::test_needs_network",
]
```

### 8. Enforcement Modes

```toml
[tool.pytest-test-categories]
# Enforcement mode
enforcement = "strict"  # or "warn" or "off"
```

- `strict`: Violations fail the test immediately
- `warn`: Violations emit a warning but test continues
- `off`: No enforcement (for gradual adoption)

### 9. Error Messages

All violation errors must be:
- Clear about what was violated
- Specific about what the test attempted to do
- Actionable with guidance on how to fix

```
================== ResourceViolation ==================
Test: test_user_creation (tests/test_users.py:42)
Category: SMALL
Violation: Network access attempted

Details:
  Test attempted to connect to: api.stripe.com:443

Small tests cannot access the network. Options:
  1. Mock the network call using responses, httpretty, or respx
  2. Use dependency injection to provide a fake HTTP client
  3. Change test category to @pytest.mark.medium (if network is required)

Documentation: https://pytest-test-categories.readthedocs.io/en/latest/resource-isolation/
=======================================================
```

### 10. pytest Integration

**New CLI options:**
```bash
# Enable/disable enforcement for this run
pytest --resource-enforcement=strict
pytest --resource-enforcement=warn
pytest --resource-enforcement=off

# Show which resources each test accessed (debugging)
pytest --show-resource-access
```

**New markers (optional, for per-test overrides):**
```python
@pytest.mark.small
@pytest.mark.allow_network  # Override: allow network for this specific test
def test_special_case():
    ...
```

### 11. Reporting

Add resource violation summary to test output:

```
=================== test session starts ====================
collected 150 items

tests/test_users.py::test_create_user PASSED [SMALL]
tests/test_users.py::test_fetch_user FAILED [SMALL - NetworkViolation]
tests/test_api.py::test_endpoint PASSED [MEDIUM]
...

================ Resource Violation Summary ================
2 tests failed due to resource violations:
  - test_fetch_user: Network access (api.example.com)
  - test_save_file: Filesystem write (/tmp/output.txt)

Tip: Run with --resource-enforcement=warn to see violations without failing
====================================================================
```

## Architecture Considerations

### Hexagonal Architecture Alignment

This feature should follow the existing hexagonal architecture pattern:

```
┌─────────────────────────────────────────────────────────────┐
│                         Ports                                │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ NetworkPort │ │FilesystemPort│ │SubprocessPort│ ...      │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Enforcement Service                       │
│  - Checks test category                                      │
│  - Applies restrictions                                      │
│  - Reports violations                                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        Adapters                              │
│  ┌──────────────────┐ ┌──────────────────┐                  │
│  │ BlockingAdapter  │ │ PassthroughAdapter│                 │
│  │ (enforcement)    │ │ (no enforcement)  │                 │
│  └──────────────────┘ └──────────────────┘                  │
│  ┌──────────────────┐                                       │
│  │ FakeAdapter      │  ← Future: DI integration             │
│  │ (auto-faking)    │                                       │
│  └──────────────────┘                                       │
└─────────────────────────────────────────────────────────────┘
```

### Ports (Interfaces)

Define abstract ports for each resource type:

```python
class NetworkPort(Protocol):
    """Port for network access control."""

    def check_connection_allowed(self, host: str, port: int) -> bool:
        """Check if connection to host:port is allowed."""
        ...

    def on_violation(self, host: str, port: int, test_context: TestContext) -> None:
        """Handle a network access violation."""
        ...
```

### Future DI Integration Path

The port/adapter design enables future dioxide integration:

```python
# Future: dioxide integration
class DioxideNetworkAdapter(NetworkPort):
    """Adapter that provides fake network via dioxide DI."""

    def __init__(self, container: dioxide.Container):
        self.container = container

    def check_connection_allowed(self, host: str, port: int) -> bool:
        # Instead of blocking, inject a fake
        self.container.register(HttpClient, FakeHttpClient)
        return True  # "Allowed" because we're faking it
```

This is OUT OF SCOPE for this feature, but the architecture must support it.

## Implementation Phases

### Phase 1: Core Infrastructure
1. Create resource restriction registry
2. Create port interfaces for each resource type
3. Create enforcement service
4. Add configuration system to pyproject.toml

### Phase 2: Network Enforcement
1. Implement NetworkPort and BlockingNetworkAdapter
2. Socket interception mechanism
3. Localhost detection for medium tests
4. Error messages and reporting

### Phase 3: Filesystem Enforcement
1. Implement FilesystemPort and BlockingFilesystemAdapter
2. File operation interception
3. Read path allowlisting
4. Error messages and reporting

### Phase 4: Additional Resources
1. Subprocess enforcement
2. Sleep/time enforcement
3. Database connection enforcement (opt-in per library)

### Phase 5: Polish
1. CLI options
2. Reporting improvements
3. Documentation
4. Migration guide for existing users

## Testing Strategy

### Unit Tests (Small)
- Test restriction registry logic
- Test violation detection logic
- Test error message formatting
- Use FakeAdapter for all resource ports

### Integration Tests (Medium)
- Test actual socket blocking
- Test actual filesystem blocking
- Test pytest hook integration
- Test CLI options

### End-to-End Tests (Medium)
- Test full workflow with pytester fixture
- Verify violations fail tests correctly
- Verify warnings work correctly
- Verify configuration is respected

## Open Questions

1. **Unix domain sockets**: Are these "network" or "filesystem"? Probably filesystem.

2. **Memory-mapped files**: Block for small tests? Probably yes.

3. **Reading test fixtures**: Should small tests be allowed to read fixture files? Configurable.

4. **Async support**: How do we handle `asyncio.sleep()` and async network operations?

5. **Third-party library interception**: How deep do we go? (requests, httpx, aiohttp, urllib3, etc.)

6. **Performance**: Will interception add measurable overhead? Need benchmarks.

7. **pytest-xdist compatibility**: Does enforcement work correctly with parallel test execution?

## Success Criteria

1. Small tests that access the network fail with clear error messages
2. Small tests that write to filesystem fail with clear error messages
3. Medium tests can access localhost but not external network
4. Configuration allows customization per project
5. Existing tests continue to work (enforcement is opt-in initially)
6. Architecture supports future DI integration without refactoring
7. Documentation explains the "why" and "how"

## References

- Google's "Software Engineering at Google" - Chapter on Testing
- pytest-socket: https://github.com/miketheman/pytest-socket
- pyfakefs: https://github.com/pytest-dev/pyfakefs
- Existing pytest-test-categories architecture: See CLAUDE.md

## Out of Scope

- Automatic resource faking via DI (future feature)
- Integration with dioxide (future feature)
- Mutation testing integration (separate tool)
- Coverage-to-test mapping (separate tool: pytest-test-impact)
