# Network Isolation for Hermetic Tests

Network isolation is a test enforcement mechanism that prevents tests from making network connections during execution. This ensures tests are **hermetic** - running entirely in memory with no external dependencies.

When enabled, the pytest-test-categories plugin intercepts socket connections and either blocks them or warns about them, depending on your configuration.

## Why Network Isolation Matters

Tests that access the network introduce several problems:

### Flaky Tests

Network-dependent tests fail intermittently due to:

- DNS resolution failures
- Service outages or maintenance windows
- Network timeouts under load
- Rate limiting from external APIs
- Certificate expiration or rotation

### Slow Tests

Network I/O adds latency that compounds across your test suite:

- DNS lookups: 10-100ms per request
- TCP connection establishment: 20-200ms
- TLS handshake: 50-500ms
- HTTP round trips: 100ms-2s+

A test suite with 1,000 tests, each making one network call averaging 200ms, adds over 3 minutes to your CI pipeline.

### Non-Deterministic Tests

External services return different data over time:

- API responses change as data is modified
- Third-party services update their schemas
- Time-dependent data (timestamps, counters) varies between runs
- Geographic routing returns different results

### Parallelization Issues

Network-dependent tests create resource contention:

- Connection pool exhaustion
- Rate limit collisions
- Port conflicts for mock servers
- Shared state on external services

## Test Size Restrictions

Network isolation follows Google's test size definitions from "Software Engineering at Google":

| Test Size | Network Access | Rationale |
|-----------|---------------|-----------|
| Small     | **Blocked**   | Must be hermetic, run in memory only |
| Medium    | Localhost only | May use local services (databases, caches) |
| Large     | Allowed       | Integration tests may access real services |
| XLarge    | Allowed       | End-to-end tests may access real services |

### Small Tests

Small tests are the foundation of a healthy test suite. They must be:

- **Fast**: Complete in under 1 second
- **Hermetic**: No external dependencies
- **Deterministic**: Same input always produces same output
- **Parallelizable**: Safe to run concurrently with other tests

Network isolation enforces hermeticity by blocking all network access in small tests.

### Medium Tests

Medium tests may access localhost services, enabling:

- Database integration tests with local containers
- Cache integration tests with local Redis/Memcached
- Service integration tests with local mock servers

External network access is blocked to maintain reproducibility.

### Large and XLarge Tests

Large and XLarge tests may access external networks for:

- End-to-end testing against staging environments
- Contract testing against real service dependencies
- Performance testing against production-like infrastructure

## How It Works

The plugin intercepts network connections by patching Python's socket module:

### Patched Entry Points

The following network entry points are intercepted:

- `socket.socket.connect` - TCP connection establishment
- `socket.socket.connect_ex` - Non-blocking connection
- `socket.create_connection` - High-level connection helper

### Connection Interception

When a test attempts to connect:

1. The blocker intercepts the `connect()` call
2. It extracts the target host and port
3. It checks if the connection is allowed based on test size
4. For violations, it either raises an exception (STRICT) or warns (WARN)

## Enabling Network Isolation

Network isolation is controlled by the `test_categories_enforcement` configuration option.

### Configuration via pyproject.toml

```toml
[tool.pytest.ini_options]
# Enable network isolation enforcement
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

In strict mode, network violations immediately fail the test with a detailed error message:

```
[TC001] Network Access Violation
Test: tests/test_api.py::test_fetch_user
Category: SMALL

What happened:
  Attempted network connection to api.example.com:443

How to fix:
  1. Mock the network call using responses, httpretty, or respx
  2. Use dependency injection to provide a fake HTTP client
  3. Change test category to @pytest.mark.medium (if network is required)

Documentation: https://pytest-test-categories.readthedocs.io/errors/TC001
```

Use strict mode in CI pipelines to catch violations before merge.

### WARN Mode

```toml
test_categories_enforcement = "warn"
```

In warn mode, network violations emit a warning but allow the test to continue:

```
PytestWarning: Network access violation in test_fetch_user:
attempted connection to api.example.com:443
```

Use warn mode during migration to identify violations without breaking the build.

### OFF Mode

```toml
test_categories_enforcement = "off"
```

In off mode, network isolation is disabled entirely. Use this for:

- Legacy test suites not yet ready for enforcement
- Specific test runs that require network access
- Debugging network-related test issues

## Common Remediation Strategies

### 1. Use responses Library

For tests using the `requests` library:

```python
import responses
import requests
import pytest

@pytest.mark.small
@responses.activate
def test_fetch_user():
    responses.add(
        responses.GET,
        "https://api.example.com/users/123",
        json={"id": "123", "name": "Alice"},
        status=200,
    )

    response = requests.get("https://api.example.com/users/123")

    assert response.json()["name"] == "Alice"
