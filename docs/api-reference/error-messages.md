# Error Messages Reference

This page provides a comprehensive index of all error codes, warning messages, and exceptions raised by pytest-test-categories.

## Error Code Format

All error codes follow the format `TC###` where:

- **TC** = Test Categories prefix
- **###** = Three-digit numeric identifier

**Error Code Ranges:**

| Range | Category |
|-------|----------|
| TC001-TC099 | Resource isolation violations |
| TC100-TC199 | Timing violations |
| TC200-TC299 | Distribution warnings |
| TC900-TC999 | Internal errors (reserved) |

---

## Resource Isolation Violations (TC001-TC005)

These errors occur when tests violate resource isolation rules based on their size category.

### TC001: Network Access Violation

**Exception:** `NetworkAccessViolationError`

**When it occurs:** A small test attempts to make a network connection, or a medium test attempts to connect to a non-localhost address.

**Example output:**

```
======================================================================
[TC001] Network Access Violation
======================================================================
Test: tests/test_api.py::test_fetch_data
Category: SMALL

What happened:
  Attempted network connection to api.example.com:443

Why it matters:
  Small tests must be hermetic and cannot access the network. Network calls
  introduce non-determinism, external dependencies, and can cause flaky tests
  due to network latency or failures.

To fix this (choose one):
  • Mock the network call using responses, httpretty, or respx
  • Use dependency injection to provide a fake HTTP client
  • Change test category to @pytest.mark.medium (if network access is required)

See: https://pytest-test-categories.readthedocs.io/en/latest/errors/network-isolation.html
======================================================================
```

**Remediation:**

| Test Size | Solutions |
|-----------|-----------|
| Small | Mock network calls, use dependency injection, or upgrade to `@pytest.mark.medium` |
| Medium | Use localhost for services, or upgrade to `@pytest.mark.large` |

---

### TC002: Filesystem Access Violation

**Exception:** `FilesystemAccessViolationError`

**When it occurs:** A small test attempts to access the filesystem.

**Example output:**

```
======================================================================
[TC002] Filesystem Access Violation
======================================================================
Test: tests/test_config.py::test_read_config
Category: SMALL

What happened:
  Attempted read on filesystem path: /home/user/config.yaml

Why it matters:
  Small tests must be hermetic and cannot access the filesystem. Filesystem
  access introduces I/O overhead, potential race conditions, and dependencies
  on the test environment state.

To fix this (choose one):
  • Use pyfakefs for comprehensive filesystem mocking
  • Mock file operations using pytest-mock (mocker fixture)
  • Use io.StringIO or io.BytesIO for in-memory file-like objects
  • Embed test data as Python constants or use importlib.resources
  • Change test category to @pytest.mark.medium (if filesystem access is required)

See: https://pytest-test-categories.readthedocs.io/en/latest/errors/filesystem-isolation.html
======================================================================
```

**Remediation:**

- Use `pyfakefs` for comprehensive filesystem mocking
- Use `io.StringIO` or `io.BytesIO` for in-memory file-like objects
- Mock filesystem operations with `pytest-mock`
- Embed test data as constants
- Upgrade to `@pytest.mark.medium` (which allows `tmp_path`)

---

### TC003: Subprocess Spawn Violation

**Exception:** `SubprocessViolationError`

**When it occurs:** A small test attempts to spawn a subprocess.

**Example output:**

```
======================================================================
[TC003] Subprocess Spawn Violation
======================================================================
Test: tests/test_cli.py::test_run_command
Category: SMALL

What happened:
  Attempted subprocess.run: git status (no args)

Why it matters:
  Small tests should run in a single process without spawning subprocesses.
  Subprocess spawning introduces non-determinism from external process behavior,
  I/O overhead from process creation, and timing variability that causes flaky tests.

To fix this (choose one):
  • Mock subprocess.run using pytest-mock (mocker.patch)
  • Use dependency injection to provide a fake command executor
  • Test the logic that prepares subprocess arguments, not the spawn itself
  • Change test category to @pytest.mark.medium (if subprocess is required)

See: https://pytest-test-categories.readthedocs.io/en/latest/errors/process-isolation.html
======================================================================
```

