# Troubleshooting Network Violations

This guide helps you identify and fix network access violations in your test suite.

## Understanding the Error Message

When a network violation occurs in strict mode, you see an error like this:

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

The error tells you:

- **Test**: The full pytest node ID of the failing test
- **Category**: The test size (SMALL, MEDIUM, etc.)
- **Details**: The host and port that the test attempted to connect to
- **Options**: Suggested fixes for the violation

## Common Violation Scenarios

### 1. Direct HTTP Requests

**Symptom**: Connection to an external API hostname on port 443 or 80.

```
Attempted connection to: api.example.com:443
```

**Cause**: Test code directly calls an HTTP library:

```python
import requests

@pytest.mark.small
def test_get_user():
    response = requests.get("https://api.example.com/users/123")
    assert response.status_code == 200
```

**Fix**: Use a mocking library like `responses`:

```python
import responses
import requests

@pytest.mark.small
@responses.activate
def test_get_user():
    responses.add(
        responses.GET,
        "https://api.example.com/users/123",
        json={"id": "123", "name": "Test User"},
        status=200,
    )

    response = requests.get("https://api.example.com/users/123")

    assert response.status_code == 200
    assert response.json()["name"] == "Test User"
```

### 2. DNS Lookups

**Symptom**: Connection to DNS server (port 53) or hostname resolution.

```
Attempted connection to: 8.8.8.8:53
```

**Cause**: Code performs DNS resolution before the connection is blocked:

```python
import socket

@pytest.mark.small
def test_resolve_hostname():
    ip = socket.gethostbyname("example.com")
    assert ip is not None
```

**Fix**: Mock the DNS resolution:

```python
@pytest.mark.small
def test_resolve_hostname(mocker):
    mocker.patch("socket.gethostbyname", return_value="93.184.216.34")

    ip = socket.gethostbyname("example.com")

    assert ip == "93.184.216.34"
```

### 3. Database Connections

**Symptom**: Connection to database ports (5432 for PostgreSQL, 3306 for MySQL, etc.).

```
Attempted connection to: localhost:5432
```

**Cause**: Test connects to a real database:

```python
import psycopg2

@pytest.mark.small
def test_database_query():
    conn = psycopg2.connect("postgresql://localhost/testdb")
    # ...
```

**Fix for small tests**: Use an in-memory fake or mock:

```python
@pytest.mark.small
def test_database_query(mocker):
    mock_conn = mocker.Mock()
    mock_cursor = mocker.Mock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [("row1",), ("row2",)]
    mocker.patch("psycopg2.connect", return_value=mock_conn)

    conn = psycopg2.connect("postgresql://localhost/testdb")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    results = cursor.fetchall()

    assert len(results) == 2
```

**Fix for integration tests**: Change to medium test:

```python
@pytest.mark.medium  # Medium tests can access localhost
def test_database_query():
    conn = psycopg2.connect("postgresql://localhost/testdb")
    # ...
```

### 4. Redis/Cache Connections

**Symptom**: Connection to Redis (port 6379) or Memcached (port 11211).

```
Attempted connection to: localhost:6379
```

**Cause**: Test connects to a cache server:

```python
import redis

@pytest.mark.small
def test_cache_operation():
    r = redis.Redis(host="localhost", port=6379)
    r.set("key", "value")
```

**Fix for small tests**: Use `fakeredis`:

```python
import fakeredis

@pytest.mark.small
def test_cache_operation():
    r = fakeredis.FakeRedis()
    r.set("key", "value")
    assert r.get("key") == b"value"
```

**Fix for integration tests**: Change to medium test.

### 5. gRPC Connections

**Symptom**: Connection to gRPC service ports.

```
Attempted connection to: grpc.example.com:50051
```

**Cause**: Test calls a gRPC service:

```python
import grpc

@pytest.mark.small
def test_grpc_call():
    channel = grpc.insecure_channel("grpc.example.com:50051")
    stub = MyServiceStub(channel)
    response = stub.GetData(Request())
```

**Fix**: Use `grpc_testing` or mock the stub:

