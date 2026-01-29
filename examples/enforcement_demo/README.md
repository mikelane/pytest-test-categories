# Enforcement Demo: Hermetic Testing in Action

This demo showcases pytest-test-categories' enforcement features. You'll see how
the plugin catches common testing anti-patterns and guides developers toward
hermetic, reliable tests.

## The Problem: Flaky Tests

Most test suites suffer from flaky tests - tests that pass locally but fail in CI,
or fail randomly with no apparent cause. The root cause is almost always **hidden
external dependencies**:

- Tests that hit real APIs
- Tests that use `time.sleep()` for synchronization
- Tests that read/write to the filesystem
- Tests that spawn subprocesses
- Tests that create threads with timing assumptions

These dependencies introduce non-determinism. pytest-test-categories **enforces
hermetic testing practices** by detecting and blocking these anti-patterns in
small tests.

## Quick Start

```bash
# From this directory
cd examples/enforcement_demo

# Run the interactive demo
./demo.sh

# Or run manually with different modes:

# See violations without failing tests
pytest --test-categories-enforcement=warn tests/

# Enforce strict hermeticity (violations fail tests)
pytest --test-categories-enforcement=strict tests/test_problem_tests.py

# Run hermetic tests (all pass in strict mode)
pytest --test-categories-enforcement=strict tests/test_solution_tests.py
```

## Demo Structure

```
enforcement_demo/
├── README.md                    # This file
├── demo.sh                      # Interactive demo script
├── pyproject.toml              # Demo configuration
├── src/demo_app/               # Example application code
│   ├── api_client.py           # HTTP client (network dependency)
│   ├── cache.py                # Cache with TTL (sleep dependency)
│   ├── config.py               # File-based config (filesystem dependency)
│   ├── shell.py                # Shell commands (subprocess dependency)
│   └── worker.py               # Background worker (threading dependency)
└── tests/
    ├── conftest.py             # Shared fixtures
    ├── test_problem_tests.py   # Tests with hermeticity violations
    └── test_solution_tests.py  # Properly hermetic tests
```

## What the Demo Shows

### 1. Sleep Violations

**Problem**: Tests using `time.sleep()` to wait for async operations.

```python
@pytest.mark.small
def test_cache_expiration():
    cache.set("key", "value", ttl=0.1)
    time.sleep(0.2)  # VIOLATION: Sleep in small test
    assert cache.get("key") is None
```

**Solution**: Use controllable time abstractions or condition-based waiting.

```python
@pytest.mark.small
def test_cache_expiration(mocker):
    fake_time = mocker.patch("time.time")
    fake_time.return_value = 1000.0

    cache.set("key", "value", ttl=60)
    fake_time.return_value = 1061.0  # Advance time

    assert cache.get("key") is None
```

### 2. Network Violations

**Problem**: Tests hitting real HTTP endpoints.

```python
@pytest.mark.small
def test_fetch_user():
    client = ApiClient("https://api.example.com")
    user = client.get_user(1)  # VIOLATION: Real network call
    assert user["name"] == "Alice"
```

**Solution**: Use HTTP mocking (responses, httpretty, respx, pytest-httpx).

```python
@pytest.mark.small
def test_fetch_user(httpx_mock):
    httpx_mock.add_response(json={"id": 1, "name": "Alice"})

    client = ApiClient("https://api.example.com")
    user = client.get_user(1)

    assert user["name"] == "Alice"
```

### 3. Filesystem Violations

**Problem**: Tests reading/writing to the real filesystem.

```python
@pytest.mark.small
def test_load_config():
    config = load_config("/etc/app/config.yaml")  # VIOLATION
    assert config["debug"] is False
```

**Solution**: Use pyfakefs, io.StringIO, or embed test data as constants.

```python
@pytest.mark.small
def test_load_config(fs):  # pyfakefs fixture
    fs.create_file("/etc/app/config.yaml", contents="debug: false")

    config = load_config("/etc/app/config.yaml")

    assert config["debug"] is False
```

### 4. Subprocess Violations

**Problem**: Tests spawning real processes.

```python
@pytest.mark.small
def test_git_version():
    result = subprocess.run(["git", "--version"], capture_output=True)  # VIOLATION
    assert "git version" in result.stdout.decode()
```

**Solution**: Mock subprocess or test the argument preparation separately.

```python
@pytest.mark.small
def test_build_git_command():
    cmd = GitClient().build_version_command()
    assert cmd == ["git", "--version"]

@pytest.mark.medium
def test_git_version_integration():
    # Medium tests can use subprocess
    result = subprocess.run(["git", "--version"], capture_output=True)
    assert "git version" in result.stdout.decode()
```

### 5. Threading Violations

**Problem**: Tests creating threads with timing assumptions.

```python
@pytest.mark.small
def test_background_job():
    worker = BackgroundWorker()
    worker.start()
    time.sleep(0.1)  # Hope it finishes...
    assert worker.completed
```

**Solution**: Test the work logic synchronously, or use medium tests for integration.

```python
@pytest.mark.small
def test_job_logic():
    result = process_item({"id": 1})
    assert result["status"] == "processed"

@pytest.mark.medium
def test_worker_integration():
    worker = BackgroundWorker()
    worker.start()
    worker.join(timeout=5.0)
    assert worker.completed
```

## Enforcement Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `off` | No enforcement (default) | Initial exploration |
| `warn` | Log violations, tests pass | Migration period |
| `strict` | Violations fail tests | Production enforcement |

### Recommended Adoption Path

```toml
# Week 1: Discovery
test_categories_enforcement = "off"
# Run with --test-size-report=detailed to see violations

# Weeks 2-4: Migration
test_categories_enforcement = "warn"
# Fix violations incrementally, CI shows warnings

# Week 5+: Production
test_categories_enforcement = "strict"
# Violations fail the build
```

## Violation Summary

After running tests, you'll see a summary like:

```
========== Hermeticity Violation Summary ==========
Violations detected (enforcement: warn):
  Network:     2 tests (test_api.py::test_fetch, test_api.py::test_post)
  Sleep:       1 test (test_cache.py::test_expiration)
  Filesystem:  1 test (test_config.py::test_load)
  Subprocess:  1 test (test_shell.py::test_run)

Total: 5 violations in 5 tests

To fix: Mock external dependencies or change test category to @pytest.mark.medium
Docs: https://pytest-test-categories.readthedocs.io/resource-isolation/
=====================================================
```

## Learn More

- [pytest-test-categories Documentation](https://pytest-test-categories.readthedocs.io)
- [Software Engineering at Google: Testing Overview](https://abseil.io/resources/swe-book)
- [Why Hermetic Tests Matter](https://testing.googleblog.com/2012/10/hermetic-servers.html)
