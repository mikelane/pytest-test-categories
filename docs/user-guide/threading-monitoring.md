# Threading Monitoring for Hermetic Tests

Threading monitoring is a test enforcement mechanism that detects when small tests create threads during execution. Unlike other isolation mechanisms that **block** operations, threading monitoring **warns** about thread creation, allowing tests to continue while flagging potential issues.

When enabled, the pytest-test-categories plugin intercepts thread creation and emits warnings for small tests that use threading.

## Why Threading Monitoring Matters

Tests that create threads introduce several problems:

### Non-Determinism

Multi-threaded tests are inherently non-deterministic:

- Thread scheduling varies between runs
- Race conditions cause intermittent failures
- Test results depend on timing, not logic
- Debugging multi-threaded failures is difficult

### Resource Management

Threads require careful lifecycle management:

- Threads must be properly joined or they leak
- Daemon threads may be killed mid-execution
- Thread cleanup in test teardown is error-prone
- Resource contention between tests

### Isolation Challenges

Threading breaks test isolation:

- Shared state between threads causes interference
- Thread-local storage can leak between tests
- Exceptions in threads may not fail the test
- Deadlocks can hang the entire test suite

### Single-Threaded Principle

Google's test size definitions specify that small tests should be **single-threaded**:

> "Small tests must run in a single process and a single thread."
> - Software Engineering at Google

## Why Monitoring Instead of Blocking?

Unlike network, filesystem, and subprocess isolation which **block** operations, threading monitoring only **warns**. This is because:

1. **Library Dependencies**: Many libraries use threading internally (logging, garbage collection, some test frameworks)
2. **Infrastructure Code**: pytest itself and its plugins may use threads
3. **Breaking Blocking**: Completely blocking threading could break legitimate test infrastructure
4. **Gradual Adoption**: Warnings allow teams to identify issues without immediate test failures

Threading monitoring provides visibility into thread usage while maintaining test suite stability.

## Test Size Restrictions

Threading monitoring follows Google's test size definitions from "Software Engineering at Google":

| Test Size | Threading | Monitoring Behavior |
|-----------|-----------|---------------------|
| Small     | Discouraged | **Warns** on thread creation |
| Medium    | Allowed   | No monitoring |
| Large     | Allowed   | No monitoring |
| XLarge    | Allowed   | No monitoring |

### Small Tests

Small tests should be single-threaded:

- **Deterministic**: No thread scheduling variability
- **Simple**: No synchronization complexity
- **Fast**: No thread creation overhead
- **Reliable**: No race conditions or deadlocks

Threading monitoring emits warnings when small tests create threads, helping teams identify tests that should either be refactored or promoted to medium.

### Medium, Large, and XLarge Tests

These tests may use threading freely for:

- Testing concurrent code
- Load testing with multiple workers
- Integration tests with background tasks
- Performance testing

## How It Works

The plugin intercepts thread creation by patching Python's threading modules:

### Monitored Entry Points

The following thread creation entry points are monitored:

| Entry Point | Module | Description |
|-------------|--------|-------------|
| `threading.Thread` | `threading` | Standard thread class |
| `threading.Timer` | `threading` | Delayed execution (inherits from Thread) |
| `ThreadPoolExecutor` | `concurrent.futures` | Thread pool for parallel execution |
| `ProcessPoolExecutor` | `concurrent.futures` | Process pool (also monitored) |

### Monitoring Behavior

When a small test creates a thread:

1. The monitor intercepts the Thread/Executor constructor
2. It checks if the current test is marked as `small`
3. For small tests, it emits a pytest warning
4. The thread is **allowed to continue** (not blocked)

### Warning Format

When threading is detected in a small test:

```
PytestWarning: Small test 'tests/test_concurrent.py::test_parallel_processing'
uses threading.Thread. Small tests should be single-threaded for determinism.
Consider using @pytest.mark.medium if concurrency testing is required.
```

## Enabling Threading Monitoring

Threading monitoring is controlled by the `test_categories_enforcement` configuration option.

### Configuration via pyproject.toml

```toml
[tool.pytest.ini_options]
# Enable threading monitoring (as part of enforcement)
test_categories_enforcement = "warn"
```

