# Markers Reference

This page documents all pytest markers provided by pytest-test-categories.

## Size Markers

pytest-test-categories provides four size markers to categorize tests based on Google's "Software Engineering at Google" best practices.

### @pytest.mark.small

```python
@pytest.mark.small
def test_example():
    """Fast, hermetic unit test."""
    pass
```

**Signature:** `@pytest.mark.small`

**Description:** Marks a test as a small (unit) test. Small tests are fast, hermetic, and test individual behaviors in isolation.

**Characteristics:**

| Property | Value |
|----------|-------|
| Time Limit | 1 second |
| Network Access | Blocked |
| Filesystem Access | Blocked |
| Subprocess Spawning | Blocked |
| Database Access | Blocked |
| Sleep Calls | Blocked |
| Target Distribution | ~80% of test suite |

**Best Practices:**

- Test a single, specific behavior
- Use test doubles (mocks, stubs, fakes) for external dependencies
- No file I/O, network, or external dependencies
- Run quickly and deterministically
- Prefer state testing over interaction testing

**Example:**

```python
import pytest

@pytest.mark.small
def test_add_numbers():
    """Unit test for addition function."""
    assert add(2, 3) == 5

@pytest.mark.small
def test_validate_email_format():
    """Unit test for email validation."""
    assert is_valid_email("user@example.com")
    assert not is_valid_email("invalid-email")
```

---

### @pytest.mark.medium

```python
@pytest.mark.medium
def test_example():
    """Integration test with local services."""
    pass
```

**Signature:** `@pytest.mark.medium` or `@pytest.mark.medium(allow_external_systems=True)`

**Description:** Marks a test as a medium (integration) test. Medium tests may use multiple threads, file I/O, and localhost network access.

**Characteristics:**

| Property | Value |
|----------|-------|
| Time Limit | 300 seconds / 5 minutes |
| Network Access | Localhost only |
| Filesystem Access | Allowed |
| Subprocess Spawning | Allowed |
| Database Access | Allowed |
| Sleep Calls | Allowed |
| Target Distribution | ~15% of test suite |

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `allow_external_systems` | `bool` | `False` | Suppress warnings when using testcontainers or Docker |

**Best Practices:**

- Test integration between components
- Use real databases (local or in-memory)
- Allow multiple threads
- Disallow external network access
- Still test a single, specific behavior

**Example:**

```python
import pytest

@pytest.mark.medium
def test_database_integration(tmp_path):
    """Test database operations with file storage."""
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    db.insert({"key": "value"})
    assert db.get("key") == "value"

@pytest.mark.medium(allow_external_systems=True)
def test_with_testcontainers():
    """Test with Docker containers (suppresses external systems warning)."""
    with PostgresContainer() as postgres:
        # Test with real PostgreSQL
        pass
```

---

### @pytest.mark.large

```python
@pytest.mark.large
def test_example():
    """End-to-end test with external services."""
    pass
```

**Signature:** `@pytest.mark.large`

**Description:** Marks a test as a large (end-to-end) test. Large tests may access external networks and multiple machines.

**Characteristics:**

| Property | Value |
|----------|-------|
| Time Limit | 900 seconds / 15 minutes |
| Network Access | Allowed |
| Filesystem Access | Allowed |
| Subprocess Spawning | Allowed |
| Database Access | Allowed |
| Sleep Calls | Allowed |
| Target Distribution | ~2.5-5% of test suite |

**Best Practices:**

- Reserve for system-level or end-to-end tests
- Test complete user workflows
- May access external services and APIs
- May span multiple machines

**Example:**

```python
import pytest
import requests

@pytest.mark.large
def test_full_api_workflow():
    """End-to-end test of API workflow."""
    response = requests.post("https://api.example.com/users", json={"name": "Test"})
    assert response.status_code == 201

    user_id = response.json()["id"]
    response = requests.get(f"https://api.example.com/users/{user_id}")
    assert response.json()["name"] == "Test"
```

---

### @pytest.mark.xlarge

```python
@pytest.mark.xlarge
def test_example():
    """Extended test for massive integration."""
    pass
```

**Signature:** `@pytest.mark.xlarge`

**Description:** Marks a test as an extra-large test. XLarge tests are for truly enormous features requiring extended execution time.

**Characteristics:**

| Property | Value |
|----------|-------|
| Time Limit | 900 seconds / 15 minutes |
| Network Access | Allowed |
| Filesystem Access | Allowed |
| Subprocess Spawning | Allowed |
| Database Access | Allowed |
| Sleep Calls | Allowed |
| Target Distribution | 0-5% of test suite |

**Best Practices:**

- Use sparingly
- Reserve for massive integration or performance tests
- Consider if the test can be split into smaller tests

**Example:**

```python
import pytest

@pytest.mark.xlarge
def test_performance_benchmark():
    """Performance test processing large dataset."""
    dataset = generate_large_dataset(size=1_000_000)
    result = process_dataset(dataset)
    assert result.performance_score > 0.95
```

---

## Base Test Classes

pytest-test-categories provides base test classes that automatically apply size markers through inheritance.

### SmallTest

```python
from pytest_test_categories import SmallTest

class TestMyFeature(SmallTest):
    def test_example(self):
        pass
```

**Module:** `pytest_test_categories.test_bases`

