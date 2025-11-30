# Sleep Blocking for Hermetic Tests

Sleep blocking is a test enforcement mechanism that prevents small tests from calling `time.sleep()` or `asyncio.sleep()` during execution. This ensures tests are **hermetic** and run **without wall-clock time dependencies**.

When enabled, the pytest-test-categories plugin intercepts sleep calls and either blocks them or warns about them, depending on your configuration.

## Why Sleep Blocking Matters

Tests that use sleep introduce several problems:

### Improper Synchronization

Sleep indicates improper synchronization patterns:

- Tests should use proper synchronization primitives (events, conditions)
- Sleep-based waiting is fragile and non-deterministic
- Race conditions are hidden, not solved, by adding sleep
- "It works if I add a sleep" is a red flag

### Slow Tests

Sleep adds pure waiting time:

- A 100ms sleep in 1,000 tests adds 100 seconds to your test suite
- Sleep durations compound with parallel execution
- CI pipelines waste compute time waiting
- Developer productivity drops waiting for slow tests

### Flaky Tests

Sleep-based tests are inherently flaky:

- Timing assumptions vary across machines
- CI environments may be slower than developer machines
- System load affects timing reliability
- "Works on my machine" becomes common

### Non-Determinism

Wall-clock dependencies break reproducibility:

- Test behavior depends on system speed
- Debugging timing issues is difficult
- Flaky failures are hard to reproduce
- Test isolation is compromised

## Test Size Restrictions

Sleep blocking follows Google's test size definitions from "Software Engineering at Google":

| Test Size | Sleep Calls | Rationale |
|-----------|-------------|-----------|
| Small     | **Blocked** | Must be hermetic, no timing dependencies |
| Medium    | Allowed     | May need timing for integration scenarios |
| Large     | Allowed     | Full system tests may require real timing |
| XLarge    | Allowed     | Same as Large |

### Small Tests

Small tests run without wall-clock dependencies:

- **Fast**: No arbitrary waiting
- **Hermetic**: No timing assumptions
- **Deterministic**: Same behavior regardless of system speed
- **Parallelizable**: No timing conflicts with other tests

Sleep blocking enforces determinism by blocking sleep calls in small tests.

### Medium, Large, and XLarge Tests

These tests may use sleep when necessary:

- Waiting for external services to start
- Rate limiting in integration tests
- Simulating real-world timing scenarios
- Testing timeout behavior

## How It Works

The plugin intercepts sleep calls by patching Python's sleep functions:

### Patched Entry Points

The following sleep functions are intercepted:

| Function | Module | Description |
|----------|--------|-------------|
| `time.sleep` | `time` | Standard synchronous sleep |
| `asyncio.sleep` | `asyncio` | Async coroutine sleep |

### Sleep Interception

When a test attempts to sleep:

1. The blocker intercepts the sleep call
2. It extracts the sleep duration
3. It checks if sleeping is allowed based on test size
4. For violations, it either raises an exception (STRICT) or warns (WARN)

### Not Intercepted

The following are intentionally **not** intercepted:

- `threading.Event.wait()` - Has legitimate synchronization uses
- `select.select()` - Used for I/O multiplexing, not arbitrary waiting
- `signal.pause()` - Platform-specific, rare in tests

## Enabling Sleep Blocking

Sleep blocking is controlled by the `test_categories_enforcement` configuration option.

### Configuration via pyproject.toml

```toml
[tool.pytest.ini_options]
# Enable sleep blocking enforcement
test_categories_enforcement = "strict"
```

### Configuration via pytest.ini

```ini
[pytest]
test_categories_enforcement = strict
```

### Configuration via Command Line

```bash
pytest --test-categories-enforcement=strict
```

## Enforcement Modes

The plugin supports three enforcement modes:

### STRICT Mode

```toml
test_categories_enforcement = "strict"
```

In strict mode, sleep violations immediately fail the test with a detailed error message:

```
[TC005] Sleep Call Violation
Test: tests/test_async.py::test_wait_for_result
Category: SMALL

What happened:
  Called time.sleep(0.1) - attempted to sleep for 0.1 seconds

How to fix:
  1. Use proper synchronization instead of sleep (e.g., threading.Event)
  2. Use condition-based waiting with polling and timeout
  3. Mock time.sleep using pytest-mock (mocker.patch)
  4. Use a FakeTimer or controllable time abstraction
  5. Change test category to @pytest.mark.medium (if timing is required)

Documentation: https://pytest-test-categories.readthedocs.io/errors/TC005
```

