# Async Testing with pytest-asyncio

This guide covers testing asynchronous Python code with pytest-test-categories, including timing considerations and async mocking patterns.

## Why Async Testing Matters

Async code introduces unique testing challenges:

- **Event loop management**: Tests need an event loop to run coroutines
- **Concurrency timing**: Race conditions and timing issues
- **Async mocking**: Standard mocks do not work with `await`
- **Resource cleanup**: Async resources need proper cleanup

## Installation

```bash
pip install pytest-asyncio
# or
uv add --dev pytest-asyncio
```

## Basic Configuration

### pytest.ini or pyproject.toml

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"  # Automatically handle async tests
asyncio_default_fixture_loop_scope = "function"  # New in 0.23+
```

Or use the marker explicitly:

```toml
[tool.pytest.ini_options]
asyncio_mode = "strict"  # Require explicit @pytest.mark.asyncio
```

## Basic Async Tests

### Simple Async Function

```python
import pytest


async def fetch_data() -> dict:
    """Simulated async data fetch."""
    return {"status": "ok", "data": [1, 2, 3]}


@pytest.mark.small
@pytest.mark.asyncio
async def test_fetch_data_returns_dict():
    """Test async function returns expected structure."""
    result = await fetch_data()

    assert result["status"] == "ok"
    assert len(result["data"]) == 3
```

### Async Context Managers

```python
import pytest
from contextlib import asynccontextmanager


@asynccontextmanager
async def database_connection():
    """Simulated async database connection."""
    connection = {"connected": True}
    try:
        yield connection
    finally:
        connection["connected"] = False


@pytest.mark.small
@pytest.mark.asyncio
async def test_database_connection_lifecycle():
    """Test async context manager properly cleans up."""
    async with database_connection() as conn:
        assert conn["connected"] is True

    assert conn["connected"] is False
```

### Testing Async Generators

```python
import pytest


async def generate_items(count: int):
    """Async generator yielding items."""
    for i in range(count):
        yield {"id": i, "value": i * 10}


@pytest.mark.small
@pytest.mark.asyncio
async def test_async_generator_yields_items():
    """Test async generator produces expected items."""
    items = [item async for item in generate_items(3)]

    assert len(items) == 3
    assert items[0]["value"] == 0
    assert items[2]["value"] == 20
```

## Async Fixtures

### Basic Async Fixture

```python
import pytest


@pytest.fixture
async def async_client():
    """Async fixture providing a client."""
    client = AsyncClient()
    await client.connect()
    yield client
    await client.disconnect()


@pytest.mark.small
@pytest.mark.asyncio
async def test_with_async_fixture(async_client):
    """Test using async fixture."""
    result = await async_client.get("/status")
    assert result["status"] == "ok"
```

### Async Fixture with Cleanup

```python
import pytest


class AsyncResource:
    def __init__(self):
        self.initialized = False
        self.closed = False

    async def initialize(self):
        self.initialized = True

    async def close(self):
        self.closed = True


@pytest.fixture
async def resource():
    """Async fixture with proper cleanup."""
    r = AsyncResource()
    await r.initialize()

    yield r

    await r.close()


@pytest.mark.small
@pytest.mark.asyncio
async def test_resource_is_initialized(resource):
    """Resource is initialized by fixture."""
    assert resource.initialized is True
    assert resource.closed is False
```

## Timing Considerations

### Async Operations and Test Size

Async tests measure wall-clock time, which includes any `await` calls:

```python
import asyncio


@pytest.mark.small  # Must complete in < 1 second
@pytest.mark.asyncio
async def test_quick_async_operation():
    """This passes: total time < 1 second."""
    await asyncio.sleep(0.1)  # 100ms
    await asyncio.sleep(0.1)  # 100ms
    # Total: ~200ms, well under 1 second


@pytest.mark.small  # FAILS: takes > 1 second
@pytest.mark.asyncio
async def test_slow_async_operation():
    """This fails: total time > 1 second."""
    await asyncio.sleep(2)  # 2 seconds
```

### Concurrent Async Operations

Concurrent operations run in parallel, saving time:

```python
import asyncio


async def slow_operation() -> str:
    await asyncio.sleep(0.3)
    return "done"


@pytest.mark.small  # Passes: concurrent execution
@pytest.mark.asyncio
async def test_concurrent_operations():
    """Three 300ms operations run concurrently in ~300ms total."""
    results = await asyncio.gather(
        slow_operation(),
        slow_operation(),
        slow_operation(),
    )

    assert len(results) == 3
    assert all(r == "done" for r in results)
```

### Timeouts in Async Tests

Use `asyncio.timeout` (Python 3.11+) or `asyncio.wait_for` for explicit timeouts:

```python
import asyncio


@pytest.mark.small
@pytest.mark.asyncio
async def test_with_timeout():
    """Test with explicit timeout."""
    async with asyncio.timeout(0.5):
        result = await quick_operation()

    assert result is not None


