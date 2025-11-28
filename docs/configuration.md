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

# Resource isolation enforcement (network and filesystem)
# Options: "strict", "warn", "off"
test_categories_enforcement = "warn"

# Additional allowed paths for filesystem access in small tests
test_categories_allowed_paths = [
    "tests/fixtures/",
    "src/mypackage/data/",
]
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
test_categories_allowed_paths = tests/fixtures/,src/mypackage/data/
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

### Resource Isolation Enforcement

Control network and filesystem isolation enforcement:

```bash
# Strict mode: fail on violations
pytest --test-categories-enforcement=strict

# Warn mode: emit warnings but don't fail
pytest --test-categories-enforcement=warn

# Disable enforcement
pytest --test-categories-enforcement=off
```

### Allowed Filesystem Paths

Add additional allowed paths for filesystem access in small tests:

```bash
# Single path
pytest --test-categories-allowed-paths=tests/fixtures/

# Multiple paths (comma-separated)
pytest --test-categories-allowed-paths=tests/fixtures/,src/mypackage/data/
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

### Resource Isolation Overrides (Planned)

Override network or filesystem isolation for specific tests:

```python
@pytest.mark.small
@pytest.mark.allow_network  # Planned - not yet available
def test_special_case_network():
    """This small test is allowed to access the network."""
    pass

@pytest.mark.small
@pytest.mark.allow_filesystem  # Planned - not yet available
def test_special_case_filesystem():
    """This small test is allowed to access the filesystem."""
    pass

@pytest.mark.small
@pytest.mark.allow_filesystem_paths('/specific/path')  # Planned - not yet available
def test_with_specific_path():
    """This small test can access a specific path."""
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
- No resource isolation enforcement (enforcement mode is "off")
- Distribution validation runs after collection
- Time limits are enforced during test execution
- Unmarked tests trigger a warning but are allowed to run

### Default Allowed Filesystem Paths

Even without configuration, small tests can access these paths:

1. **System temp directory**: `tempfile.gettempdir()` and subdirectories
2. **pytest basetemp**: Where `tmp_path` fixture creates directories
3. **Test-specific tmp_path**: Automatically allowed when using the fixture

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
test_categories_allowed_paths = [
    "tests/fixtures/",
    "src/mypackage/data/",
]
addopts = ["--test-size-report=basic"]
```

## Configuration Options Reference

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `test_categories_enforcement` | string | `"off"` | Enforcement mode: `"strict"`, `"warn"`, or `"off"` |
| `test_categories_allowed_paths` | list | `[]` | Additional paths allowed for filesystem access in small tests |
| `--test-size-report` | CLI | none | Generate test size report: `basic` or `detailed` |
| `--test-categories-enforcement` | CLI | none | Override enforcement mode from command line |
| `--test-categories-allowed-paths` | CLI | none | Override allowed paths from command line |
