# Common Testing Patterns

This guide covers common patterns for writing tests that work well with pytest-test-categories, including mocking strategies, fixture patterns, and test organization approaches.

## Mocking External Services for Small Tests

Small tests must be hermetic - they cannot make network calls or access external services. Here are proven patterns for mocking different types of dependencies.

### HTTP Clients with pytest-httpx

The [pytest-httpx](https://colin-b.github.io/pytest_httpx/) library intercepts HTTP requests made with `httpx`:

```python
import pytest
import httpx

@pytest.mark.small
def test_api_client_fetches_user(httpx_mock):
    """Mock HTTP response for testing API client behavior."""
    httpx_mock.add_response(
        url="https://api.example.com/users/1",
        json={"id": 1, "name": "Alice", "email": "alice@example.com"},
    )

    with httpx.Client() as client:
        response = client.get("https://api.example.com/users/1")

    assert response.json()["name"] == "Alice"
```

#### Mocking Different HTTP Methods

```python
@pytest.mark.small
def test_api_client_creates_user(httpx_mock):
    """Mock POST request."""
    httpx_mock.add_response(
        url="https://api.example.com/users",
        method="POST",
        json={"id": 42, "name": "Bob"},
        status_code=201,
    )

    with httpx.Client() as client:
        response = client.post(
            "https://api.example.com/users",
            json={"name": "Bob", "email": "bob@example.com"},
        )

    assert response.status_code == 201
    assert response.json()["id"] == 42
```

#### Mocking Error Responses

```python
@pytest.mark.small
def test_api_client_handles_errors(httpx_mock):
    """Mock error response."""
    httpx_mock.add_response(
        url="https://api.example.com/users/999",
        status_code=404,
    )

    with httpx.Client() as client:
        response = client.get("https://api.example.com/users/999")

    assert response.status_code == 404
```

### HTTP Clients with responses (for requests library)

If you use the `requests` library, use [responses](https://github.com/getsentry/responses):

```python
import pytest
import responses
import requests

@pytest.mark.small
@responses.activate
def test_fetch_user_profile():
    """Mock requests library HTTP calls."""
    responses.add(
        responses.GET,
        "https://api.example.com/users/1",
        json={"id": 1, "name": "Alice"},
        status=200,
    )

    response = requests.get("https://api.example.com/users/1")

    assert response.json()["name"] == "Alice"
```

### Database Mocking with Fakes

Instead of mocking individual database calls, create a fake implementation of your repository:

#### Repository Interface

```python
# src/repositories.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class User:
    id: int
    name: str
    email: str

class UserRepository(ABC):
    """Abstract repository interface for user persistence."""

    @abstractmethod
    def get_by_id(self, user_id: int) -> User | None:
        """Find user by ID."""

    @abstractmethod
    def save(self, user: User) -> User:
        """Save user and return with assigned ID."""

    @abstractmethod
    def delete(self, user_id: int) -> bool:
        """Delete user by ID. Returns True if deleted."""
```

#### Fake Implementation for Testing

```python
# tests/fakes.py
from repositories import User, UserRepository

class FakeUserRepository(UserRepository):
    """In-memory fake repository for testing."""

    def __init__(self):
        self._users: dict[int, User] = {}
        self._next_id = 1

    def get_by_id(self, user_id: int) -> User | None:
        return self._users.get(user_id)

    def save(self, user: User) -> User:
        if user.id == 0:
            user = User(id=self._next_id, name=user.name, email=user.email)
            self._next_id += 1
        self._users[user.id] = user
        return user

    def delete(self, user_id: int) -> bool:
        if user_id in self._users:
            del self._users[user_id]
            return True
        return False
```

#### Using the Fake in Tests

```python
import pytest
from fakes import FakeUserRepository
from repositories import User

@pytest.mark.small
class DescribeUserRepository:
    """Tests for user repository behavior using fake implementation."""

    def test_saves_and_retrieves_user(self):
        repo = FakeUserRepository()
        user = User(id=0, name="Alice", email="alice@example.com")

        saved = repo.save(user)
        retrieved = repo.get_by_id(saved.id)

        assert retrieved is not None
        assert retrieved.name == "Alice"

    def test_returns_none_for_missing_user(self):
        repo = FakeUserRepository()

        result = repo.get_by_id(999)

        assert result is None
```

### Redis with fakeredis

Use [fakeredis](https://github.com/cunla/fakeredis-py) for Redis testing:

```python
import pytest
import fakeredis

@pytest.mark.small
def test_cache_stores_value():
    """Use fakeredis for in-memory Redis testing."""
    redis_client = fakeredis.FakeRedis()

    redis_client.set("user:1", "Alice")
    result = redis_client.get("user:1")

    assert result == b"Alice"
```

## Fixture Patterns by Test Size

### Small Test Fixtures

Small test fixtures should create data in memory with no I/O:

```python
# tests/conftest.py
import pytest
from dataclasses import dataclass

@dataclass
class Product:
    id: int
    name: str
    price: float

@pytest.fixture
def sample_products() -> list[Product]:
    """Provide sample products for testing.

    This fixture creates pure Python objects - no I/O required.
    Safe for small tests.
    """
    return [
        Product(id=1, name="Widget", price=9.99),
        Product(id=2, name="Gadget", price=19.99),
        Product(id=3, name="Tool", price=29.99),
    ]

@pytest.fixture
def product_repository(sample_products):
    """Provide a pre-populated fake repository.

    Uses in-memory fake - safe for small tests.
    """
    from fakes import FakeProductRepository

    repo = FakeProductRepository()
    for product in sample_products:
        repo.save(product)
    return repo
```

### File Fixtures with tmp_path

Use `tmp_path` for tests that need file operations:

```python
@pytest.fixture
def csv_file(tmp_path):
    """Create a sample CSV file for testing.

    Uses tmp_path for isolated filesystem access.
    Safe for small tests.
    """
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("name,price\nWidget,9.99\nGadget,19.99\n")
    return csv_path

@pytest.fixture
def json_file(tmp_path):
    """Create a sample JSON file for testing."""
    import json

    json_path = tmp_path / "data.json"
    json_path.write_text(json.dumps([
        {"name": "Widget", "price": 9.99},
        {"name": "Gadget", "price": 19.99},
    ]))
    return json_path

@pytest.fixture
def data_directory(tmp_path, csv_file, json_file):
    """Create a directory with multiple data files.

    Composes other fixtures for more complex scenarios.
    """
    return {
        "root": tmp_path,
        "csv": csv_file,
        "json": json_file,
    }
```

### Medium Test Fixtures

Medium test fixtures can access localhost and containers:

```python
# tests/medium/conftest.py
import pytest
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

@pytest.fixture
def local_http_server():
    """Start a local HTTP server for testing.

    Creates a real HTTP server on localhost.
    Appropriate for medium tests only.
    """
    class SimpleHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')

        def log_message(self, format, *args):
            pass  # Suppress logs

    server = HTTPServer(("127.0.0.1", 0), SimpleHandler)
    port = server.server_address[1]

    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    yield f"http://127.0.0.1:{port}"

    server.shutdown()
```

### Testcontainers Fixtures

For database integration tests, use testcontainers:

```python
# tests/medium/conftest.py
import pytest

try:
    from testcontainers.postgres import PostgresContainer
    HAS_TESTCONTAINERS = True
except ImportError:
    HAS_TESTCONTAINERS = False

@pytest.fixture
def postgres_container():
    """Start a PostgreSQL container for integration testing.

    Requires Docker. Appropriate for medium tests with
    allow_external_systems=True marker.
    """
    if not HAS_TESTCONTAINERS:
        pytest.skip("testcontainers not installed")

    with PostgresContainer("postgres:15-alpine") as postgres:
        # Initialize schema
        import psycopg2
        conn = psycopg2.connect(
            host=postgres.get_container_host_ip(),
            port=postgres.get_exposed_port(5432),
            database=postgres.dbname,
            user=postgres.username,
            password=postgres.password,
        )
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL
                )
            """)
            conn.commit()
        conn.close()

        yield postgres
```

Usage:

```python
@pytest.mark.skipif(not HAS_TESTCONTAINERS, reason="testcontainers not installed")
@pytest.mark.medium(allow_external_systems=True)
def test_database_integration(postgres_container):
    """Test with real PostgreSQL database."""
    import psycopg2

    conn = psycopg2.connect(
        host=postgres_container.get_container_host_ip(),
        port=postgres_container.get_exposed_port(5432),
        database=postgres_container.dbname,
        user=postgres_container.username,
        password=postgres_container.password,
    )

    with conn.cursor() as cur:
        cur.execute("INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id",
                    ("Alice", "alice@example.com"))
        user_id = cur.fetchone()[0]
        conn.commit()

    assert user_id > 0
    conn.close()
```

## Test Organization Strategies

### By Feature

Organize tests by feature area:

```
tests/
    users/
        test_user_creation.py
        test_user_authentication.py
        test_user_profile.py
    products/
        test_product_catalog.py
        test_product_search.py
    orders/
        test_order_creation.py
        test_order_fulfillment.py
    conftest.py
```

Mark tests with appropriate sizes within each file:

```python
# tests/users/test_user_creation.py
import pytest

@pytest.mark.small
class DescribeUserCreation:
    """Unit tests for user creation logic."""

    def test_creates_user_with_valid_data(self, user_repository):
        ...

    def test_rejects_duplicate_email(self, user_repository):
        ...

@pytest.mark.medium
class DescribeUserCreationIntegration:
    """Integration tests for user creation with database."""

    def test_persists_user_to_database(self, postgres_container):
        ...
```

### By Test Size

Organize tests by size for clear separation:

```
tests/
    small/
        test_models.py
        test_validation.py
        test_utils.py
    medium/
        test_database.py
        test_api_integration.py
    large/
        test_e2e_workflow.py
    conftest.py
```

Apply markers via directory conftest:

```python
# tests/small/conftest.py
import pytest

def pytest_collection_modifyitems(items):
    """Automatically mark all tests in small/ as small tests."""
    for item in items:
        if "/small/" in str(item.fspath):
            item.add_marker(pytest.mark.small)
```

### Hybrid Approach

Combine both approaches:

```
tests/
    unit/                    # All small tests by feature
        users/
            test_creation.py
            test_validation.py
        products/
            test_pricing.py
    integration/             # All medium tests by feature
        users/
            test_database.py
        products/
            test_search.py
    e2e/                     # All large tests
        test_checkout_flow.py
    conftest.py
```

## Parametrization Best Practices

### Simple Parametrization

```python
import pytest

@pytest.mark.small
@pytest.mark.parametrize(
    ("input_value", "expected_output"),
    [
        (0, 0),
        (1, 1),
        (2, 4),
        (3, 9),
        (10, 100),
    ],
)
def test_square(input_value, expected_output):
    """Test square function with multiple inputs."""
    assert square(input_value) == expected_output
```

### Parametrization with IDs

```python
@pytest.mark.small
@pytest.mark.parametrize(
    ("email", "is_valid"),
    [
        pytest.param("user@example.com", True, id="valid-simple"),
        pytest.param("user+tag@example.com", True, id="valid-with-plus"),
        pytest.param("user@sub.example.com", True, id="valid-subdomain"),
        pytest.param("invalid", False, id="invalid-no-at"),
        pytest.param("user@", False, id="invalid-no-domain"),
        pytest.param("@example.com", False, id="invalid-no-local"),
    ],
)
def test_email_validation(email, is_valid):
    """Test email validation with descriptive IDs."""
    assert is_valid_email(email) == is_valid
```

### Combining Fixtures with Parametrization

```python
@pytest.fixture
def user_factory():
    """Factory fixture for creating test users."""
    def create_user(name="Test", email="test@example.com", role="user"):
        return User(id=0, name=name, email=email, role=role)
    return create_user

@pytest.mark.small
@pytest.mark.parametrize("role", ["user", "admin", "moderator"])
def test_user_permissions(user_factory, role):
    """Test permissions for different user roles."""
    user = user_factory(role=role)
    permissions = get_permissions(user)
    assert "read" in permissions
```

## Dependency Injection Patterns

### Constructor Injection

Design your classes to accept dependencies:

```python
# src/user_service.py
class UserService:
    """User service with injected dependencies."""

    def __init__(
        self,
        repository: UserRepository,
        email_client: EmailClient,
    ):
        self._repository = repository
        self._email_client = email_client

    def create_user(self, name: str, email: str) -> User:
        user = self._repository.save(User(id=0, name=name, email=email))
        self._email_client.send_welcome(user.email)
        return user
```

Testing with fakes:

```python
@pytest.mark.small
def test_user_creation_sends_welcome_email(mocker):
    """Test with fake repository and mock email client."""
    fake_repo = FakeUserRepository()
    mock_email = mocker.Mock()

    service = UserService(repository=fake_repo, email_client=mock_email)
    user = service.create_user("Alice", "alice@example.com")

    assert fake_repo.get_by_id(user.id) is not None
    mock_email.send_welcome.assert_called_once_with("alice@example.com")
```

### Protocol-Based Injection

Use Python protocols for type-safe dependency injection:

```python
# src/protocols.py
from typing import Protocol

class EmailClient(Protocol):
    """Protocol for email sending."""

    def send_welcome(self, email: str) -> None:
        """Send welcome email."""

class UserRepository(Protocol):
    """Protocol for user persistence."""

    def save(self, user: User) -> User:
        """Save user."""

    def get_by_id(self, user_id: int) -> User | None:
        """Get user by ID."""
```

## Related Documentation

- [Migration Guide](migration-guide.md) - Step-by-step migration process
- [CI Integration](ci-integration.md) - CI/CD configuration examples
- [Filesystem Isolation](filesystem-isolation.md) - Filesystem isolation patterns
- [Network Isolation](network-isolation.md) - Network isolation patterns
- [Sample Project](https://github.com/mikelane/pytest-test-categories/tree/main/examples/sample_project) - Complete working example
