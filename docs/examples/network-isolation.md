# Network Isolation Examples

> **PLANNED FEATURE - Coming in v0.4.0**
>
> These examples demonstrate the **expected behavior** once network isolation is fully released.
> The `NetworkBlockerPort` interface exists (PR #74), but pytest hook integration is planned
> for PR #69. The error messages, CLI options, and markers shown below are **not yet available**.
>
> Track progress: [Issue #70](https://github.com/mikelane/pytest-test-categories/issues/70)

## Prerequisites

To follow these examples when the feature is released, you may want to install optional mocking libraries:

```bash
# For mocking requests library
pip install responses

# For mocking httpx library
pip install respx

# For mocking Redis
pip install fakeredis
```

These libraries are **not required** by pytest-test-categories but are recommended for writing
hermetic tests that mock network calls.

---

This document provides practical examples of tests that violate network isolation and how to fix them.

## Example 1: HTTP API Client

### Violating Test

This test makes a real HTTP request, violating small test requirements:

```python
# tests/test_user_api.py
import pytest
import requests


@pytest.mark.small
def test_fetch_user_profile():
    """Fetch user profile from API."""
    response = requests.get("https://api.example.com/users/123")

    assert response.status_code == 200
    assert response.json()["id"] == "123"
```

**Error:**

```
HermeticityViolationError: Network access attempted
Attempted connection to: api.example.com:443
```

### Fixed Test Using `responses`

```python
# tests/test_user_api.py
import pytest
import responses
import requests


@pytest.mark.small
@responses.activate
def test_fetch_user_profile():
    """Fetch user profile from API."""
    # Arrange: Set up mock response
    responses.add(
        responses.GET,
        "https://api.example.com/users/123",
        json={"id": "123", "name": "Alice", "email": "alice@example.com"},
        status=200,
    )

    # Act: Make the request (intercepted by responses)
    response = requests.get("https://api.example.com/users/123")

    # Assert: Verify the response
    assert response.status_code == 200
    assert response.json()["id"] == "123"
    assert response.json()["name"] == "Alice"
```

### Fixed Test Using Dependency Injection

```python
# src/user_service.py
from dataclasses import dataclass

import httpx


@dataclass
class User:
    id: str
    name: str
    email: str


def fetch_user(user_id: str, client: httpx.Client | None = None) -> User:
    """Fetch user from API.

    Args:
        user_id: The user ID to fetch.
        client: Optional HTTP client. Uses default if not provided.

    Returns:
        User object with profile data.

    """
    client = client or httpx.Client()
    response = client.get(f"https://api.example.com/users/{user_id}")
    response.raise_for_status()
    data = response.json()
    return User(id=data["id"], name=data["name"], email=data["email"])
```

```python
# tests/test_user_service.py
import pytest

from user_service import User, fetch_user


@pytest.mark.small
def test_fetch_user_returns_user_object(mocker):
    """Fetch user returns properly structured User object."""
    # Arrange: Create mock client
    mock_response = mocker.Mock()
    mock_response.json.return_value = {
        "id": "123",
        "name": "Alice",
        "email": "alice@example.com",
    }
    mock_response.raise_for_status = mocker.Mock()

    mock_client = mocker.Mock()
    mock_client.get.return_value = mock_response

    # Act: Call with mock client
    user = fetch_user("123", client=mock_client)

    # Assert: Verify user object
    assert isinstance(user, User)
    assert user.id == "123"
    assert user.name == "Alice"
    assert user.email == "alice@example.com"

    # Verify correct URL was called
    mock_client.get.assert_called_once_with("https://api.example.com/users/123")
```

## Example 2: Database Integration

### Violating Test

This test connects to a real PostgreSQL database:

```python
# tests/test_user_repository.py
import pytest
import psycopg2


@pytest.mark.small
def test_find_user_by_email():
    """Find user by email address."""
    conn = psycopg2.connect(
        host="localhost",
        database="testdb",
        user="testuser",
        password="testpass",
    )
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM users WHERE email = %s", ("alice@example.com",))
    result = cursor.fetchone()

    assert result is not None
    assert result[1] == "Alice"
```

**Error:**

```
HermeticityViolationError: Network access attempted
Attempted connection to: localhost:5432
```

### Fixed Test Using Repository Pattern

```python
# src/user_repository.py
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class User:
    id: str
    name: str
    email: str


class UserRepository(ABC):
    """Abstract repository for user persistence."""

    @abstractmethod
    def find_by_email(self, email: str) -> User | None:
        """Find user by email address."""


class PostgresUserRepository(UserRepository):
    """PostgreSQL implementation of user repository."""

    def __init__(self, connection):
        self._conn = connection

    def find_by_email(self, email: str) -> User | None:
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT id, name, email FROM users WHERE email = %s",
            (email,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return User(id=row[0], name=row[1], email=row[2])
```

```python
# tests/fakes/fake_user_repository.py
from user_repository import User, UserRepository


class FakeUserRepository(UserRepository):
    """In-memory fake for testing."""

    def __init__(self, users: list[User] | None = None):
        self._users = {u.email: u for u in (users or [])}

    def find_by_email(self, email: str) -> User | None:
        return self._users.get(email)

    def add(self, user: User) -> None:
        """Add user to fake repository."""
        self._users[user.email] = user
```

```python
# tests/test_user_repository.py
import pytest

from fakes.fake_user_repository import FakeUserRepository
from user_repository import User


@pytest.mark.small
def test_find_user_by_email_returns_matching_user():
    """Find user by email returns the matching user."""
    # Arrange: Create fake with test data
    alice = User(id="123", name="Alice", email="alice@example.com")
    repo = FakeUserRepository(users=[alice])

    # Act: Find user
    result = repo.find_by_email("alice@example.com")

    # Assert: Correct user returned
    assert result is not None
    assert result.id == "123"
    assert result.name == "Alice"


@pytest.mark.small
def test_find_user_by_email_returns_none_for_unknown():
    """Find user by email returns None for unknown email."""
    # Arrange: Empty repository
    repo = FakeUserRepository()

    # Act: Find non-existent user
    result = repo.find_by_email("unknown@example.com")

    # Assert: None returned
    assert result is None
```

### Integration Test (Medium)

For tests that need the real database:

```python
# tests/integration/test_postgres_user_repository.py
import pytest
import psycopg2

from user_repository import PostgresUserRepository


@pytest.fixture
def postgres_connection():
    """Create PostgreSQL connection for integration tests."""
    conn = psycopg2.connect(
        host="localhost",
        database="testdb",
        user="testuser",
        password="testpass",
    )
    yield conn
    conn.close()


@pytest.mark.medium  # Medium tests can access localhost
def test_postgres_repository_finds_user(postgres_connection):
    """PostgreSQL repository finds existing user."""
    repo = PostgresUserRepository(postgres_connection)

    result = repo.find_by_email("alice@example.com")

    assert result is not None
```

## Example 3: Redis Cache

### Violating Test

```python
# tests/test_cache.py
import pytest
import redis


@pytest.mark.small
def test_cache_stores_value():
    """Cache stores and retrieves values."""
    r = redis.Redis(host="localhost", port=6379)
    r.set("key", "value")
    result = r.get("key")

    assert result == b"value"
```

**Error:**

```
HermeticityViolationError: Network access attempted
Attempted connection to: localhost:6379
```

### Fixed Test Using fakeredis

```python
# tests/test_cache.py
import pytest
import fakeredis


@pytest.mark.small
def test_cache_stores_value():
    """Cache stores and retrieves values."""
    r = fakeredis.FakeRedis()
    r.set("key", "value")
    result = r.get("key")

    assert result == b"value"
```

### Fixed Test Using Cache Abstraction

```python
# src/cache.py
from abc import ABC, abstractmethod


class Cache(ABC):
    """Abstract cache interface."""

    @abstractmethod
    def get(self, key: str) -> bytes | None:
        """Get value from cache."""

    @abstractmethod
    def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """Set value in cache."""


class RedisCache(Cache):
    """Redis implementation."""

    def __init__(self, client):
        self._client = client

    def get(self, key: str) -> bytes | None:
        return self._client.get(key)

    def set(self, key: str, value: str, ttl: int | None = None) -> None:
        self._client.set(key, value, ex=ttl)
```

```python
# tests/fakes/fake_cache.py
from cache import Cache


class FakeCache(Cache):
    """In-memory cache for testing."""

    def __init__(self):
        self._store: dict[str, bytes] = {}

    def get(self, key: str) -> bytes | None:
        return self._store.get(key)

    def set(self, key: str, value: str, ttl: int | None = None) -> None:
        self._store[key] = value.encode()
```

```python
# tests/test_cache.py
import pytest

from fakes.fake_cache import FakeCache


@pytest.mark.small
def test_cache_stores_and_retrieves_value():
    """Cache stores and retrieves values correctly."""
    cache = FakeCache()

    cache.set("user:123", "Alice")
    result = cache.get("user:123")

    assert result == b"Alice"


@pytest.mark.small
def test_cache_returns_none_for_missing_key():
    """Cache returns None for missing keys."""
    cache = FakeCache()

    result = cache.get("nonexistent")

    assert result is None
```

## Example 4: External API with httpx

### Violating Test

```python
# tests/test_weather.py
import pytest
import httpx


@pytest.mark.small
def test_get_current_temperature():
    """Get current temperature for a city."""
    response = httpx.get(
        "https://api.weather.com/current",
        params={"city": "Seattle"},
    )
    data = response.json()

    assert "temperature" in data
```

### Fixed Test Using respx

```python
# tests/test_weather.py
import pytest
import httpx
import respx


@pytest.mark.small
@respx.mock
def test_get_current_temperature():
    """Get current temperature for a city."""
    # Arrange: Mock the weather API
    respx.get(
        "https://api.weather.com/current",
        params={"city": "Seattle"},
    ).respond(json={"temperature": 55, "unit": "fahrenheit"})

    # Act: Make the request
    response = httpx.get(
        "https://api.weather.com/current",
        params={"city": "Seattle"},
    )
    data = response.json()

    # Assert: Verify response
    assert data["temperature"] == 55
    assert data["unit"] == "fahrenheit"
```

## Example 5: Async HTTP Client

### Violating Test

```python
# tests/test_async_api.py
import pytest
import httpx


@pytest.mark.small
@pytest.mark.asyncio
async def test_async_fetch_data():
    """Fetch data asynchronously."""
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        data = response.json()

    assert data["status"] == "ok"
```

### Fixed Test Using respx

```python
# tests/test_async_api.py
import pytest
import httpx
import respx


@pytest.mark.small
@pytest.mark.asyncio
@respx.mock
async def test_async_fetch_data():
    """Fetch data asynchronously."""
    # Arrange: Mock the API endpoint
    respx.get("https://api.example.com/data").respond(
        json={"status": "ok", "data": [1, 2, 3]}
    )

    # Act: Make async request
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        data = response.json()

    # Assert: Verify response
    assert data["status"] == "ok"
    assert data["data"] == [1, 2, 3]
```

## Configuration Examples

### pyproject.toml

```toml
[tool.pytest.ini_options]
# Markers for test sizes
markers = [
    "small: Fast, hermetic unit tests (< 1s)",
    "medium: Integration tests with local services (< 5min)",
    "large: End-to-end tests (< 15min)",
    "xlarge: Extended tests (< 15min)",
    "allow_network: Override network blocking for specific test",
]

# Enable strict network isolation
test_categories_enforcement = "strict"
```

### pytest.ini

```ini
[pytest]
markers =
    small: Fast, hermetic unit tests (< 1s)
    medium: Integration tests with local services (< 5min)
    large: End-to-end tests (< 15min)
    xlarge: Extended tests (< 15min)
    allow_network: Override network blocking for specific test

test_categories_enforcement = strict
```

### CI Pipeline Example

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          pip install uv
          uv sync --all-groups

      - name: Run tests with network isolation
        run: |
          uv run pytest --test-categories-enforcement=strict
```

### Gradual Migration Example

```yaml
# .github/workflows/test.yml
jobs:
  # Warn about violations but don't fail
  test-with-warnings:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests (warn mode)
        run: |
          uv run pytest --test-categories-enforcement=warn 2>&1 | tee test-output.txt
          grep "Network access violation" test-output.txt > violations.txt || true
          if [ -s violations.txt ]; then
            echo "::warning::Network violations detected (see violations.txt)"
          fi

  # Strict enforcement on main branch
  test-strict:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Run tests (strict mode)
        run: |
          uv run pytest --test-categories-enforcement=strict
```

## Related Documentation

- [User Guide: Network Isolation](../user-guide/network-isolation.md)
- [Troubleshooting: Network Violations](../troubleshooting/network-violations.md)
- [ADR-001: Network Isolation](../architecture/adr-001-network-isolation.md)