Use strict mode in CI pipelines to catch violations before merge.

### WARN Mode

```toml
test_categories_enforcement = "warn"
```

In warn mode, sleep violations emit a warning but allow the test to continue:

```
PytestWarning: Sleep violation in test_wait_for_result:
called time.sleep(0.1)
```

Use warn mode during migration to identify violations without breaking the build.

### OFF Mode

```toml
test_categories_enforcement = "off"
```

In off mode, sleep blocking is disabled entirely.

## Per-Test Overrides

Individual tests can override the global enforcement using markers:

### Allow Sleep Calls

```python
import pytest

@pytest.mark.small
@pytest.mark.allow_sleep
def test_special_case():
    """This small test is allowed to use sleep."""
    import time
    time.sleep(0.01)  # Allowed for this test only
```

Use sparingly and document why the override is necessary.

## Common Remediation Strategies

### 1. Use threading.Event for Synchronization

Replace sleep with proper synchronization:

```python
import threading
import pytest

# Bad: Sleep-based waiting
def wait_for_result_bad(worker):
    worker.start()
    import time
    time.sleep(0.1)  # Hope it's done by now
    return worker.result

# Good: Event-based synchronization
def wait_for_result_good(worker, timeout=1.0):
    done_event = threading.Event()

    def on_complete():
        done_event.set()

    worker.on_complete = on_complete
    worker.start()

    if not done_event.wait(timeout=timeout):
        raise TimeoutError("Worker did not complete in time")

    return worker.result

@pytest.mark.small
def test_worker_completes():
    # Use a mock worker that completes immediately
    class MockWorker:
        def __init__(self):
            self.result = "done"
            self.on_complete = None

        def start(self):
            if self.on_complete:
                self.on_complete()

    worker = MockWorker()
    result = wait_for_result_good(worker)

    assert result == "done"
```

### 2. Use Condition-Based Polling

Replace arbitrary sleep with condition checking:

```python
import pytest

# Bad: Fixed sleep
def wait_for_file_bad(path):
    import time
    time.sleep(1.0)  # Hope file exists by now
    return path.exists()

# Good: Condition-based polling
def wait_for_file_good(path, timeout=5.0, poll_interval=0.1):
    import time
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if path.exists():
            return True
        time.sleep(poll_interval)  # Only used in medium tests
    return False

# For small tests, mock the file existence
@pytest.mark.small
def test_file_processing(mocker, tmp_path):
    test_file = tmp_path / "data.txt"
    test_file.write_text("content")  # File exists immediately

    from myapp.files import process_when_ready
    result = process_when_ready(test_file)

    assert result == "processed"
```

### 3. Mock time.sleep

Use pytest-mock to eliminate sleep:

```python
import pytest

@pytest.mark.small
def test_retry_logic(mocker):
    mock_sleep = mocker.patch("time.sleep")

    from myapp.retry import retry_with_backoff

    call_count = 0
    def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Failed")
        return "success"

    result = retry_with_backoff(flaky_function, max_retries=3)

    assert result == "success"
    assert call_count == 3
    assert mock_sleep.call_count == 2  # Slept twice between retries
```

### 4. Use Controllable Time Abstraction

Design code to use injectable time sources:

```python
from abc import ABC, abstractmethod
import time
import pytest

# Time abstraction interface
class Clock(ABC):
    @abstractmethod
    def now(self) -> float: ...

    @abstractmethod
    def sleep(self, seconds: float) -> None: ...

# Production implementation
class SystemClock(Clock):
    def now(self) -> float:
        return time.time()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)

# Test implementation
class FakeClock(Clock):
    def __init__(self, initial_time: float = 0.0):
        self._time = initial_time
        self.sleep_calls: list[float] = []

    def now(self) -> float:
        return self._time

    def sleep(self, seconds: float) -> None:
        self.sleep_calls.append(seconds)
        self._time += seconds

    def advance(self, seconds: float) -> None:
        self._time += seconds

# Code using clock abstraction
class RateLimiter:
    def __init__(self, clock: Clock, rate: float):
        self.clock = clock
        self.min_interval = 1.0 / rate
        self.last_call = 0.0

    def wait(self) -> None:
        elapsed = self.clock.now() - self.last_call
        if elapsed < self.min_interval:
            self.clock.sleep(self.min_interval - elapsed)
        self.last_call = self.clock.now()

# Small test with fake clock
@pytest.mark.small
def test_rate_limiter():
    clock = FakeClock(initial_time=100.0)
    limiter = RateLimiter(clock, rate=10.0)  # 10 calls per second

    limiter.wait()  # First call, no wait
    limiter.wait()  # Should wait 0.1 seconds

    assert len(clock.sleep_calls) == 1
    assert clock.sleep_calls[0] == pytest.approx(0.1, abs=0.01)
```

