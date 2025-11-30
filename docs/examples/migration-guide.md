# Migration Guide

This guide walks you through migrating an existing pytest test suite to use pytest-test-categories for test size enforcement and distribution tracking.

## Overview

Migration is a gradual process. You do not need to categorize every test at once. The plugin supports a phased approach:

1. **Install and configure** - Get the plugin running in warning mode
2. **Categorize tests** - Add size markers to your tests
3. **Fix violations** - Refactor tests that violate hermeticity constraints
4. **Enable enforcement** - Switch to strict mode once migration is complete

## Phase 1: Installation and Initial Configuration

### Install the Plugin

```bash
# Using pip
pip install pytest-test-categories

# Using uv
uv add pytest-test-categories

# Using poetry
poetry add pytest-test-categories
```

### Configure Warning Mode

Start with warning mode to see issues without breaking your CI:

```toml
# pyproject.toml
[tool.pytest.ini_options]
# Start with warn mode - tests still pass but violations are reported
test_categories_enforcement = "warn"

# Also monitor distribution (optional)
test_categories_distribution_enforcement = "warn"
```

### Run Your Tests

```bash
# Run all tests and observe warnings
pytest -v

# Generate a report to see test distribution
pytest --test-size-report=detailed
```

At this point, tests without size markers will show warnings but still pass.

## Phase 2: Categorizing Existing Tests

### Understanding Test Sizes

Before categorizing tests, understand what each size means:

| Size | Time Limit | Network | Filesystem | External Systems |
|------|-----------|---------|------------|------------------|
| Small | 1 second | Blocked | `tmp_path` only | None |
| Medium | 5 minutes | Localhost only | Allowed | Containers OK |
| Large | 15 minutes | Allowed | Allowed | Allowed |
| XLarge | 15 minutes | Allowed | Allowed | Allowed |

### Target Distribution

Based on Google's "Software Engineering at Google" recommendations:

- **80% small tests** - Fast, hermetic unit tests
- **15% medium tests** - Integration tests with containers/localhost
- **5% large/xlarge tests** - End-to-end integration tests

### Step 1: Identify Test Types

Review your test suite and categorize tests by their behavior:

```bash
# List all test files to review
find tests -name "test_*.py" -type f

# Or check test collection
pytest --collect-only -q
```

Create a simple checklist:

- **Pure unit tests** (no I/O, no mocking needed) -> `@pytest.mark.small`
- **Tests with mocked HTTP/database** -> `@pytest.mark.small`
- **Tests using `tmp_path`** -> `@pytest.mark.small`
- **Tests using localhost servers** -> `@pytest.mark.medium`
- **Tests using testcontainers** -> `@pytest.mark.medium(allow_external_systems=True)`
- **Tests calling real external APIs** -> `@pytest.mark.large`

### Step 2: Add Markers to Tests

Start with the simplest tests first:

#### Before (Unmarked Test)

```python
# tests/test_calculator.py
def test_add():
    assert add(1, 2) == 3

def test_subtract():
    assert subtract(5, 3) == 2
```

#### After (Marked Test)

```python
# tests/test_calculator.py
import pytest

@pytest.mark.small
def test_add():
    assert add(1, 2) == 3

@pytest.mark.small
def test_subtract():
    assert subtract(5, 3) == 2
```

### Step 3: Use Class-Level Markers for Groups

If a file or class has all tests of the same size, mark the class:

#### Before

```python
# tests/test_user_service.py
def test_create_user(mocker):
    # Uses mocks, fast
    ...

def test_update_user(mocker):
    # Uses mocks, fast
    ...

def test_delete_user(mocker):
    # Uses mocks, fast
    ...
```

#### After

```python
# tests/test_user_service.py
import pytest

@pytest.mark.small
class TestUserService:
    def test_create_user(self, mocker):
        ...

    def test_update_user(self, mocker):
        ...

    def test_delete_user(self, mocker):
        ...
```

### Step 4: Use Base Classes (Optional)

For a cleaner syntax, inherit from base classes:

```python
# tests/test_user_service.py
from pytest_test_categories import SmallTest

class TestUserService(SmallTest):
    def test_create_user(self, mocker):
        ...

    def test_update_user(self, mocker):
        ...
```

### Step 5: Organize by Directory (Optional)

Create a directory structure that reflects test sizes:

```
tests/
    small/           # Fast unit tests
        test_models.py
        test_utils.py
    medium/          # Integration tests
        test_database.py
        test_api_client.py
    large/           # E2E tests
        test_full_workflow.py
    conftest.py
```

You can apply markers via `conftest.py`:

```python
# tests/small/conftest.py
import pytest

def pytest_collection_modifyitems(items):
    for item in items:
        if "small" in str(item.fspath):
            item.add_marker(pytest.mark.small)
```

## Phase 3: Fixing Common Violations

### Tests That Make HTTP Requests

#### Before (Violates Hermeticity)

```python
@pytest.mark.small
def test_fetch_user():
    response = requests.get("https://api.example.com/users/1")
    assert response.status_code == 200
```

#### After (Using pytest-httpx)

