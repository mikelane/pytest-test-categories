# Test Sizes

pytest-test-categories implements Google's test size taxonomy, which categorizes tests by their execution characteristics and resource requirements.

## Overview

Test sizes provide a vocabulary for describing what a test does and what resources it needs. This taxonomy helps teams:

- Set appropriate expectations for test execution time
- Design tests with the right level of isolation
- Maintain a balanced test pyramid
- Optimize CI/CD pipeline performance

## The Four Test Sizes

### Small Tests

Small tests are the foundation of your test suite. They should make up approximately 80% of all tests.

**Characteristics:**
- Execute in under 1 second
- Run entirely in memory
- No network access
- No filesystem access (except for test fixtures)
- No database access
- Fully deterministic

**Use cases:**
- Unit tests for pure functions
- Testing business logic in isolation
- Validator and parser tests
- Data transformation tests

**Example:**

```python
import pytest

@pytest.mark.small
def test_calculate_discount():
    """Small test for pure business logic."""
    from myapp.pricing import calculate_discount

    result = calculate_discount(original_price=100, discount_percent=20)

    assert result == 80.0

@pytest.mark.small
def test_email_validation():
    """Small test for input validation."""
    from myapp.validators import is_valid_email

    assert is_valid_email("user@example.com") is True
    assert is_valid_email("invalid-email") is False
```

### Medium Tests

Medium tests may access local services and typically make up about 15% of your test suite.

**Characteristics:**
- Execute in under 5 minutes
- May access localhost services
- May use local databases (PostgreSQL, MySQL, SQLite)
- May use local caches (Redis, Memcached)
- Should still be deterministic

**Use cases:**
- Repository layer tests with real databases
- Cache integration tests
- Local service integration tests
- Tests using Docker containers

**Example:**

```python
import pytest

@pytest.mark.medium
def test_user_repository_creates_user(postgres_connection):
    """Medium test using a local PostgreSQL database."""
    from myapp.repositories import UserRepository

    repo = UserRepository(postgres_connection)
    user = repo.create(name="Alice", email="alice@example.com")

    assert user.id is not None
    assert user.name == "Alice"

@pytest.mark.medium
def test_cache_stores_and_retrieves(redis_client):
    """Medium test using a local Redis instance."""
    from myapp.cache import UserCache

    cache = UserCache(redis_client)
    cache.set("user:123", {"name": "Bob"})

    result = cache.get("user:123")
    assert result["name"] == "Bob"
```

### Large Tests

Large tests may access external services and typically make up about 5% of your test suite (combined with XLarge).

**Characteristics:**
- Execute in under 15 minutes
- May access external networks
- May call real APIs
- May use staging environments
- May be non-deterministic

**Use cases:**
- End-to-end workflow tests
- External API integration tests
- Staging environment tests
- Contract tests

**Example:**

```python
import pytest

@pytest.mark.large
def test_payment_workflow_end_to_end(staging_client):
    """Large test for complete payment workflow."""
    # Create order
    order = staging_client.create_order(items=["SKU001", "SKU002"])

    # Process payment
    payment = staging_client.process_payment(order.id, amount=order.total)

    # Verify order completed
    assert payment.status == "completed"
    assert staging_client.get_order(order.id).status == "paid"

@pytest.mark.large
def test_external_api_integration():
    """Large test calling an external API."""
    import httpx

    response = httpx.get("https://api.example.com/health")

    assert response.status_code == 200
```

### XLarge Tests

XLarge tests are for scenarios that need extended execution time, similar to large tests in resource access.

**Characteristics:**
- Execute in under 15 minutes (same as Large)
- May access external networks
- Used for extended or stress testing scenarios

**Use cases:**
- Performance benchmarks
- Stress tests
- Migration testing
- Large data set processing

**Example:**

```python
import pytest

@pytest.mark.xlarge
def test_bulk_import_performance(large_dataset):
    """XLarge test for bulk import performance."""
    from myapp.importers import BulkImporter

    importer = BulkImporter()
    result = importer.import_records(large_dataset)

    assert result.success_count == len(large_dataset)
    assert result.duration_seconds < 300  # 5 minutes max
```

## Choosing the Right Size

Use this decision tree to choose the appropriate test size:

1. **Does the test need external network access?**
   - Yes: Use `@pytest.mark.large` or `@pytest.mark.xlarge`
   - No: Continue to step 2

2. **Does the test need local services (databases, caches)?**
   - Yes: Use `@pytest.mark.medium`
   - No: Continue to step 3

3. **Can the test complete in under 1 second?**
   - Yes: Use `@pytest.mark.small`
   - No: Consider refactoring or use `@pytest.mark.medium`

## Using Base Test Classes

As an alternative to markers, inherit from base test classes:

```python
from pytest_test_categories import SmallTest, MediumTest, LargeTest, XLargeTest

class TestCalculator(SmallTest):
    """All tests in this class are marked as small."""

    def test_add(self):
        assert Calculator().add(1, 2) == 3

    def test_subtract(self):
        assert Calculator().subtract(5, 3) == 2

class TestDatabaseOperations(MediumTest):
    """All tests in this class are marked as medium."""

    def test_insert(self, db):
        db.insert({"key": "value"})
        assert db.count() == 1
```

## Test Pyramid

A healthy test suite follows the test pyramid pattern:

```
         /\
        /  \
       / L  \     5% Large/XLarge
      /------\
     /   M    \   15% Medium
    /----------\
   /     S      \ 80% Small
  /--------------\
```

This distribution optimizes for:
- **Fast feedback**: Most tests run quickly
- **High confidence**: Comprehensive coverage at unit level
- **Cost efficiency**: Fewer expensive integration tests
- **Maintainability**: Small tests are easier to maintain

See [Distribution Validation](distribution-validation.md) for how the plugin enforces this distribution.