@pytest.mark.small
@pytest.mark.asyncio
async def test_timeout_raises():
    """Test that slow operation times out."""
    with pytest.raises(asyncio.TimeoutError):
        async with asyncio.timeout(0.1):
            await asyncio.sleep(1)  # Longer than timeout
```

## Async HTTP Mocking with respx

[respx](https://lundberg.github.io/respx/) mocks `httpx` async clients.

### Installation

```bash
pip install respx
# or
uv add --dev respx
```

### Basic Usage

```python
import pytest
import httpx
import respx


@pytest.mark.small
@pytest.mark.asyncio
@respx.mock
async def test_async_http_request():
    """Mock async HTTP request."""
    respx.get("https://api.example.com/users/1").respond(
        json={"id": 1, "name": "Alice"},
    )

    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/users/1")

    assert response.status_code == 200
    assert response.json()["name"] == "Alice"
```

### Using respx as a Fixture

```python
import pytest
import httpx
import respx


@pytest.fixture
def mock_api():
    """Fixture providing respx mock."""
    with respx.mock:
        yield respx


@pytest.mark.small
@pytest.mark.asyncio
async def test_with_respx_fixture(mock_api):
    """Use respx fixture for cleaner setup."""
    mock_api.get("https://api.example.com/data").respond(
        json={"status": "ok"},
    )

    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")

    assert response.json()["status"] == "ok"
```

### Mocking Multiple Endpoints

```python
@pytest.mark.small
@pytest.mark.asyncio
@respx.mock
async def test_multiple_endpoints():
    """Mock multiple API endpoints."""
    respx.get("https://api.example.com/users/1").respond(
        json={"id": 1, "name": "Alice"},
    )
    respx.get("https://api.example.com/users/1/orders").respond(
        json=[{"order_id": "A001", "total": 99.99}],
    )

    async with httpx.AsyncClient() as client:
        user_response = await client.get("https://api.example.com/users/1")
        orders_response = await client.get("https://api.example.com/users/1/orders")

    assert user_response.json()["name"] == "Alice"
    assert len(orders_response.json()) == 1
```

### Mocking Errors

```python
import httpx
import respx


@pytest.mark.small
@pytest.mark.asyncio
@respx.mock
async def test_handles_network_error():
    """Mock network errors."""
    respx.get("https://api.example.com/unreachable").mock(
        side_effect=httpx.ConnectError("Connection refused"),
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.ConnectError):
            await client.get("https://api.example.com/unreachable")


@pytest.mark.small
@pytest.mark.asyncio
@respx.mock
async def test_handles_timeout():
    """Mock timeout errors."""
    respx.get("https://api.example.com/slow").mock(
        side_effect=httpx.TimeoutException("Request timed out"),
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException):
            await client.get("https://api.example.com/slow")
```

### Verifying Requests

```python
import respx


@pytest.mark.small
@pytest.mark.asyncio
@respx.mock
async def test_request_verification():
    """Verify correct requests were made."""
    route = respx.post("https://api.example.com/users").respond(
        json={"id": 42},
        status_code=201,
    )

    async with httpx.AsyncClient() as client:
        await client.post(
            "https://api.example.com/users",
            json={"name": "Bob", "email": "bob@example.com"},
        )

    assert route.called
    assert route.call_count == 1

    request = route.calls[0].request
    assert b'"name": "Bob"' in request.content
```

## Mocking Async Functions

### Using pytest-mock with Async

```python
import pytest


async def external_api_call(user_id: str) -> dict:
    """External API call to mock."""
    # In reality, this would make an HTTP request
    ...


async def get_user_profile(user_id: str) -> dict:
    """Function that uses external API."""
    data = await external_api_call(user_id)
    return {"id": user_id, "name": data["name"], "active": True}


@pytest.mark.small
@pytest.mark.asyncio
async def test_get_user_profile(mocker):
    """Mock async function with mocker."""
    # Create async mock
    mock_api = mocker.AsyncMock(return_value={"name": "Alice", "email": "alice@example.com"})
    mocker.patch("mymodule.external_api_call", mock_api)

    result = await get_user_profile("123")

    assert result["name"] == "Alice"
    assert result["active"] is True
    mock_api.assert_called_once_with("123")
```

### AsyncMock for Complex Scenarios

```python
import pytest


@pytest.mark.small
@pytest.mark.asyncio
async def test_async_mock_side_effects(mocker):
    """AsyncMock with side effects."""
    mock = mocker.AsyncMock(
        side_effect=[
            {"attempt": 1, "status": "failed"},
            {"attempt": 2, "status": "success"},
        ],
    )

    result1 = await mock()
    result2 = await mock()

    assert result1["status"] == "failed"
    assert result2["status"] == "success"


@pytest.mark.small
@pytest.mark.asyncio
async def test_async_mock_raises(mocker):
    """AsyncMock that raises exception."""
    mock = mocker.AsyncMock(side_effect=ValueError("Invalid input"))

    with pytest.raises(ValueError, match="Invalid input"):
        await mock()
```

## Testing Async Context Managers

```python
import pytest
from contextlib import asynccontextmanager


