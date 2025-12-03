# Configuration

pytest-test-categories can be configured through multiple mechanisms: pyproject.toml, pytest.ini, command-line options, and markers.

## Configuration Precedence

Configuration is applied in the following order (later overrides earlier):

1. Default values
2. Configuration file (pyproject.toml or pytest.ini)
3. Command-line options
4. Per-test markers

## Quick Reference

| Category | ini Option | CLI Option | Default |
|----------|------------|------------|---------|
| Enforcement | `test_categories_enforcement` | `--test-categories-enforcement` | `off` |
| Distribution | `test_categories_distribution_enforcement` | `--test-categories-distribution-enforcement` | `off` |
| Report | - | `--test-size-report` | none |
| Report File | - | `--test-size-report-file` | none |

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

# Distribution enforcement (test pyramid validation)
# Options: "strict", "warn", "off"
test_categories_distribution_enforcement = "warn"
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
test_categories_distribution_enforcement = warn
```

## Command-Line Options

### Test Size Report

Generate a report of tests by size category:

```bash
# Basic report (summary only)
pytest --test-size-report=basic

# Detailed report (includes individual tests)
pytest --test-size-report=detailed

# JSON report (machine-readable)
pytest --test-size-report=json

# JSON report saved to file
pytest --test-size-report=json --test-size-report-file=report.json
```

**Report Formats:**

| Format | Description | Use Case |
|--------|-------------|----------|
| `basic` | Summary counts and percentages | Quick overview |
| `detailed` | Individual test listings with timing | Debugging slow tests |
| `json` | Machine-readable JSON output | CI/CD integration, dashboards |

### Resource Isolation Enforcement

Control network, filesystem, process, database, and sleep isolation enforcement:

```bash
# Strict mode: fail on violations
pytest --test-categories-enforcement=strict

# Warn mode: emit warnings but don't fail
pytest --test-categories-enforcement=warn

# Disable enforcement
pytest --test-categories-enforcement=off
```

**Enforcement Modes:**

| Mode | Behavior |
|------|----------|
| `off` | No enforcement, violations not detected |
| `warn` | Violations emit pytest warnings, tests continue |
| `strict` | Violations raise exceptions, tests fail |

### Distribution Enforcement

Control test pyramid distribution enforcement:

```bash
# Strict mode: fail if distribution is outside acceptable range
pytest --test-categories-distribution-enforcement=strict

# Warn mode: emit warnings but don't fail
pytest --test-categories-distribution-enforcement=warn

# Disable distribution validation
pytest --test-categories-distribution-enforcement=off
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

### Medium Test Options

The medium marker accepts optional parameters:

```python
@pytest.mark.medium(allow_external_systems=True)
def test_with_docker():
    """Suppress external systems warning when using testcontainers."""
    pass
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `allow_external_systems` | `bool` | `False` | Suppress warnings when using Docker/testcontainers |


## Time Limits

Test sizes have **fixed time limits** that are not configurable. This follows Google's "Software Engineering at Google" philosophy where test sizes are DEFINITIONS, not suggestions.

| Size | Time Limit | Description |
|------|------------|-------------|
| Small | 1 second | Fast unit tests without external dependencies |
| Medium | 300 seconds (5 min) | Integration tests with local services |
| Large | 900 seconds (15 min) | Full system/E2E tests |
| XLarge | 900 seconds (15 min) | Extended tests with same limits as large |

Tests exceeding their time limit will fail with a `TimingViolationError` ([TC006](api-reference/error-messages.md#tc006-timing-violation)).

**Philosophy:** If a test exceeds its category's time limit, the correct action is to **recategorize the test** to a larger size, not to extend the limit. This ensures that test size categories maintain their semantic meaning across all projects.

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

# Plugin configuration - enforcement
test_categories_enforcement = "warn"
test_categories_distribution_enforcement = "warn"

# Default report option
addopts = ["--test-size-report=basic"]
```

## Configuration Options Reference

### ini Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `test_categories_enforcement` | string | `"off"` | Resource isolation enforcement mode: `"strict"`, `"warn"`, or `"off"` |
| `test_categories_distribution_enforcement` | string | `"off"` | Distribution validation enforcement mode: `"strict"`, `"warn"`, or `"off"` |

### CLI Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--test-size-report` | choice | none | Generate test size report: `basic`, `detailed`, or `json` |
| `--test-size-report-file` | path | none | Output file path for JSON report (requires `--test-size-report=json`) |
| `--test-categories-enforcement` | choice | none | Override resource isolation enforcement mode from command line |
| `--test-categories-distribution-enforcement` | choice | none | Override distribution enforcement mode from command line |

## Source Code References

| Component | Location |
|-----------|----------|
| CLI options registration | [`plugin.py#pytest_addoption`](https://github.com/mikelane/pytest-test-categories/blob/main/src/pytest_test_categories/plugin.py) |
| Time limit definitions | [`timing.py`](https://github.com/mikelane/pytest-test-categories/blob/main/src/pytest_test_categories/timing.py) |
| Enforcement mode handling | [`plugin.py#_get_enforcement_mode`](https://github.com/mikelane/pytest-test-categories/blob/main/src/pytest_test_categories/plugin.py) |
