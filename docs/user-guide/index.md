# User Guide

This user guide provides comprehensive documentation for using pytest-test-categories in your projects.

## Core Concepts

pytest-test-categories is built around the test size taxonomy from Google's "Software Engineering at Google" book. The plugin helps you maintain a healthy test suite by enforcing timing constraints, resource isolation, and validating test distribution.

## Topics

```{toctree}
:maxdepth: 2

test-sizes
timing-enforcement
distribution-validation
reporting
```

## Resource Isolation

The plugin enforces resource restrictions based on test size, ensuring small tests remain hermetic and fast.

```{toctree}
:maxdepth: 2

network-isolation
filesystem-isolation
process-isolation
database-isolation
sleep-blocking
threading-monitoring
mocking-and-small-tests
```

## Quick Reference

### Test Size Markers

| Marker | Time Limit | Network | Filesystem | Subprocess | Database | Sleep | Threading |
|--------|------------|---------|------------|------------|----------|-------|-----------|
| `@pytest.mark.small` | 1 second | Blocked | Blocked | Blocked | Blocked | Blocked | Warned |
| `@pytest.mark.medium` | 5 minutes | Localhost | Allowed | Allowed | Allowed | Allowed | Allowed |
| `@pytest.mark.large` | 15 minutes | Allowed | Allowed | Allowed | Allowed | Allowed | Allowed |
| `@pytest.mark.xlarge` | 15 minutes | Allowed | Allowed | Allowed | Allowed | Allowed | Allowed |

### Resource Isolation Summary

| Resource | Small Tests | Medium Tests | Large/XLarge Tests |
|----------|-------------|--------------|-------------------|
| **Network** | Blocked | Localhost only | Allowed |
| **Filesystem** | Blocked | Allowed | Allowed |
| **Subprocess** | Blocked | Allowed | Allowed |
| **Database** | Blocked (including :memory:) | Allowed | Allowed |
| **Sleep** | Blocked | Allowed | Allowed |
| **Threading** | Warned | Allowed | Allowed |

### Base Test Classes

```python
from pytest_test_categories import SmallTest, MediumTest, LargeTest, XLargeTest

class TestMyFeature(SmallTest):
    def test_example(self):
        assert True
```

### Distribution Targets

| Size | Target | Range |
|------|--------|-------|
| Small | 80% | 75-85% |
| Medium | 15% | 10-20% |
| Large/XLarge | 5% | 2-8% |

### Enforcement Modes

Configure enforcement via `pyproject.toml`:

```toml
[tool.pytest.ini_options]
# Options: "strict", "warn", "off"
test_categories_enforcement = "strict"
```

| Mode | Behavior |
|------|----------|
| `strict` | Violations fail tests immediately |
| `warn` | Violations emit warnings, tests continue |
| `off` | No enforcement |

### If a Test Needs Resources, Change Its Size

The test size defines the constraints, not the other way around. If a test genuinely requires network, filesystem, or subprocess access, recategorize it:

```python
import pytest

# Tests that need network access should be medium or large
@pytest.mark.medium  # Medium tests can access localhost
def test_with_local_database():
    ...

@pytest.mark.large  # Large tests can access external networks
def test_external_api_integration():
    ...

# Use mocking for small tests
@pytest.mark.small
def test_api_client(mocker):
    mocker.patch("requests.get", return_value=Mock(json=lambda: {"key": "value"}))
    ...
```

## Getting Started

1. **Install the plugin**: `pip install pytest-test-categories`
2. **Mark your tests**: Add `@pytest.mark.small`, `@pytest.mark.medium`, etc.
3. **Enable enforcement**: Set `test_categories_enforcement = "warn"` in config
4. **Review warnings**: Fix violations or adjust test sizes
5. **Go strict**: Set `test_categories_enforcement = "strict"` for CI

## Best Practices

1. **Start with 80% small tests** - They're fast and reliable
2. **Use WARN mode first** - Identify violations without breaking CI
3. **Fix violations systematically** - Small tests first, then medium
4. **Mock external resources** - Use pytest-mock, responses, pyfakefs
5. **Design for testability** - Use dependency injection
6. **Categorize correctly** - If a test needs resources, use the right size
