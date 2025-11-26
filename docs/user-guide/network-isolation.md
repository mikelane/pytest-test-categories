# Network Isolation for Hermetic Tests

## What is Network Isolation?

Network isolation is a test enforcement mechanism that prevents tests from making network connections during execution. This ensures tests are **hermetic** - they run entirely in memory with no external dependencies.

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

## Google's Test Size Definitions

The network isolation feature implements Google's test size definitions from "Software Engineering at Google":

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
============================================================
HermeticityViolationError
============================================================
Test: tests/test_api.py::test_fetch_user
Category: SMALL
Violation: Network access attempted

Details:
  Attempted connection to: api.example.com:443

Small tests have restricted resource access. Options:
  1. Mock the network call using responses, httpretty, or respx
  2. Use dependency injection to provide a fake HTTP client
  3. Change test category to @pytest.mark.medium (if network is required)

Documentation: See docs/architecture/adr-001-network-isolation.md
============================================================
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

## Per-Test Overrides

Individual tests can override the global enforcement using markers:

### Allow Network Access

```python
import pytest

@pytest.mark.small
@pytest.mark.allow_network
def test_special_case_requiring_network():
    """This small test is allowed to access the network."""
    # Network access is permitted for this test only
    ...
```

Use sparingly and document why the override is necessary.

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

### 4. Apply Dependency Injection

Design code to accept HTTP clients as parameters:

```python
# Production code
def fetch_user(user_id: str, client: httpx.Client | None = None) -> User:
    client = client or httpx.Client()
    response = client.get(f"https://api.example.com/users/{user_id}")
    return User.model_validate(response.json())

# Test code
def test_fetch_user():
    mock_client = Mock(spec=httpx.Client)
    mock_client.get.return_value = Mock(
        json=lambda: {"id": "123", "name": "Test User"}
    )

    user = fetch_user("123", client=mock_client)

    assert user.name == "Test User"
```

### 5. Consider Test Size Carefully

If a test genuinely requires network access, consider whether it belongs in a different size category:

- **Small**: Unit tests, pure functions, isolated components
- **Medium**: Integration with local services
- **Large**: Integration with external services

## Related Documentation

- [Architecture Decision Record: Network Isolation](../architecture/adr-001-network-isolation.md)
- [Troubleshooting Network Violations](../troubleshooting/network-violations.md)
- [Network Isolation Examples](../examples/network-isolation.md)