### Configuration via pytest.ini

```ini
[pytest]
test_categories_enforcement = warn
```

### Configuration via Command Line

```bash
pytest --test-categories-enforcement=warn
```

## Enforcement Modes

Threading monitoring behaves consistently in WARN mode. Unlike other isolation mechanisms:

| Mode | Behavior |
|------|----------|
| STRICT | Emits warning (does not block) |
| WARN | Emits warning |
| OFF | No monitoring |

Threading monitoring never blocks thread creation, only warns about it.

## Common Remediation Strategies

### 1. Mock Threading for Unit Tests

Replace thread creation with mocking:

```python
import pytest

@pytest.mark.small
def test_background_task_scheduled(mocker):
    mock_thread = mocker.patch("threading.Thread")

    from myapp.tasks import schedule_background_task
    schedule_background_task("process_data")

    mock_thread.assert_called_once()
    assert mock_thread.call_args[1]["target"].__name__ == "process_data"
```

### 2. Test Thread Logic Separately

Separate the logic from threading:

```python
import pytest

# Production code
def process_items(items):
    """Business logic - no threading here."""
    return [transform(item) for item in items]

def process_items_parallel(items, num_workers=4):
    """Parallel wrapper - tested in medium tests."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        return list(executor.map(transform, items))

# Small test: Test the logic
@pytest.mark.small
def test_process_items():
    items = [1, 2, 3]
    result = process_items(items)
    assert result == [2, 4, 6]  # Assuming transform doubles

# Medium test: Test the parallel execution
@pytest.mark.medium
def test_process_items_parallel():
    items = list(range(100))
    result = process_items_parallel(items, num_workers=4)
    assert len(result) == 100
```

### 3. Use Dependency Injection for Executors

Design code to accept executor interfaces:

```python
from abc import ABC, abstractmethod
from concurrent.futures import Executor, ThreadPoolExecutor
from typing import Callable, TypeVar
import pytest

T = TypeVar("T")

# Executor abstraction
class TaskExecutor(ABC):
    @abstractmethod
    def submit(self, fn: Callable[[], T]) -> T: ...

# Production implementation
class ThreadedExecutor(TaskExecutor):
    def __init__(self, max_workers: int = 4):
        self.pool = ThreadPoolExecutor(max_workers=max_workers)

    def submit(self, fn: Callable[[], T]) -> T:
        future = self.pool.submit(fn)
        return future.result()

# Test implementation (synchronous)
class SyncExecutor(TaskExecutor):
    def submit(self, fn: Callable[[], T]) -> T:
        return fn()  # Execute immediately in same thread

# Code using executor
class DataProcessor:
    def __init__(self, executor: TaskExecutor):
        self.executor = executor

    def process(self, data: list) -> list:
        results = []
        for item in data:
            result = self.executor.submit(lambda: transform(item))
            results.append(result)
        return results

# Small test with sync executor
@pytest.mark.small
def test_data_processor():
    executor = SyncExecutor()
    processor = DataProcessor(executor)

    result = processor.process([1, 2, 3])

    assert result == [2, 4, 6]
```

### 4. Use asyncio Instead of Threading

For I/O-bound concurrency, prefer asyncio:

```python
import asyncio
import pytest

# Async code (no threading)
async def fetch_all(urls: list[str]) -> list[str]:
    async def fetch_one(url: str) -> str:
        # Simulated async fetch
        await asyncio.sleep(0)  # Yield control
        return f"content from {url}"

    return await asyncio.gather(*[fetch_one(url) for url in urls])

@pytest.mark.small
@pytest.mark.asyncio
async def test_fetch_all():
    urls = ["http://a.com", "http://b.com"]
    results = await fetch_all(urls)

    assert len(results) == 2
    assert "content from" in results[0]
```

### 5. Change Test Size

If the test genuinely requires threading:

```python
import pytest

@pytest.mark.medium  # Medium tests can use threading
def test_concurrent_processing():
    from concurrent.futures import ThreadPoolExecutor
    from myapp.processor import process_batch

    items = list(range(1000))

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(process_batch, items))

    assert len(results) == 1000
```

### 6. Suppress Warning for Known Cases