**Blocked Methods:**

- `subprocess.run`
- `subprocess.Popen`
- `subprocess.call`
- `subprocess.check_output`
- `os.popen`

**Remediation:**

- Mock subprocess calls
- Use dependency injection
- Test argument preparation separately
- Upgrade to `@pytest.mark.medium`

---

### TC004: Database Access Violation

**Exception:** `DatabaseViolationError`

**When it occurs:** A small test attempts to connect to a database (including in-memory databases like SQLite `:memory:`).

**Example output:**

```
======================================================================
[TC004] Database Access Violation
======================================================================
Test: tests/test_repository.py::test_save_user
Category: SMALL

What happened:
  Attempted sqlite3 database connection to: :memory:

Why it matters:
  Small tests should not connect to databases, even in-memory ones like sqlite3 :memory:.
  Database connections introduce I/O operations, external state dependencies,
  and additional complexity that can cause non-deterministic behavior.

To fix this (choose one):
  • Mock sqlite3.connect using pytest-mock (mocker.patch)
  • Use dependency injection to provide a fake database/repository
  • Use in-memory data structures (dict, list) for test data
  • Test business logic separately from database operations
  • Change test category to @pytest.mark.medium (if database access is required)

See: https://pytest-test-categories.readthedocs.io/en/latest/errors/database-isolation.html
======================================================================
```

**Blocked Libraries:**

- `sqlite3`
- `psycopg2` / `psycopg`
- `mysql.connector`
- `pymongo`
- `sqlalchemy` (connection methods)

**Remediation:**

- Mock database connections
- Use fake repositories (in-memory dicts)
- Test business logic separately
- Upgrade to `@pytest.mark.medium`

---

### TC005: Sleep Call Violation

**Exception:** `SleepViolationError`

**When it occurs:** A small test calls a sleep function.

**Example output:**

```
======================================================================
[TC005] Sleep Call Violation
======================================================================
Test: tests/test_async.py::test_wait_for_result
Category: SMALL

What happened:
  Called time.sleep(0.5) - attempted to sleep for 0.5 seconds

Why it matters:
  Small tests should not call sleep functions. Using sleep in tests indicates
  waiting for async operations that should use proper synchronization, flaky
  timing assumptions, or polling patterns that should use condition-based
  waiting instead.

To fix this (choose one):
  • Use proper synchronization instead of sleep (e.g., threading.Event)
  • Use condition-based waiting with polling and timeout
  • Mock time.sleep using pytest-mock (mocker.patch)
  • Use a FakeTimer or controllable time abstraction
  • Change test category to @pytest.mark.medium (if timing is required)

See: https://pytest-test-categories.readthedocs.io/en/latest/errors/sleep-blocking.html
======================================================================
```

**Blocked Functions:**

- `time.sleep`
- `asyncio.sleep`

**Remediation:**

- Use proper synchronization primitives
- Use condition-based waiting
- Mock sleep functions
- Use controllable time abstractions
- Upgrade to `@pytest.mark.medium`

---

## Timing Violations (TC006)

### TC006: Timing Violation

**Exception:** `TimingViolationError`

**When it occurs:** A test exceeds the time limit for its size category.

**Example output:**

```
======================================================================
[TC006] Timing Violation
======================================================================
Test: tests/test_slow.py::test_compute
Category: SMALL

What happened:
  SMALL test exceeded time limit of 1.0 seconds (took 2.5 seconds)

Why it matters:
  Tests have time limits based on their size category. Exceeding the time limit
  indicates the test is doing too much work for its category, may have performance
  issues, or should be recategorized to a larger size.

To fix this (choose one):
  • Optimize the test to run faster (reduce setup, use fixtures)
  • Mock slow dependencies (network, filesystem, database)
  • Split the test into smaller, focused tests
  • Change test category to @pytest.mark.medium (if more time is genuinely needed)

See: https://pytest-test-categories.readthedocs.io/en/latest/errors/timing-limits.html
======================================================================
```

**Time Limits (Fixed):**

| Size | Limit |
|------|-------|
| Small | 1 second |
| Medium | 300 seconds (5 min) |
| Large | 900 seconds (15 min) |
| XLarge | 900 seconds (15 min) |

