# Mocking Libraries and Small Tests

This guide explains how mocking libraries work with pytest-test-categories and why mocked tests remain hermetic even when they appear to make external calls.

## Key Insight: Mocks Bypass the Network Blocker by Design

When you use mocking libraries like `responses`, `respx`, `pytest-mock`, or `unittest.mock`, your tests remain fully hermetic even though the code under test appears to make network calls. This is intentional and correct behavior.

**Why?** Mocking libraries intercept HTTP calls at the library level (requests, httpx, etc.) **before** they reach Python's socket layer. Since our network blocker operates at the socket level, mocked calls never trigger it.

```
Without mocking:
  Your code → requests.get() → socket.connect() → BLOCKED by pytest-test-categories

With mocking:
  Your code → requests.get() → responses mock → returns fake data (never reaches socket)
```

## Mocked Tests Are Still Hermetic

A test using mocks is hermetic because:

1. **No actual network traffic occurs** - The mock intercepts the call before any real connection
2. **Tests are deterministic** - Mock responses are controlled and predictable
3. **Tests are fast** - No network latency
4. **Tests are isolated** - No dependency on external services
5. **Tests are parallelizable** - No shared network resources

This is exactly the behavior you want for small tests.

## Common Mocking Libraries

### responses (for requests library)

The `responses` library mocks the `requests` library at the session level:

```python
import pytest
import requests
import responses

@pytest.mark.small
@responses.activate
def test_api_client_fetches_user():
    """This test is hermetic - responses intercepts before socket layer."""
    responses.add(
        responses.GET,
        "https://api.example.com/users/123",
        json={"id": "123", "name": "Alice", "email": "alice@example.com"},
        status=200,
    )

    # This call APPEARS to access the network but never does
    response = requests.get("https://api.example.com/users/123")

    assert response.status_code == 200
    assert response.json()["name"] == "Alice"
```

### respx (for httpx library)

The `respx` library mocks `httpx` at the transport level:

```python
import pytest
import httpx
import respx

@pytest.mark.small
@respx.mock
def test_async_api_client():
    """Hermetic test using respx for httpx."""
    respx.get("https://api.example.com/health").respond(
        json={"status": "healthy"},
        status_code=200,
    )

    response = httpx.get("https://api.example.com/health")

    assert response.json()["status"] == "healthy"
```

### pytest-mock (for any library)

The `pytest-mock` library provides the `mocker` fixture for general-purpose mocking:

```python
import pytest

@pytest.mark.small
def test_user_service_creates_user(mocker):
    """Hermetic test using pytest-mock."""
    # Mock the HTTP client at the point of use
    mock_post = mocker.patch("myapp.services.httpx.post")
    mock_post.return_value.json.return_value = {"id": "456", "name": "Bob"}
    mock_post.return_value.status_code = 201

    from myapp.services import UserService

    service = UserService()
    user = service.create_user(name="Bob", email="bob@example.com")

    assert user["id"] == "456"
    mock_post.assert_called_once()
```

### unittest.mock (standard library)

Python's built-in mocking works the same way:

```python
import pytest
from unittest.mock import Mock, patch

@pytest.mark.small
@patch("requests.get")
def test_weather_service(mock_get):
    """Hermetic test using unittest.mock."""
    mock_response = Mock()
    mock_response.json.return_value = {"temp": 72, "conditions": "sunny"}
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    from myapp.weather import get_current_weather

    weather = get_current_weather("Seattle")

    assert weather["temp"] == 72
```

### VCR.py (record/replay)

VCR.py records real HTTP interactions and replays them in subsequent test runs:

```python
import pytest
import vcr

@pytest.mark.small
@vcr.use_cassette("tests/cassettes/user_api.yaml")
def test_user_api_response_format():
    """Hermetic test using recorded cassette."""
    import requests

    # First run: records real response to cassette file
    # Subsequent runs: replays from cassette (no network access)
    response = requests.get("https://api.example.com/users/123")

    assert "id" in response.json()
    assert "name" in response.json()
```

**Note:** After recording, VCR.py tests are hermetic. During the initial recording, you may need to temporarily use `@pytest.mark.large` or disable enforcement.

## Architecture: How the Layers Work