If a warning is expected and acceptable:

```python
import pytest
import warnings

@pytest.mark.small
def test_with_expected_threading():
    # Suppress the specific warning
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Small test.*uses threading")

        # Code that legitimately uses threading
        from myapp.tasks import run_with_timeout
        result = run_with_timeout(my_function, timeout=1.0)

    assert result is not None
```

## Best Practices

### 1. Review Threading Warnings Regularly

Treat threading warnings as technical debt:

```bash
pytest --test-categories-enforcement=warn 2>&1 | grep "uses threading"
```

### 2. Categorize Tests Appropriately

If a test needs threading, it probably should be a medium test:

```python
# Before: Small test with threading (generates warning)
@pytest.mark.small
def test_parallel_computation():
    from concurrent.futures import ThreadPoolExecutor
    # ...

# After: Properly categorized as medium
@pytest.mark.medium
def test_parallel_computation():
    from concurrent.futures import ThreadPoolExecutor
    # ...
```

### 3. Isolate Concurrent Logic

Design code so concurrent execution is separate from business logic:

```
+------------------+     +-------------------+     +------------------+
|  Business Logic  | --> |  Execution Layer  | --> |   Threading      |
|  (Small Tests)   |     |   (Abstraction)   |     |   (Medium Tests) |
+------------------+     +-------------------+     +------------------+
```

### 4. Use Thread-Safe Test Fixtures

When threading is necessary, ensure fixtures are thread-safe:

```python
import threading
import pytest

@pytest.fixture
def thread_safe_counter():
    class Counter:
        def __init__(self):
            self._count = 0
            self._lock = threading.Lock()

        def increment(self):
            with self._lock:
                self._count += 1

        @property
        def value(self):
            with self._lock:
                return self._count

    return Counter()

@pytest.mark.medium
def test_concurrent_increments(thread_safe_counter):
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(thread_safe_counter.increment)
            for _ in range(100)
        ]
        concurrent.futures.wait(futures)

    assert thread_safe_counter.value == 100
```

## Understanding the Warnings

### Common Warning Sources

| Warning Source | Likely Cause | Recommended Action |
|----------------|--------------|-------------------|
| `threading.Thread` | Direct thread creation | Mock or change to medium |
| `ThreadPoolExecutor` | Parallel task execution | Use sync executor or change to medium |
| `ProcessPoolExecutor` | Multiprocessing | Mock or change to medium |
| `Timer` | Delayed execution | Mock or use async patterns |

### Identifying the Root Cause

When you see a threading warning, check:

1. **Is it your code?** The thread might be created by a library.
2. **Is it necessary?** Could the logic be tested without threading?
3. **Is the test size correct?** Should this be a medium test?

## Troubleshooting

### "Threading warning in library code"

Some libraries create threads during import or initialization.

**Solution**: This is expected. Either:
- Ignore the warning if it's from infrastructure
- Mock the library's thread creation
- Mark the test as medium if threading is integral

### "Warning appears for Timer usage"

`threading.Timer` inherits from `threading.Thread`, so it triggers monitoring.

**Solution**: Mock the timer or use a controllable time abstraction:

```python
@pytest.mark.small
def test_scheduled_task(mocker):
    mock_timer = mocker.patch("threading.Timer")

    from myapp.scheduler import schedule_task
    schedule_task("cleanup", delay=60.0)

    mock_timer.assert_called_once()
```

### "ThreadPoolExecutor warning even when mocked"

The warning triggers on class instantiation. Ensure you're patching at the right level:

```python
@pytest.mark.small
def test_parallel_fetch(mocker):
    # Patch the class, not just the submit method
    mock_executor = mocker.patch("concurrent.futures.ThreadPoolExecutor")
    mock_instance = mocker.MagicMock()
    mock_executor.return_value.__enter__.return_value = mock_instance

    from myapp.fetcher import fetch_parallel
    fetch_parallel(["url1", "url2"])

    mock_instance.submit.assert_called()
```

## Related Documentation

- [Test Sizes](test-sizes.md)
- [Sleep Blocking](sleep-blocking.md)
- [Process Isolation](process-isolation.md)
- [Configuration Reference](../configuration.md)
