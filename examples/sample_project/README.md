# Sample Project: pytest-test-categories Best Practices

This example project demonstrates best practices for test categorization using pytest-test-categories, following Google's "Software Engineering at Google" test size guidelines.

## Overview

The project includes:
- **Source code** demonstrating common patterns (API client, database repository, file processor)
- **Small tests** using mocks, fakes, and `tmp_path` for fast, hermetic testing
- **Medium tests** using localhost servers and testcontainers
- **Large tests** for full integration scenarios
- **Configuration examples** for various enforcement modes

## Quick Start

```bash
# Install dependencies
uv sync --all-groups

# Run all tests
uv run pytest

# Run only small tests (fast, hermetic)
uv run pytest -m small

# Run with test size reporting
uv run pytest --test-size-report=detailed

# Run with strict enforcement
uv run pytest --test-categories-enforcement=strict
```

## Test Organization

```
tests/
  small/                    # Fast, hermetic tests (target: 80% of suite)
    test_pure_logic.py      # No mocking needed
    test_with_mocks.py      # HTTP mocking, database fakes, tmp_path
  medium/                   # May use localhost/containers (target: 15%)
    test_localhost_api.py   # Real HTTP server on localhost
    test_with_testcontainers.py  # Docker containers
  large/                    # Full integration (target: 5%)
    test_full_integration.py  # End-to-end scenarios
  conftest.py              # Shared fixtures
```

## Test Size Guidelines

### Small Tests (80% of suite)

Small tests are fast, deterministic, and hermetic:

- **No network access** - Use `pytest-httpx` for HTTP mocking
- **No filesystem access** - Use `tmp_path` fixture for isolated file operations
- **No database connections** - Use in-memory fakes (e.g., `FakeProductRepository`)
- **No subprocess spawning** - Mock subprocess calls
- **Complete in < 1 second**

Example:
```python
@pytest.mark.small
def it_fetches_user_with_mocked_http(httpx_mock):
    httpx_mock.add_response(json={'id': 1, 'name': 'Alice'})
    client = ApiClient(base_url='https://api.example.com')

    user = client.get_user(1)

    assert user.name == 'Alice'
```

### Medium Tests (15% of suite)

Medium tests may use localhost and containers:

- **Localhost network allowed** - Can run local HTTP servers
- **Containers allowed** - Use testcontainers for real databases
- **Complete in < 5 minutes**
- **Use `allow_external_systems=True`** for testcontainers

Example:
```python
@pytest.mark.medium(allow_external_systems=True)
def it_saves_to_postgres(postgres_container):
    repo = PostgresProductRepository(connection_params={...})

    saved = repo.save(Product(id=0, name='Widget', price=9.99))

    assert saved.id > 0
```

### Large Tests (5% of suite)

Large tests are for full integration:

- **External network allowed**
- **Real external services allowed**
- **Complete in < 15 minutes**
- **Use sparingly** - Most testing should be small/medium

Example:
```python
@pytest.mark.large
def it_processes_complete_data_pipeline(integration_temp_dir):
    # Full end-to-end test with multiple components
    ...
```

## Configuration Examples

### Basic Configuration (pyproject.toml)

```toml
[tool.pytest.ini_options]
# Warn on hermeticity violations (good for adoption)
test_categories_enforcement = "warn"
```

### Strict Mode

```toml
[tool.pytest.ini_options]
# Fail tests that violate hermeticity
test_categories_enforcement = "strict"

# Also enforce distribution percentages
test_categories_distribution_enforcement = "strict"
```

### Custom Time Limits

```toml
[tool.pytest.ini_options]
test_categories_small_time_limit = "2.0"    # 2 seconds
test_categories_medium_time_limit = "600.0"  # 10 minutes
```

### CLI Overrides

```bash
# Override enforcement mode
pytest --test-categories-enforcement=strict

# Override time limits
pytest --test-categories-small-time-limit=0.5

# Generate JSON report
pytest --test-size-report=json --test-size-report-file=report.json
```

## CI Integration

See `.github/workflows/test.yml` for a complete GitHub Actions example showing:

- Running tests by category (small first, then medium, then large)
- Generating and uploading test reports
- Coverage with test categories
- Skipping slow tests in PR builds

## Best Practices

1. **Start with small tests** - Default to small unless you have a specific reason not to
2. **Use fakes over mocks** - Fakes like `FakeProductRepository` are more maintainable
3. **Use `tmp_path` for files** - Never access the real filesystem in small tests
4. **Mark testcontainers correctly** - Use `@pytest.mark.medium(allow_external_systems=True)`
5. **Monitor distribution** - Aim for 80/15/5 split across small/medium/large
6. **Run small tests first in CI** - Get fast feedback before running slower tests

## Resources

- [pytest-test-categories documentation](https://pytest-test-categories.readthedocs.io/)
- [Software Engineering at Google - Testing Overview](https://abseil.io/resources/swe-book)
- [pytest-httpx documentation](https://colin-b.github.io/pytest_httpx/)
- [testcontainers-python documentation](https://testcontainers-python.readthedocs.io/)