**Description:** Base class for small tests. Automatically applies `@pytest.mark.small` to all test methods in the class.

**Class Attribute:**

```python
pytestmark = pytest.mark.small
```

**Example:**

```python
from pytest_test_categories import SmallTest

class DescribeCalculator(SmallTest):
    """Small tests for Calculator class."""

    def test_add_positive_numbers(self):
        calc = Calculator()
        assert calc.add(2, 3) == 5

    def test_add_negative_numbers(self):
        calc = Calculator()
        assert calc.add(-2, -3) == -5
```

---

### MediumTest

```python
from pytest_test_categories import MediumTest

class TestIntegration(MediumTest):
    def test_example(self):
        pass
```

**Module:** `pytest_test_categories.test_bases`

**Description:** Base class for medium tests. Automatically applies `@pytest.mark.medium` to all test methods in the class.

**Class Attribute:**

```python
pytestmark = pytest.mark.medium
```

**Example:**

```python
from pytest_test_categories import MediumTest

class DescribeDatabaseIntegration(MediumTest):
    """Medium tests for database operations."""

    def test_create_and_retrieve(self, tmp_path):
        db = Database(tmp_path / "test.db")
        db.create("user", {"name": "Alice"})
        assert db.get("user")["name"] == "Alice"
```

---

### LargeTest

```python
from pytest_test_categories import LargeTest

class TestE2E(LargeTest):
    def test_example(self):
        pass
```

**Module:** `pytest_test_categories.test_bases`

**Description:** Base class for large tests. Automatically applies `@pytest.mark.large` to all test methods in the class.

**Class Attribute:**

```python
pytestmark = pytest.mark.large
```

**Example:**

```python
from pytest_test_categories import LargeTest

class DescribeAPIWorkflow(LargeTest):
    """Large tests for complete API workflows."""

    def test_user_registration_flow(self, api_client):
        # Complete end-to-end workflow
        user = api_client.register(email="test@example.com")
        api_client.verify_email(user.id)
        session = api_client.login(email="test@example.com")
        assert session.is_authenticated
```

---

### XLargeTest

```python
from pytest_test_categories import XLargeTest

class TestPerformance(XLargeTest):
    def test_example(self):
        pass
```

**Module:** `pytest_test_categories.test_bases`

**Description:** Base class for extra-large tests. Automatically applies `@pytest.mark.xlarge` to all test methods in the class.

**Class Attribute:**

```python
pytestmark = pytest.mark.xlarge
```

**Example:**

```python
from pytest_test_categories import XLargeTest

class DescribeLoadTesting(XLargeTest):
    """XLarge tests for load and performance."""

    def test_concurrent_users(self, load_test_framework):
        results = load_test_framework.run(
            users=1000,
            duration_seconds=300
        )
        assert results.error_rate < 0.01
```

---

## Marker Inheritance and Composition

### Class-Level Markers

Apply a marker to all tests in a class:

```python
import pytest

@pytest.mark.medium
class TestDatabaseOperations:
    def test_insert(self):
        pass  # Inherits @pytest.mark.medium

    def test_query(self):
        pass  # Inherits @pytest.mark.medium
```

### Module-Level Markers

Apply a marker to all tests in a module using `pytestmark`:

```python
# test_integration.py
import pytest

pytestmark = pytest.mark.medium

def test_one():
    pass  # Has @pytest.mark.medium

def test_two():
    pass  # Has @pytest.mark.medium
```

### Multiple Markers

Tests can have multiple markers, but only ONE size marker:

```python
import pytest

@pytest.mark.small
@pytest.mark.slow  # Custom marker, not a size marker
def test_example():
    pass
```

**Error - Multiple Size Markers:**

```python
# THIS WILL RAISE pytest.UsageError
@pytest.mark.small
@pytest.mark.medium
def test_invalid():
    pass
```

```
pytest.UsageError: Test cannot have multiple size markers: ['small', 'medium']
```

### Marker Precedence

When markers are applied at multiple levels, pytest's standard precedence applies:

1. Function-level markers (highest priority)
2. Class-level markers
3. Module-level markers (lowest priority)

```python
import pytest

pytestmark = pytest.mark.small  # Module level

class TestExample:
    pytestmark = pytest.mark.medium  # Class level - overrides module

    @pytest.mark.large  # Function level - overrides class
    def test_one(self):
        pass  # Uses @pytest.mark.large

    def test_two(self):
        pass  # Uses @pytest.mark.medium
```

---

## Unmarked Tests

Tests without a size marker will trigger a warning:

```
PytestWarning: Test has no size marker: tests/test_example.py::test_unmarked
```

Unmarked tests are allowed to run but are tracked separately in distribution statistics.

**Best Practice:** Always mark your tests with an appropriate size marker.

---

## Source Code References

| Component | Location |
|-----------|----------|
| Size markers registration | [`plugin.py#pytest_configure`](https://github.com/mikelane/pytest-test-categories/blob/main/src/pytest_test_categories/plugin.py) |
| TestSize enum | [`types.py#TestSize`](https://github.com/mikelane/pytest-test-categories/blob/main/src/pytest_test_categories/types.py) |
| Base test classes | [`test_bases.py`](https://github.com/mikelane/pytest-test-categories/blob/main/src/pytest_test_categories/test_bases.py) |