```python
@pytest.mark.small
def test_grpc_call(mocker):
    mock_stub = mocker.Mock()
    mock_stub.GetData.return_value = Response(data="test")
    mocker.patch("my_module.MyServiceStub", return_value=mock_stub)

    # Test code that uses the stub
    ...
```

### 6. SMTP/Email Connections

**Symptom**: Connection to mail servers (port 25, 465, 587).

```
Attempted connection to: smtp.gmail.com:587
```

**Cause**: Test sends actual emails:

```python
import smtplib

@pytest.mark.small
def test_send_email():
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.send_message(msg)
```

**Fix**: Mock the SMTP connection:

```python
@pytest.mark.small
def test_send_email(mocker):
    mock_smtp = mocker.Mock()
    mocker.patch("smtplib.SMTP", return_value=mock_smtp)

    # Call code that sends email
    send_notification("user@example.com", "Hello")

    mock_smtp.send_message.assert_called_once()
```

## Identifying Network-Calling Code

### Step 1: Run Tests in Warn Mode

First, identify all violations without failing tests:

```bash
pytest --test-categories-enforcement=warn 2>&1 | grep -A5 "Network access violation"
```

### Step 2: Add Debugging Output

If the source is unclear, add socket debugging:

```python
import socket

# Temporarily patch to see call stack
original_connect = socket.socket.connect

def debug_connect(self, address):
    import traceback
    print(f"Connection attempt to: {address}")
    traceback.print_stack()
    return original_connect(self, address)

socket.socket.connect = debug_connect
```

### Step 3: Use pytest Verbose Mode

Run the specific test with verbose output:

```bash
pytest tests/test_api.py::test_fetch_user -vvs
```

### Step 4: Check Fixture Dependencies

Network calls often happen in fixtures:

```python
@pytest.fixture
def api_client():
    # This fixture makes a network call!
    client = APIClient("https://api.example.com")
    client.authenticate()  # <-- Network call here
    return client
```

Review all fixtures used by the failing test.

## Migration Guide

### Phase 1: Assessment

1. Enable warn mode in CI:

   ```toml
   [tool.pytest.ini_options]
   test_categories_enforcement = "warn"
   ```

2. Collect all warnings from a full test run
3. Categorize violations by type (HTTP, database, cache, etc.)
4. Estimate effort to fix each category

### Phase 2: Quick Wins

1. Fix tests that already have mocking infrastructure but make extra calls
2. Replace real clients with fakes in test fixtures
3. Add missing `@responses.activate` decorators

### Phase 3: Refactoring

1. Introduce dependency injection for HTTP clients
2. Create test doubles for external service clients
3. Add factory functions that return appropriate client for context

### Phase 4: Enforcement

1. Switch to strict mode in CI:

   ```toml
   [tool.pytest.ini_options]
   test_categories_enforcement = "strict"
   ```

2. Add pre-commit hook to catch violations locally
3. Document mocking patterns for the team

## Temporary Workarounds

### Allow Network for Specific Test

If you cannot immediately fix a test, use the `allow_network` marker:

```python
@pytest.mark.small
@pytest.mark.allow_network  # TODO: Remove after fixing #123
def test_legacy_api_call():
    """Temporary workaround until mocking is implemented."""
    ...
```

Always add a TODO comment and track the technical debt.

### Skip in CI Only

For tests that work locally but fail in CI due to network restrictions:

```python
import os

@pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="Network access blocked in CI"
)
@pytest.mark.small
def test_requires_network():
    ...
```

This is a temporary measure - fix the underlying issue.

## Getting Help

If you encounter a violation you cannot resolve:

1. Check the [examples documentation](../examples/network-isolation.md)
2. Review the [ADR for network isolation](../architecture/adr-001-network-isolation.md)
3. Open a [GitHub Discussion](https://github.com/mikelane/pytest-test-categories/discussions) with:
   - The full error message
   - The test code (sanitized if needed)
   - What you have tried

## Related Documentation

- [User Guide: Network Isolation](../user-guide/network-isolation.md)
- [Examples: Network Isolation](../examples/network-isolation.md)
- [ADR-001: Network Isolation](../architecture/adr-001-network-isolation.md)