### 5. Use freezegun or time-machine

For tests that need to manipulate time:

```python
from freezegun import freeze_time
import pytest

@pytest.mark.small
@freeze_time("2024-01-15 12:00:00")
def test_time_based_logic():
    from myapp.scheduling import is_business_hours

    assert is_business_hours() is True

@pytest.mark.small
@freeze_time("2024-01-15 03:00:00")
def test_outside_business_hours():
    from myapp.scheduling import is_business_hours

    assert is_business_hours() is False
```

### 6. Use asyncio.Event for Async Code

Replace asyncio.sleep with proper async synchronization:

```python
import asyncio
import pytest

# Bad: Sleep-based async waiting
async def wait_for_result_bad(task):
    await asyncio.sleep(0.1)
    return task.result()

# Good: Event-based async waiting
async def wait_for_result_good(task, timeout=1.0):
    done_event = asyncio.Event()

    def on_complete(future):
        done_event.set()

    task.add_done_callback(on_complete)

    try:
        await asyncio.wait_for(done_event.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        raise TimeoutError("Task did not complete in time")

    return task.result()

@pytest.mark.small
@pytest.mark.asyncio
async def test_async_task():
    # Use a task that completes immediately
    async def instant_task():
        return "done"

    task = asyncio.create_task(instant_task())
    result = await wait_for_result_good(task)

    assert result == "done"
```

### 7. Change Test Size

If the test legitimately requires timing:

```python
import pytest

@pytest.mark.medium  # Medium tests can use sleep
def test_rate_limiter_integration():
    import time
    from myapp.limiter import RateLimiter

    limiter = RateLimiter(rate=10.0)  # 10 per second

    start = time.monotonic()
    for _ in range(5):
        limiter.wait()
    elapsed = time.monotonic() - start

    # Should take approximately 0.4 seconds (5 calls with 0.1s spacing)
    assert elapsed >= 0.4
    assert elapsed < 0.6
```

## Best Practices

### 1. Start with WARN Mode

When first enabling sleep blocking, use warn mode to identify all violations:

```bash
pytest --test-categories-enforcement=warn 2>&1 | grep "Sleep violation"
```

### 2. Identify Why Sleep is Used

Common reasons for sleep in tests:

| Reason | Better Alternative |
|--------|-------------------|
| Waiting for async operation | Use proper synchronization (Event, Condition) |
| Waiting for background thread | Use Event.wait() with timeout |
| Rate limiting | Mock time.sleep or use FakeClock |
| Simulating delays | Mock the delay mechanism |
| Flaky test mitigation | Fix the root cause of flakiness |

### 3. Design for Testability

Make timing behavior injectable:

```python
# Production code with injectable delay
async def fetch_with_retry(url: str, delay_fn=asyncio.sleep):
    for attempt in range(3):
        try:
            return await fetch(url)
        except Exception:
            if attempt < 2:
                await delay_fn(1.0 * (attempt + 1))
    raise Exception("All retries failed")

# Test with instant "delays"
@pytest.mark.small
@pytest.mark.asyncio
async def test_fetch_retries():
    async def no_delay(seconds):
        pass  # Instant "sleep"

    # ... test with no_delay as delay_fn
```

### 4. Use pytest Plugins for Async Testing

For async code, use `pytest-asyncio`:

```python
import pytest

@pytest.mark.small
@pytest.mark.asyncio
async def test_async_function():
    # Async test without sleep
    result = await my_async_function()
    assert result == expected
```

## Troubleshooting

### "SleepViolationError" in library code

Some libraries call sleep internally:
- Retry libraries
- Connection pools
- Rate limiters

**Solution**: Mock at the library level or use a higher-level abstraction.

### "asyncio.sleep not being caught"

Ensure the async sleep is actually being called. The blocker patches `asyncio.sleep` at module import time.

**Solution**: Ensure tests are running with the correct pytest configuration.

### "Test works with sleep but fails without"

This indicates a synchronization bug. The sleep was hiding a race condition.

**Solution**: Find and fix the race condition using proper synchronization.

## Related Documentation

- [Architecture Decision Record: Sleep Isolation](../architecture/adr-005-sleep-isolation.md)
- [Test Sizes](test-sizes.md)
- [Threading Monitoring](threading-monitoring.md)
- [Configuration Reference](../configuration.md)