Time limits are fixed per Google's testing standards and cannot be customized. This ensures consistent test categorization across all projects.

**Remediation:**

- Optimize test performance
- Mock slow dependencies
- Split into smaller tests
- Upgrade to larger test category

---

## Distribution Warnings (TC007)

### TC007: Test Distribution Warning

**Exception:** `DistributionViolationError` (strict mode only)

**When it occurs:** The test suite distribution does not match recommended proportions.

**Example output (warning mode):**

```
PytestWarning: [TC007] Test distribution does not meet targets: Small tests are 45.0%
(target: 75%-85%). Consider adding more small tests or converting medium tests.
```

**Example output (strict mode):**

```
pytest.UsageError: [TC007] Test distribution does not meet targets: Small tests are 45.0%
(target: 75%-85%). Consider adding more small tests or converting medium tests.
```

**Target Distribution:**

| Size | Target | Tolerance | Acceptable Range |
|------|--------|-----------|------------------|
| Small | 80% | +/- 5% | 75% - 85% |
| Medium | 15% | +/- 5% | 10% - 20% |
| Large/XLarge | 5% | +/- 3% | 2% - 8% |

**Critical Thresholds:**

| Condition | Severity |
|-----------|----------|
| Small tests < 50% | Critical - test pyramid inverted |
| Medium tests > 20% | Warning |
| Large/XLarge > 8% | Warning |

**Remediation:**

- Add more small (unit) tests
- Convert medium tests to small by mocking dependencies
- Review if large tests can be split
- Ensure integration logic is tested at appropriate levels

---

## Pytest Warnings

### Missing Size Marker Warning

**Type:** `PytestWarning`

**When it occurs:** A test has no size marker.

**Example output:**

```
PytestWarning: Test has no size marker: tests/test_example.py::test_unmarked
```

**Remediation:**

Add an appropriate size marker:

```python
import pytest

@pytest.mark.small  # Add this
def test_unmarked():
    pass
```

---

### Multiple Size Markers Error

**Type:** `pytest.UsageError`

**When it occurs:** A test has more than one size marker.

**Example output:**

```
pytest.UsageError: Test cannot have multiple size markers: ['small', 'medium']
```

**Cause:**

```python
@pytest.mark.small
@pytest.mark.medium  # ERROR: Can't have both!
def test_invalid():
    pass
```

**Remediation:**

Use only one size marker per test.

---

## Exception Hierarchy

```
Exception
+-- HermeticityViolationError (base for resource violations)
|   +-- NetworkAccessViolationError [TC001]
|   +-- FilesystemAccessViolationError [TC002]
|   +-- SubprocessViolationError [TC003]
|   +-- DatabaseViolationError [TC004]
|   +-- SleepViolationError [TC005]
+-- TimingViolationError [TC006]
+-- DistributionViolationError [TC007]
```

---

## Enforcement Modes

Error behavior depends on the configured enforcement mode:

| Mode | Violations | Warnings |
|------|------------|----------|
| `off` | Not checked | Not emitted |
| `warn` | Emit warning | Emit warning |
| `strict` | Raise exception | Emit warning |

**Configuration:**

```toml
# pyproject.toml
[tool.pytest.ini_options]
test_categories_enforcement = "strict"
test_categories_distribution_enforcement = "warn"
```

```bash
# Command line
pytest --test-categories-enforcement=strict
pytest --test-categories-distribution-enforcement=warn
```

---

## Source Code References

| Component | Location |
|-----------|----------|
| Error codes registry | [`errors.py`](https://github.com/mikelane/pytest-test-categories/blob/main/src/pytest_test_categories/errors.py) |
| Exception classes | [`exceptions.py`](https://github.com/mikelane/pytest-test-categories/blob/main/src/pytest_test_categories/exceptions.py) |
| Timing violations | [`timing.py`](https://github.com/mikelane/pytest-test-categories/blob/main/src/pytest_test_categories/timing.py) |
| Distribution validation | [`services/distribution_validation.py`](https://github.com/mikelane/pytest-test-categories/blob/main/src/pytest_test_categories/services/distribution_validation.py) |
