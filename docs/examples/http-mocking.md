# HTTP Mocking for Small Tests

This guide demonstrates how to use popular HTTP mocking libraries with pytest-test-categories to keep your tests small and hermetic.

## Why Mock HTTP Requests?

Small tests must complete in under 1 second and cannot access the network. Real HTTP requests violate both constraints:

- Network latency adds unpredictable delays
- External services may be unavailable
- Tests become non-deterministic
- Tests couple to external system behavior

**The solution**: Mock HTTP requests at the library level, allowing your code to execute normally while intercepting network calls.

## pytest-httpx (for httpx)

[pytest-httpx](https://colin-b.github.io/pytest_httpx/) provides a `httpx_mock` fixture that intercepts all `httpx` requests.

### Installation

```bash
pip install pytest-httpx
# or
uv add --dev pytest-httpx
```

### Basic Usage

```python
import pytest
import httpx


@pytest.mark.small
def test_fetches_user_profile(httpx_mock):
    """Mock a simple GET request."""
    httpx_mock.add_response(
        url="https://api.example.com/users/123",
        json={"id": "123", "name": "Alice", "email": "alice@example.com"},
    )

    with httpx.Client() as client:
        response = client.get("https://api.example.com/users/123")

    assert response.status_code == 200
    assert response.json()["name"] == "Alice"
```

### Mocking Different HTTP Methods

```python
@pytest.mark.small
def test_creates_user(httpx_mock):
    """Mock a POST request."""
    httpx_mock.add_response(
        url="https://api.example.com/users",
        method="POST",
        json={"id": "456", "name": "Bob"},
        status_code=201,
    )

    with httpx.Client() as client:
        response = client.post(
            "https://api.example.com/users",
            json={"name": "Bob", "email": "bob@example.com"},
        )

    assert response.status_code == 201
    assert response.json()["id"] == "456"


@pytest.mark.small
def test_updates_user(httpx_mock):
    """Mock a PUT request."""
    httpx_mock.add_response(
        url="https://api.example.com/users/123",
        method="PUT",
        json={"id": "123", "name": "Alice Updated"},
    )

    with httpx.Client() as client:
        response = client.put(
            "https://api.example.com/users/123",
            json={"name": "Alice Updated"},
        )

    assert response.json()["name"] == "Alice Updated"


@pytest.mark.small
def test_deletes_user(httpx_mock):
    """Mock a DELETE request."""
    httpx_mock.add_response(
        url="https://api.example.com/users/123",
        method="DELETE",
        status_code=204,
    )

    with httpx.Client() as client:
        response = client.delete("https://api.example.com/users/123")

    assert response.status_code == 204
```

### Mocking Error Responses

```python
@pytest.mark.small
def test_handles_not_found(httpx_mock):
    """Mock a 404 response."""
    httpx_mock.add_response(
        url="https://api.example.com/users/999",
        status_code=404,
        json={"error": "User not found"},
    )

    with httpx.Client() as client:
        response = client.get("https://api.example.com/users/999")

    assert response.status_code == 404


@pytest.mark.small
def test_handles_server_error(httpx_mock):
    """Mock a 500 response."""
    httpx_mock.add_response(
        url="https://api.example.com/users",
        status_code=500,
        json={"error": "Internal server error"},
    )

    with httpx.Client() as client:
        response = client.get("https://api.example.com/users")

    assert response.status_code == 500


@pytest.mark.small
def test_handles_timeout(httpx_mock):
    """Mock a connection timeout."""
    httpx_mock.add_exception(
        httpx.TimeoutException("Connection timed out"),
        url="https://api.example.com/slow-endpoint",
    )

    with httpx.Client() as client:
        with pytest.raises(httpx.TimeoutException):
            client.get("https://api.example.com/slow-endpoint")
```

### URL Pattern Matching

```python
import re


@pytest.mark.small
def test_matches_url_pattern(httpx_mock):
    """Match URLs with regex patterns."""
    httpx_mock.add_response(
        url=re.compile(r"https://api\.example\.com/users/\d+"),
        json={"id": "matched", "name": "Pattern User"},
    )

    with httpx.Client() as client:
        # All these URLs match the pattern
        r1 = client.get("https://api.example.com/users/1")
        r2 = client.get("https://api.example.com/users/999")

    assert r1.json()["id"] == "matched"
    assert r2.json()["id"] == "matched"
```

### Verifying Requests

```python
@pytest.mark.small
def test_verifies_request_was_made(httpx_mock):
    """Verify the correct request was sent."""
    httpx_mock.add_response(
        url="https://api.example.com/users",
        method="POST",
        json={"id": "123"},
    )

    with httpx.Client() as client:
        client.post(
            "https://api.example.com/users",
            json={"name": "Alice"},
            headers={"Authorization": "Bearer token123"},
        )

    # Verify request details
    request = httpx_mock.get_request()
    assert request.method == "POST"
    assert request.headers["Authorization"] == "Bearer token123"
    assert request.content == b'{"name": "Alice"}'
```

## responses (for requests)

[responses](https://github.com/getsentry/responses) mocks the `requests` library.

### Installation

```bash
pip install responses
# or
uv add --dev responses
```

### Basic Usage

```python
import pytest
import requests
import responses


@pytest.mark.small
@responses.activate
def test_fetches_user_profile():
    """Mock a GET request with responses."""
    responses.add(
        responses.GET,
        "https://api.example.com/users/123",
        json={"id": "123", "name": "Alice"},
        status=200,
    )

    response = requests.get("https://api.example.com/users/123")

    assert response.status_code == 200
    assert response.json()["name"] == "Alice"
```

### Using the Fixture Style

```python
@pytest.mark.small
def test_fetches_user_with_fixture(mocked_responses):
    """Use responses as a fixture (requires responses[tests])."""
    mocked_responses.add(
        responses.GET,
        "https://api.example.com/users/123",
        json={"id": "123", "name": "Alice"},
    )

    response = requests.get("https://api.example.com/users/123")

    assert response.json()["name"] == "Alice"
```

### Mocking Multiple Endpoints

```python
@pytest.mark.small
@responses.activate
def test_fetches_user_and_orders():
    """Mock multiple endpoints in one test."""
    responses.add(
        responses.GET,
        "https://api.example.com/users/123",
        json={"id": "123", "name": "Alice"},
    )
    responses.add(
        responses.GET,
        "https://api.example.com/users/123/orders",
        json=[{"order_id": "001", "total": 99.99}],
    )

    user = requests.get("https://api.example.com/users/123").json()
    orders = requests.get("https://api.example.com/users/123/orders").json()

    assert user["name"] == "Alice"
    assert len(orders) == 1
    assert orders[0]["total"] == 99.99
```

### Dynamic Responses with Callbacks

```python
@pytest.mark.small
@responses.activate
def test_dynamic_response():
    """Generate response based on request."""
    def request_callback(request):
        payload = request.body
        return (201, {}, f'{{"received": {payload}}}')

    responses.add_callback(
        responses.POST,
        "https://api.example.com/echo",
        callback=request_callback,
        content_type="application/json",
    )

    response = requests.post(
        "https://api.example.com/echo",
        json={"message": "hello"},
    )

    assert response.status_code == 201
```

### Mocking Errors

```python
@pytest.mark.small
@responses.activate
def test_handles_connection_error():
    """Mock a connection error."""
    responses.add(
        responses.GET,
        "https://api.example.com/unreachable",
        body=requests.exceptions.ConnectionError("Connection refused"),
    )

    with pytest.raises(requests.exceptions.ConnectionError):
        requests.get("https://api.example.com/unreachable")
```

## httpretty (Library-Agnostic)

[httpretty](https://github.com/gabrielfalcao/HTTPretty) works at the socket level, mocking any HTTP library.

### Installation

```bash
pip install httpretty
# or
uv add --dev httpretty
```

### Basic Usage

```python
import pytest
import httpretty as hp
import requests


@pytest.mark.small
@hp.activate
def test_fetches_data():
    """Mock HTTP at socket level."""
    hp.register_uri(
        hp.GET,
        "https://api.example.com/data",
        body='{"status": "ok"}',
        content_type="application/json",
    )

    response = requests.get("https://api.example.com/data")

    assert response.json()["status"] == "ok"
```

### Works with Any HTTP Library

```python
import urllib.request


@pytest.mark.small
@hp.activate
def test_works_with_urllib():
    """httpretty mocks any HTTP library."""
    hp.register_uri(
        hp.GET,
        "https://api.example.com/data",
        body='{"library": "urllib"}',
    )

    with urllib.request.urlopen("https://api.example.com/data") as response:
        data = response.read().decode()

    assert "urllib" in data
```

### Rotating Responses

```python
@pytest.mark.small
@hp.activate
def test_rotating_responses():
    """Return different responses on subsequent calls."""
    hp.register_uri(
        hp.GET,
        "https://api.example.com/counter",
        responses=[
            hp.Response(body='{"count": 1}'),
            hp.Response(body='{"count": 2}'),
            hp.Response(body='{"count": 3}'),
        ],
    )

    r1 = requests.get("https://api.example.com/counter")
    r2 = requests.get("https://api.example.com/counter")
    r3 = requests.get("https://api.example.com/counter")

    assert r1.json()["count"] == 1
    assert r2.json()["count"] == 2
    assert r3.json()["count"] == 3
```

## Choosing the Right Library

| Library | Best For | Async Support |
|---------|----------|---------------|
| pytest-httpx | httpx users | Yes |
| responses | requests users | No |
| httpretty | Multiple HTTP libraries | Limited |
| respx | httpx async | Yes |

### Decision Guide

1. **Using httpx?** Use `pytest-httpx`
2. **Using requests?** Use `responses`
3. **Mixed HTTP libraries?** Use `httpretty`
4. **Async httpx?** Use `respx` (see [Async Testing](async-testing.md))

## Testing Real API Clients

When testing code that wraps HTTP calls, mock at the right level:

### Application Code

```python
# src/user_client.py
import httpx
from dataclasses import dataclass


@dataclass
class User:
    id: str
    name: str
    email: str


class UserClient:
    """Client for the User API."""

    def __init__(self, base_url: str, client: httpx.Client | None = None):
        self.base_url = base_url
        self._client = client or httpx.Client()

    def get_user(self, user_id: str) -> User:
        """Fetch a user by ID."""
        response = self._client.get(f"{self.base_url}/users/{user_id}")
        response.raise_for_status()
        data = response.json()
        return User(id=data["id"], name=data["name"], email=data["email"])

    def create_user(self, name: str, email: str) -> User:
        """Create a new user."""
        response = self._client.post(
            f"{self.base_url}/users",
            json={"name": name, "email": email},
        )
        response.raise_for_status()
        data = response.json()
        return User(id=data["id"], name=data["name"], email=data["email"])
```

### Tests

```python
import pytest
import httpx

from user_client import UserClient, User


@pytest.mark.small
def test_get_user_returns_user_object(httpx_mock):
    """Test that get_user parses response into User object."""
    httpx_mock.add_response(
        url="https://api.example.com/users/123",
        json={"id": "123", "name": "Alice", "email": "alice@example.com"},
    )

    client = UserClient("https://api.example.com")
    user = client.get_user("123")

    assert isinstance(user, User)
    assert user.id == "123"
    assert user.name == "Alice"
    assert user.email == "alice@example.com"


@pytest.mark.small
def test_get_user_raises_on_not_found(httpx_mock):
    """Test that get_user raises HTTPStatusError on 404."""
    httpx_mock.add_response(
        url="https://api.example.com/users/999",
        status_code=404,
    )

    client = UserClient("https://api.example.com")

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        client.get_user("999")

    assert exc_info.value.response.status_code == 404


@pytest.mark.small
def test_create_user_sends_correct_payload(httpx_mock):
    """Test that create_user sends the right request body."""
    httpx_mock.add_response(
        url="https://api.example.com/users",
        method="POST",
        json={"id": "456", "name": "Bob", "email": "bob@example.com"},
        status_code=201,
    )

    client = UserClient("https://api.example.com")
    user = client.create_user("Bob", "bob@example.com")

    # Verify response parsing
    assert user.name == "Bob"

    # Verify request was correct
    request = httpx_mock.get_request()
    assert request.content == b'{"name": "Bob", "email": "bob@example.com"}'
```

## When Tests Need Real HTTP

If your test genuinely needs to make HTTP requests, recategorize it:

```python
@pytest.mark.medium
def test_real_api_health_check():
    """Integration test against local service."""
    import httpx

    # Medium tests can access localhost
    response = httpx.get("http://localhost:8080/health")

    assert response.status_code == 200


@pytest.mark.large
def test_external_api_contract():
    """Contract test against staging API."""
    import httpx

    # Large tests can access external networks
    response = httpx.get("https://staging-api.example.com/health")

    assert response.status_code == 200
```

Do not use override markers to bypass isolation. If a test needs real HTTP, it is not a small test. Recategorize it to the appropriate size.

## Related Documentation

- [Common Patterns](common-patterns.md) - General mocking strategies
- [Network Isolation](network-isolation.md) - How network isolation works
- [Async Testing](async-testing.md) - Async HTTP mocking with respx
- [Container Testing](container-testing.md) - Testing against real services in containers