Understanding the architecture helps explain why this works:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Your Test Code                               │
│   response = requests.get("https://api.example.com/users/1")    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Mocking Library Layer                           │
│   responses, respx, httpretty, pytest-mock, etc.                │
│                                                                 │
│   ✓ Intercepts HTTP calls HERE                                  │
│   ✓ Returns fake response                                       │
│   ✗ Never calls lower layers                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ (only reached if NOT mocked)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   HTTP Library Layer                            │
│   requests, httpx, urllib3, aiohttp, etc.                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Socket Layer                                 │
│   socket.socket.connect()                                       │
│                                                                 │
│   ✗ pytest-test-categories blocks HERE                          │
│   ✗ Only reached if mocking is NOT active                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Operating System                              │
│   TCP/IP network stack                                          │
└─────────────────────────────────────────────────────────────────┘
```

## Best Practices

### 1. Choose the Right Mocking Library

| Library | Best For | HTTP Library |
|---------|----------|--------------|
| `responses` | Simple request/response mocking | `requests` |
| `respx` | Async-first, modern API | `httpx` |
| `aioresponses` | Async HTTP mocking | `aiohttp` |
| `httpretty` | Library-agnostic mocking | Any |
| `pytest-mock` | General-purpose, DI patterns | Any |
| `VCR.py` | Record/replay patterns | Any |

### 2. Mock at the Right Level

**Preferred:** Mock at the HTTP library level (responses, respx)
```python
@responses.activate
def test_user_fetch():
    responses.add(responses.GET, "https://api.example.com/users/1", json={"id": 1})
    # Test code that uses requests internally
```

**Also good:** Mock at your service boundary
```python
def test_user_service(mocker):
    mocker.patch.object(api_client, "get_user", return_value={"id": 1})
    # Test code that uses api_client
```

**Avoid:** Mocking too deep (socket level) - let the blocker do its job

### 3. Keep Mocks Minimal

Only mock what you need to test:

```python
# Good: Minimal mock for the test case
@pytest.mark.small
@responses.activate
def test_handles_404_error():
    responses.add(responses.GET, "https://api.example.com/users/999", status=404)

    with pytest.raises(UserNotFoundError):
        fetch_user(999)

# Avoid: Over-mocking unrelated endpoints
@pytest.mark.small
@responses.activate
def test_handles_404_error():
    responses.add(responses.GET, "https://api.example.com/users/999", status=404)
    responses.add(responses.GET, "https://api.example.com/health", json={})  # Unnecessary
    responses.add(responses.POST, "https://api.example.com/users", json={})  # Unnecessary
    # ...
```

### 4. Use Dependency Injection for Testability

Design your code to accept dependencies, making it easy to inject mocks:

```python
# Production code with DI
class UserService:
    def __init__(self, http_client=None):
        self.client = http_client or httpx.Client()

    def get_user(self, user_id: str) -> dict:
        response = self.client.get(f"https://api.example.com/users/{user_id}")
        return response.json()

# Test code - inject mock client
@pytest.mark.small
def test_user_service_returns_user(mocker):
    mock_client = mocker.Mock()
    mock_client.get.return_value.json.return_value = {"id": "123", "name": "Alice"}

    service = UserService(http_client=mock_client)
    user = service.get_user("123")

    assert user["name"] == "Alice"
```

## Frequently Asked Questions

### Q: If mocks bypass the blocker, how do I know my test is hermetic?

The network blocker is a safety net, not your only line of defense. If your test uses proper mocking:
- No real network calls occur
- The test is deterministic and fast
- The test would pass even if the network were disconnected

The blocker catches cases where you **forgot** to mock, or where mocking failed.

### Q: Should I use mocking or change to medium/large tests?

**Use mocking when:**
- Testing business logic that happens to call external services
- The network call is incidental to what you're testing
- You want fast, deterministic feedback

**Change to medium/large when:**
- Testing the actual integration with an external service
- Verifying real network behavior (timeouts, retries, TLS)
- Testing with real databases or local services

### Q: What if my mock setup fails and a real call gets through?

That's exactly when the network blocker helps. If your mock doesn't properly intercept a call, the blocker will catch it and fail the test with a clear error message, rather than making a real network call that could be slow, flaky, or have side effects.

### Q: Do I need to use `@responses.activate` or similar decorators?

Yes, mocking libraries typically require explicit activation:

| Library | Activation Method |
|---------|-------------------|
| `responses` | `@responses.activate` decorator or context manager |
| `respx` | `@respx.mock` decorator or context manager |
| `aioresponses` | `aioresponses()` context manager |
| `httpretty` | `@httpretty.activate` decorator |
| `pytest-mock` | Automatic via `mocker` fixture |
| `VCR.py` | `@vcr.use_cassette()` decorator |

If you forget activation, the real call will go through and the network blocker will catch it.

## Related Documentation

- [Network Isolation](network-isolation.md) - How the network blocker works
- [Test Sizes](test-sizes.md) - Understanding test categories
- [Common Patterns](../examples/common-patterns.md) - More mocking examples
- [Troubleshooting](../troubleshooting/index.md) - Common issues and solutions
