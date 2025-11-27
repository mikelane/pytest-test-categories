# Getting Started

This guide will help you get up and running with pytest-test-categories in just a few minutes.

## Prerequisites

- Python 3.11 or higher
- pytest 8.0 or higher

## Installation

Install pytest-test-categories using pip:

```bash
pip install pytest-test-categories
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv add pytest-test-categories
```

## Basic Usage

### Step 1: Mark Your Tests

Add size markers to your tests to categorize them:

```python
import pytest

@pytest.mark.small
def test_addition():
    """Small tests must complete in under 1 second."""
    assert 1 + 1 == 2

@pytest.mark.medium
def test_database_query(db_connection):
    """Medium tests can take up to 5 minutes."""
    result = db_connection.query("SELECT * FROM users")
    assert len(result) > 0

@pytest.mark.large
def test_end_to_end_workflow(app):
    """Large tests can take up to 15 minutes."""
    # Full workflow test
    pass
```

### Step 2: Run Your Tests

Run pytest as usual:

```bash
pytest
```

The plugin will automatically:
1. Count tests by size category
2. Append size labels to test IDs (e.g., `test_addition[SMALL]`)
3. Enforce time limits for each test
4. Report distribution statistics

### Step 3: Review the Output

After tests complete, you'll see a distribution summary:

```
======================== Test Size Distribution ========================
Small:   45 tests (81.8%) - Target: 80% +/- 5% [OK]
Medium:   8 tests (14.5%) - Target: 15% +/- 5% [OK]
Large:    2 tests ( 3.6%) - Target:  5% +/- 3% [OK]
========================================================================
```

## Test Size Guidelines

### Small Tests (< 1 second)

Small tests are the foundation of a healthy test suite. They should be:

- **Fast**: Complete in under 1 second
- **Hermetic**: No external dependencies (network, filesystem, databases)
- **Deterministic**: Same input always produces same output
- **Parallelizable**: Safe to run concurrently

```python
@pytest.mark.small
def test_email_validation():
    from myapp.validators import validate_email
    assert validate_email("user@example.com") is True
    assert validate_email("invalid") is False
```

### Medium Tests (< 5 minutes)

Medium tests may access local services:

- Local databases (PostgreSQL, MySQL, SQLite)
- Local caches (Redis, Memcached)
- Local mock servers

```python
@pytest.mark.medium
def test_user_repository(postgres_connection):
    from myapp.repositories import UserRepository
    repo = UserRepository(postgres_connection)
    user = repo.find_by_email("alice@example.com")
    assert user is not None
```

### Large Tests (< 15 minutes)

Large tests may access external services:

- External APIs
- Staging environments
- Third-party services

```python
@pytest.mark.large
def test_payment_integration(staging_api):
    from myapp.payments import process_payment
    result = process_payment(amount=100, currency="USD")
    assert result.success is True
```

### XLarge Tests (< 15 minutes)

XLarge tests are for extended test scenarios that need the full time allocation but aren't necessarily accessing external services.

## Using Base Test Classes

As an alternative to markers, you can inherit from base test classes:

```python
from pytest_test_categories import SmallTest, MediumTest

class TestEmailValidator(SmallTest):
    def test_valid_email(self):
        assert validate_email("user@example.com") is True

class TestUserRepository(MediumTest):
    def test_find_user(self, db):
        user = UserRepository(db).find_by_email("test@example.com")
        assert user is not None
```

## Next Steps

- Learn about [timing enforcement](user-guide/timing-enforcement.md)
- Configure [distribution validation](user-guide/distribution-validation.md)
- Set up [test reporting](user-guide/reporting.md)
- Explore [network isolation](user-guide/network-isolation.md) (planned feature)