```

### 2. Use respx Library

For tests using the `httpx` library:

```python
import httpx
import respx
import pytest

@pytest.mark.small
@respx.mock
def test_fetch_user():
    respx.get("https://api.example.com/users/123").respond(
        json={"id": "123", "name": "Alice"}
    )

    response = httpx.get("https://api.example.com/users/123")

    assert response.json()["name"] == "Alice"
```

### 3. Use Dependency Injection

Design code to accept HTTP clients as parameters:

```python
from unittest.mock import Mock
import httpx
import pytest

# Production code
def fetch_user(user_id: str, client: httpx.Client | None = None) -> dict:
    client = client or httpx.Client()
    response = client.get(f"https://api.example.com/users/{user_id}")
    return response.json()

# Test code
@pytest.mark.small
def test_fetch_user():
    mock_client = Mock(spec=httpx.Client)
    mock_response = Mock()
    mock_response.json.return_value = {"id": "123", "name": "Alice"}
    mock_client.get.return_value = mock_response

    result = fetch_user("123", client=mock_client)

    assert result["name"] == "Alice"
```

### 4. Use pytest-mock

For simple mocking scenarios:

```python
import pytest

@pytest.mark.small
def test_fetch_user(mocker):
    mock_get = mocker.patch("requests.get")
    mock_get.return_value.json.return_value = {"id": "123", "name": "Alice"}

    from myapp.users import fetch_user
    result = fetch_user("123")

    assert result["name"] == "Alice"
```

### 5. Use VCR.py for Record/Replay

For complex API interactions:

```python
import vcr
import pytest

@pytest.mark.small
@vcr.use_cassette("tests/cassettes/user_123.yaml")
def test_fetch_user():
    # First run records the interaction
    # Subsequent runs replay from cassette
    from myapp.users import fetch_user
    result = fetch_user("123")

    assert result["name"] == "Alice"
```

### 6. Recategorize the Test

If the test legitimately requires network access, it's not a small test - recategorize it:

```python
import pytest

@pytest.mark.medium  # Medium tests can access localhost
def test_database_integration(local_postgres):
    from myapp.repos import UserRepository
    repo = UserRepository(local_postgres)
    user = repo.create(name="Alice")
    assert user.id is not None

@pytest.mark.large  # Large tests can access external networks
def test_staging_api():
    import httpx
    response = httpx.get("https://staging.example.com/health")
    assert response.status_code == 200
```

The test size defines the constraints, not the other way around.

## Best Practices

### 1. Start with WARN Mode

When first enabling network isolation, use warn mode to identify all violations:

```bash
pytest --test-categories-enforcement=warn 2>&1 | grep "Network access violation"
```

### 2. Fix Violations Systematically

Address violations in order of test frequency:

1. Fix small tests first (they run most often)
2. Then medium tests
3. Large tests typically need network access

### 3. Use Mocking Libraries

Replace network calls with mocks using established libraries:

- **requests**: Use `responses` or `requests-mock`
- **httpx**: Use `respx`
- **aiohttp**: Use `aioresponses`
- **urllib**: Use `responses` or manual patching

### 4. Consider Test Size Carefully

If a test genuinely requires network access, consider whether it belongs in a different size category:

- **Small**: Unit tests, pure functions, isolated components
- **Medium**: Integration with local services
- **Large**: Integration with external services

### 5. Use Localhost Services for Medium Tests

For database and service integration:

```python
import pytest

@pytest.fixture(scope="session")
def postgres_container():
    """Start a PostgreSQL container for medium tests."""
    import docker
    client = docker.from_env()
    container = client.containers.run(
        "postgres:15",
        detach=True,
        ports={"5432/tcp": None},
        environment={"POSTGRES_PASSWORD": "test"},
    )
    yield container
    container.stop()
    container.remove()

@pytest.mark.medium
def test_user_repository(postgres_container):
    # Test with real database on localhost
    ...
```

## Troubleshooting

### "NetworkAccessViolationError" in tests that don't make network calls

Some libraries make network calls during import or initialization:
- Analytics/telemetry libraries
- Configuration loaders that fetch from URLs
- Logging handlers that send to remote services

**Solution**: Mock the library at import time or disable the network-calling feature.

### "Connection to localhost blocked in medium test"

Ensure you're using the correct test marker:

```python
@pytest.mark.medium  # Not @pytest.mark.small
def test_with_local_database():
    ...
```

### "Test passes locally but fails in CI"

Common causes:
1. Different network configurations in CI
2. Firewall rules blocking connections
3. DNS resolution differences

**Solution**: Use mocking instead of relying on network access.

## Related Documentation

- [Architecture Decision Record: Network Isolation](../architecture/adr-001-network-isolation.md)
- [Test Sizes](test-sizes.md)
- [Filesystem Isolation](filesystem-isolation.md)
- [Configuration Reference](../configuration.md)