class AsyncDatabasePool:
    """Simulated async database pool."""

    async def acquire(self):
        return AsyncConnection()

    async def release(self, conn):
        await conn.close()


class AsyncConnection:
    """Simulated async connection."""

    def __init__(self):
        self.closed = False

    async def execute(self, query: str) -> list:
        return [{"id": 1, "name": "Test"}]

    async def close(self):
        self.closed = True


@asynccontextmanager
async def get_connection(pool: AsyncDatabasePool):
    """Async context manager for connections."""
    conn = await pool.acquire()
    try:
        yield conn
    finally:
        await pool.release(conn)


@pytest.mark.small
@pytest.mark.asyncio
async def test_async_context_manager(mocker):
    """Test async context manager behavior."""
    pool = AsyncDatabasePool()

    async with get_connection(pool) as conn:
        result = await conn.execute("SELECT * FROM users")
        assert len(result) == 1

    assert conn.closed is True
```

## Testing Async Iterators

```python
import pytest


class AsyncPaginator:
    """Async iterator for paginated results."""

    def __init__(self, items: list, page_size: int = 2):
        self.items = items
        self.page_size = page_size
        self.offset = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.offset >= len(self.items):
            raise StopAsyncIteration

        page = self.items[self.offset : self.offset + self.page_size]
        self.offset += self.page_size
        return page


@pytest.mark.small
@pytest.mark.asyncio
async def test_async_paginator():
    """Test async iterator produces pages."""
    items = [1, 2, 3, 4, 5]
    paginator = AsyncPaginator(items, page_size=2)

    pages = [page async for page in paginator]

    assert len(pages) == 3
    assert pages[0] == [1, 2]
    assert pages[1] == [3, 4]
    assert pages[2] == [5]
```

## Concurrent Test Execution

### Testing Race Conditions

```python
import asyncio
import pytest


class Counter:
    """Shared counter for concurrency testing."""

    def __init__(self):
        self.value = 0
        self._lock = asyncio.Lock()

    async def increment_unsafe(self):
        """Unsafe increment (race condition)."""
        current = self.value
        await asyncio.sleep(0.001)  # Simulate work
        self.value = current + 1

    async def increment_safe(self):
        """Safe increment with lock."""
        async with self._lock:
            current = self.value
            await asyncio.sleep(0.001)
            self.value = current + 1


@pytest.mark.small
@pytest.mark.asyncio
async def test_safe_concurrent_increment():
    """Test that locked increment is thread-safe."""
    counter = Counter()

    await asyncio.gather(*[counter.increment_safe() for _ in range(10)])

    assert counter.value == 10
```

### Testing Task Cancellation

```python
import asyncio
import pytest


async def long_running_task():
    """Task that can be cancelled."""
    try:
        await asyncio.sleep(10)
        return "completed"
    except asyncio.CancelledError:
        return "cancelled"


@pytest.mark.small
@pytest.mark.asyncio
async def test_task_cancellation():
    """Test that task handles cancellation gracefully."""
    task = asyncio.create_task(long_running_task())

    await asyncio.sleep(0.1)  # Let task start
    task.cancel()

    result = await task
    assert result == "cancelled"
```

## Best Practices

### 1. Use asyncio_mode = "auto"

Reduces boilerplate by auto-detecting async tests:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### 2. Prefer AsyncMock Over Manual Coroutines

```python
# Good: Use AsyncMock
mock = mocker.AsyncMock(return_value={"data": "value"})

# Less good: Manual async wrapper
async def mock_coro():
    return {"data": "value"}
```

### 3. Clean Up Async Resources

Always use `try/finally` or context managers:

```python
@pytest.fixture
async def client():
    """Fixture with guaranteed cleanup."""
    client = AsyncClient()
    await client.connect()
    try:
        yield client
    finally:
        await client.disconnect()
```

### 4. Avoid asyncio.sleep in Small Tests

Replace sleeps with mocks or reduce sleep duration:

```python
# Bad: Long sleep in small test
@pytest.mark.small
@pytest.mark.asyncio
async def test_with_long_sleep():
    await asyncio.sleep(2)  # Exceeds 1 second limit

# Good: Mock the sleep or use tiny delays
@pytest.mark.small
@pytest.mark.asyncio
async def test_with_mocked_time(mocker):
    mocker.patch("asyncio.sleep", new_callable=mocker.AsyncMock)
    await some_function_that_sleeps()
```

### 5. Use Timeouts for External Calls

Even in medium/large tests, use explicit timeouts:

```python
@pytest.mark.medium
@pytest.mark.asyncio
async def test_external_service():
    """Test with explicit timeout."""
    async with asyncio.timeout(30):  # 30 second timeout
        result = await call_external_service()

    assert result is not None
```

## Related Documentation

- [HTTP Mocking](http-mocking.md) - Sync HTTP mocking patterns
- [Common Patterns](common-patterns.md) - General mocking strategies
- [Timing Enforcement](../user-guide/timing-enforcement.md) - How timing limits work
