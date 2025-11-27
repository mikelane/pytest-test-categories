# Configuration

pytest-test-categories can be configured through multiple mechanisms: pyproject.toml, pytest.ini, command-line options, and markers.

## Configuration Precedence

Configuration is applied in the following order (later overrides earlier):

1. Default values
2. Configuration file (pyproject.toml or pytest.ini)
3. Command-line options
4. Per-test markers

## pyproject.toml

The recommended way to configure pytest-test-categories is through `pyproject.toml`:

```toml
[tool.pytest.ini_options]
# Test size markers (automatically registered)
markers = [
    "small: Fast, hermetic unit tests (< 1s)",
    "medium: Integration tests with local services (< 5min)",
    "large: End-to-end tests (< 15min)",
    "xlarge: Extended tests (< 15min)",
]

# Network isolation enforcement (planned feature)
# Options: "strict", "warn", "off"
test_categories_enforcement = "warn"
```

## pytest.ini

Alternatively, use `pytest.ini`:

```ini
[pytest]
markers =
    small: Fast, hermetic unit tests (< 1s)
    medium: Integration tests with local services (< 5min)
    large: End-to-end tests (< 15min)
    xlarge: Extended tests (< 15min)

test_categories_enforcement = warn
```

## Command-Line Options

### Test Size Report

Generate a report of tests by size category:

```bash
# Basic report (summary only)
pytest --test-size-report=basic

# Detailed report (includes individual tests)
pytest --test-size-report=detailed
```

### Network Enforcement (Planned)

Control network isolation enforcement:

```bash
# Strict mode: fail on network violations
pytest --test-categories-enforcement=strict

# Warn mode: emit warnings but don't fail
pytest --test-categories-enforcement=warn

# Disable enforcement
pytest --test-categories-enforcement=off
```

## Markers

### Size Markers

Mark tests with their size category:

```python
import pytest

@pytest.mark.small
def test_unit():
    pass

@pytest.mark.medium
def test_integration():
    pass

@pytest.mark.large
def test_e2e():
    pass

@pytest.mark.xlarge
def test_extended():
    pass
```

### Network Override (Planned)

Override network isolation for specific tests:

```python
@pytest.mark.small
@pytest.mark.allow_network  # Planned - not yet available
def test_special_case():
    """This small test is allowed to access the network."""
    pass
```

## Time Limits

Each test size has a predefined time limit:

| Size | Time Limit |
|------|------------|
| Small | 1 second |
| Medium | 5 minutes (300 seconds) |
| Large | 15 minutes (900 seconds) |
| XLarge | 15 minutes (900 seconds) |

Tests exceeding their time limit will fail with a `TimingViolationError`.

## Distribution Targets

The plugin validates that your test suite follows the recommended distribution:

| Size | Target | Tolerance | Acceptable Range |
|------|--------|-----------|------------------|
| Small | 80% | +/- 5% | 75% - 85% |
| Medium | 15% | +/- 5% | 10% - 20% |
| Large/XLarge | 5% | +/- 3% | 2% - 8% |

### Critical Thresholds

The plugin warns when distribution is severely out of balance:

- **Small tests < 50%**: Critical warning - test pyramid is inverted
- **Medium tests > 20%**: Warning - too many medium tests
- **Large/XLarge > 8%**: Warning - too many slow tests

## Environment Variables

Currently, pytest-test-categories does not use environment variables for configuration. All configuration is done through pytest's standard configuration mechanisms.

## Default Behavior

If no configuration is provided:

- All size markers are registered automatically
- No network enforcement (enforcement mode is "off")
- Distribution validation runs after collection
- Time limits are enforced during test execution
- Unmarked tests trigger a warning but are allowed to run

## Example Complete Configuration

```toml
[tool.pytest.ini_options]
# Test paths
testpaths = ["tests"]

# Test discovery patterns
python_files = ["test_*.py", "it_*.py"]
python_functions = ["test_*", "it_*"]
python_classes = ["Test*", "Describe*"]

# Size markers (automatically registered by plugin)
markers = [
    "small: Fast, hermetic unit tests (< 1s)",
    "medium: Integration tests with local services (< 5min)",
    "large: End-to-end tests (< 15min)",
    "xlarge: Extended tests (< 15min)",
]

# Plugin configuration
test_categories_enforcement = "warn"
addopts = ["--test-size-report=basic"]
```
