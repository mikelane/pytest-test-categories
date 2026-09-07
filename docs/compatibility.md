# Ecosystem Compatibility

pytest-test-categories is designed to work alongside the existing pytest ecosystem. This page documents compatibility with popular plugins and recommended tool combinations.

## Compatibility Matrix

| Tool | Status | Notes |
|------|--------|-------|
| `pytest-xdist` | ✅ Supported | Per-worker isolation; distribution stats aggregated correctly |
| `pytest-timeout` | ✅ Complementary | Our time limits are per-category; use for global CI failsafe |
| `pytest-socket` | ✅ Overlaps | Both block network; choose based on per-test control needs |
| `pytest-httpx` | ✅ Recommended | Mock HTTP calls to make tests hermetic |
| `responses` | ✅ Recommended | Alternative HTTP mocking library |
| `httpretty` | ✅ Compatible | Another HTTP mocking option |
| `pyfakefs` | ✅ Recommended (scoped, see below) | Filesystem virtualization for hermetic tests |
| `pytest-mock` | ✅ Recommended | General-purpose mocking |
| `freezegun` | ✅ Recommended | Time mocking for deterministic tests |
| `time-machine` | ✅ Recommended | Modern alternative to freezegun (faster) |
| `pytest-cov` | ✅ Compatible | Coverage tracking works normally |
| `pytest-benchmark` | ✅ Compatible | Benchmarks work; mind category time limits |
| `hypothesis` | ✅ Compatible | Property-based testing works normally |
| `pytest-asyncio` | ✅ Compatible | Async tests work normally |
| `testcontainers` | ✅ Compatible | Use `@pytest.mark.large` for container tests (orchestration required) |

## Detailed Notes

### pytest-xdist

Full parallel execution support. Each worker runs independently with proper session handling.

**Configuration considerations:**
- Distribution stats are aggregated correctly across workers
- Each worker enforces hermeticity independently
- Use `pytest -n auto` as usual

```bash
# Parallel execution works out of the box
pytest -n auto --test-categories-enforcement=strict
```

### pytest-timeout

Our category-based time limits (1s/300s/900s) and pytest-timeout serve different purposes:

- **pytest-test-categories**: Enforces size-appropriate limits, fails fast on violations
- **pytest-timeout**: Global failsafe for CI, catches runaway tests

**Recommended setup:**
```toml
[tool.pytest.ini_options]
test_categories_enforcement = "strict"
timeout = 600  # Global 10-minute failsafe via pytest-timeout
```

### pytest-socket vs. pytest-test-categories

Both can block network access, but with different philosophies:

| Feature | pytest-socket | pytest-test-categories |
|---------|---------------|------------------------|
| Per-test overrides | ✅ Yes (`@pytest.mark.enable_socket`) | ❌ No (by design) |
| Filesystem blocking | ❌ No | ✅ Yes |
| Subprocess blocking | ❌ No | ✅ Yes |
| Time limits | ❌ No | ✅ Yes |
| Distribution validation | ❌ No | ✅ Yes |

**Choose based on your needs:**
- Use **pytest-socket** if you need per-test network overrides
- Use **pytest-test-categories** for holistic test quality enforcement
- They can coexist if you need both behaviors

### HTTP Mocking Libraries

For hermetic small tests, you need to mock HTTP calls. We recommend:

| Library | Style | Best For |
|---------|-------|----------|
| `pytest-httpx` | Pytest fixture | HTTPX users |
| `responses` | Decorator / context manager | Requests users |
| `httpretty` | Context manager | Any HTTP library |
| `respx` | Async-first | Async HTTPX users |

**Example with pytest-httpx:**
```python
@pytest.mark.small
def test_fetch_user(httpx_mock):
    httpx_mock.add_response(
        url="https://api.example.com/users/1",
        json={"id": 1, "name": "Alice"}
    )

    result = fetch_user(1)

    assert result["name"] == "Alice"
```

### pyfakefs

`pyfakefs` provides an in-memory fake filesystem via its `fs` fixture, letting small
tests exercise real file-handling code without touching the real filesystem.

```python
@pytest.mark.small
def test_write_report(fs):  # pyfakefs fixture
    fs.create_file("/data/input.txt", contents="hello")
    write_report("/data/input.txt", "/data/output.txt")
    assert Path("/data/output.txt").read_text() == "HELLO"
```

**Enforcement is suspended while pyfakefs is active.** Every filesystem operation a
test performs while `fs` is installed is already purely in-memory, so there is
nothing for this plugin to block — attempting to intercept pyfakefs's own fake
classes would only produce false `FilesystemAccessViolationError` reports on
operations that never touch the real filesystem.

**Only the function-scoped `fs` fixture is currently verified safe.** Two related
gaps are open, tracked separately:

- Module/class/session-scoped pyfakefs fixtures (`fs_module`, `fs_class`,
  `fs_session`) can leave a fake filesystem resumed for a *sibling* test that
  never requested pyfakefs at all, with no violation reported for that sibling
  ([#256](https://github.com/mikelane/pytest-test-categories/issues/256)).
- Using pyfakefs's own `with Patcher():` context manager directly inside a test
  body (instead of through the `fs` fixture) can reproduce the exact false
  positive this page's recommendation exists to avoid, on a cold import
  ([#257](https://github.com/mikelane/pytest-test-categories/issues/257)).

Until those are resolved, prefer `fs` over `fs_module`/`fs_class`/`fs_session` and
over a bare `with Patcher():` in the test body.

**Caveat:** if a test calls `fs.pause()` to temporarily restore real filesystem
access while pyfakefs is still installed, that real access is *not* detected as a
violation. Enforcement only resumes once pyfakefs itself is torn down (normally
at the `fs` fixture's teardown) — calling `fs.resume()` restores the fake
filesystem but does not restore this plugin's enforcement.

### Time Mocking Libraries

For tests that involve time:

| Library | Performance | API Style |
|---------|-------------|-----------|
| `time-machine` | Fast (C extension) | Decorator / context manager |
| `freezegun` | Slower (pure Python) | Decorator / context manager |

**Example with time-machine:**
```python
import time_machine

@pytest.mark.small
@time_machine.travel("2024-01-01 12:00:00", tick=False)
def test_expiration_check():
    token = create_token(expires_in_seconds=3600)
    assert token.is_valid()

    # Advance time by 2 hours
    with time_machine.travel("2024-01-01 14:00:00", tick=False):
        assert not token.is_valid()
```

## Recommended Stack

For a new project starting with hermetic testing:

```bash
# Core testing
pip install pytest pytest-test-categories

# HTTP mocking (choose one)
pip install pytest-httpx  # if using httpx
pip install responses     # if using requests

# Filesystem mocking
pip install pyfakefs

# General mocking
pip install pytest-mock

# Time mocking
pip install time-machine

# Parallel execution
pip install pytest-xdist
```

Or all at once:
```bash
pip install pytest pytest-test-categories pytest-httpx pyfakefs pytest-mock time-machine pytest-xdist
```

## Known Incompatibilities

None beyond the scoped pyfakefs gaps documented above (module/class/session-scoped fixtures and the manual `Patcher()` context manager — see the [pyfakefs](#pyfakefs) section). If you discover a compatibility issue, please [open an issue](https://github.com/mikelane/pytest-test-categories/issues).

## Integration Testing

The plugin is tested against the following pytest versions:

- pytest >=9.1.1

And Python versions:

- Python 3.11
- Python 3.12
- Python 3.13
- Python 3.14 (preview)