```python
@pytest.mark.small
def test_fetch_user(httpx_mock):
    httpx_mock.add_response(
        url="https://api.example.com/users/1",
        json={"id": 1, "name": "Alice"},
    )

    response = httpx.get("https://api.example.com/users/1")

    assert response.status_code == 200
    assert response.json()["name"] == "Alice"
```

### Tests That Access the Database

#### Before (Violates Hermeticity)

```python
@pytest.mark.small
def test_create_user():
    conn = psycopg2.connect(...)  # Real database connection
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users ...")
```

#### After (Using Fake Repository)

```python
@pytest.mark.small
def test_create_user():
    repo = FakeUserRepository()  # In-memory fake

    user = repo.create(name="Alice")

    assert user.id is not None
    assert repo.get_by_id(user.id).name == "Alice"
```

See [Common Patterns](common-patterns.md) for the full fake repository implementation.

### Tests That Access the Filesystem

#### Before (Violates Hermeticity)

```python
@pytest.mark.small
def test_read_config():
    config = load_config("config/settings.yaml")  # Real file
    assert config["database"]["host"] == "localhost"
```

#### After (Using tmp_path)

```python
@pytest.mark.small
def test_read_config(tmp_path):
    config_file = tmp_path / "settings.yaml"
    config_file.write_text("database:\n  host: localhost\n")

    config = load_config(config_file)

    assert config["database"]["host"] == "localhost"
```

### Tests That Genuinely Need External Access

Some tests legitimately need network or filesystem access. Mark them appropriately:

```python
@pytest.mark.medium
def test_database_integration(postgres_container):
    """This test intentionally uses a real database container."""
    repo = PostgresUserRepository(postgres_container.connection_string)
    user = repo.create(name="Alice")
    assert repo.get_by_id(user.id) is not None

@pytest.mark.medium(allow_external_systems=True)
def test_with_testcontainers(postgres_container):
    """Explicitly mark testcontainers usage to suppress warnings."""
    ...
```

## Phase 4: Enabling Strict Enforcement

Once all tests are categorized and violations are fixed:

### Update Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
# Switch to strict mode
test_categories_enforcement = "strict"

# Optionally enforce distribution targets
test_categories_distribution_enforcement = "warn"  # or "strict"
```

### CI Configuration

Update your CI to run tests by size:

```yaml
# .github/workflows/test.yml
jobs:
  small-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e .[test]
      - run: pytest -m small --test-categories-enforcement=strict

  medium-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e .[test]
      - run: pytest -m medium --test-categories-enforcement=strict
```

See [CI Integration](ci-integration.md) for complete examples.

## Handling Edge Cases

### Tests That Are Hard to Categorize

If a test does not fit neatly into a category, ask yourself:

1. **Can it be split?** A test that does multiple things should be separate tests.
2. **Can it be mocked?** External dependencies should be mocked for small tests.
3. **Is it really necessary?** Some integration tests duplicate unit test coverage.

### Tests That Need Gradual Migration

For tests that are difficult to migrate immediately, use `WARN` mode and recategorize them temporarily:

```python
# Option 1: Recategorize to medium temporarily during migration
@pytest.mark.medium  # TODO: Refactor to use mocks and change to @pytest.mark.small
def test_legacy_http_call():
    """Needs refactoring to use mocks."""
    ...

# Option 2: Use pytest.mark.skip for tests that need major refactoring
@pytest.mark.skip(reason="Migration in progress: needs mock refactoring (see #123)")
def test_complex_legacy_integration():
    ...
```

### Skipping Tests During Migration

If a test cannot be immediately fixed, mark it:

```python
@pytest.mark.skip(reason="Needs migration to use mocks (see #123)")
def test_problematic_integration():
    ...
```

## Migration Checklist

Use this checklist to track your migration progress:

- [ ] Install pytest-test-categories
- [ ] Configure warning mode
- [ ] Run tests and review warnings
- [ ] Categorize pure unit tests (no I/O)
- [ ] Categorize tests with mocked dependencies
- [ ] Categorize integration tests
- [ ] Fix network access violations in small tests
- [ ] Fix filesystem access violations in small tests
- [ ] Fix database access violations in small tests
- [ ] Verify distribution meets targets (80/15/5)
- [ ] Enable strict enforcement
- [ ] Update CI configuration
- [ ] Document testing conventions for team

## Next Steps

- [Common Patterns](common-patterns.md) - Fixture patterns and mocking strategies
- [CI Integration](ci-integration.md) - GitHub Actions, GitLab CI, and Jenkins examples
- [Filesystem Isolation](filesystem-isolation.md) - Detailed filesystem isolation examples
- [Network Isolation](network-isolation.md) - Detailed network isolation examples

## Reference: Sample Project

The [sample_project](https://github.com/mikelane/pytest-test-categories/tree/main/examples/sample_project) in the examples directory demonstrates a fully migrated codebase with:

- Small tests using mocks and fakes
- Medium tests using testcontainers
- Large tests for end-to-end scenarios
- Complete GitHub Actions workflow
- Configuration examples for all enforcement modes
