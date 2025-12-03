<p align="center">
  <img src="docs/_static/logo.svg" alt="pytest-test-categories logo" width="200">
</p>

<h1 align="center">Pytest Test Categories Plugin</h1>

<p align="center">
  <a href="https://pypi.org/project/pytest-test-categories/"><img src="https://img.shields.io/pypi/v/pytest-test-categories.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/pytest-test-categories/"><img src="https://img.shields.io/pypi/pyversions/pytest-test-categories.svg" alt="Python versions"></a>
  <a href="https://github.com/mikelane/pytest-test-categories/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/mikelane/pytest-test-categories/ci.yml?branch=main&label=CI" alt="CI Status"></a>
  <a href="https://codecov.io/gh/mikelane/pytest-test-categories"><img src="https://img.shields.io/codecov/c/github/mikelane/pytest-test-categories" alt="Code Coverage"></a>
  <a href="https://pytest-test-categories.readthedocs.io/en/latest/?badge=latest"><img src="https://readthedocs.org/projects/pytest-test-categories/badge/?version=latest" alt="Documentation Status"></a>
  <a href="https://pepy.tech/project/pytest-test-categories"><img src="https://static.pepy.tech/badge/pytest-test-categories/month" alt="Downloads"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
</p>

<p align="center">
  A pytest plugin that enforces test timing constraints, resource isolation, and validates test size distributions based on Google's "Software Engineering at Google" best practices.
</p>

**[Documentation](https://pytest-test-categories.readthedocs.io)** | **[PyPI](https://pypi.org/project/pytest-test-categories/)** | **[GitHub](https://github.com/mikelane/pytest-test-categories)**

## Why pytest-test-categories?

### The Problem

Most test suites suffer from:

- **Flaky tests** due to network timeouts, race conditions, or shared state
- **Slow CI pipelines** because tests lack time budgets
- **Testing pyramid inversion** with too many slow integration tests and too few fast unit tests
- **No enforced boundaries** between unit, integration, and system tests

### The Solution

pytest-test-categories brings Google's battle-tested testing philosophy to Python:

1. **Categorize tests by size** (small, medium, large, xlarge) with clear resource constraints
2. **Enforce hermeticity** by blocking network, filesystem, database, and subprocess access in small tests
3. **Enforce time limits** so slow tests fail fast
4. **Validate distribution** to maintain a healthy 80/15/5 test pyramid

When a small test tries to access the network, it fails immediately with actionable guidance:

```
HermeticityViolationError: Network access blocked in small test

Options:
  1. Mock the network call using responses, httpretty, or respx
  2. Use dependency injection to provide a fake HTTP client
  3. Change test category to @pytest.mark.medium (if network is required)
```

## Features

- **Test size categorization**: Mark tests with `@pytest.mark.small`, `@pytest.mark.medium`, `@pytest.mark.large`, or `@pytest.mark.xlarge`
- **Resource isolation**: Block network, filesystem, database, subprocess, and sleep access in small tests
- **Fixed time limits**: Enforce Google's standard time limits (1s/5min/15min/15min)
- **Distribution validation**: Ensure your test suite follows the recommended 80/15/5 test pyramid
- **JSON/XML reporting**: Export test size reports for CI integration and dashboards
- **Base test classes**: Inherit from `SmallTest`, `MediumTest`, `LargeTest`, or `XLargeTest`
- **Zero overhead**: Less than 1% performance impact on test execution
- **Parallel execution**: Full pytest-xdist compatibility for distributed testing

## Test Size Categories

| Resource | Small | Medium | Large | XLarge |
|----------|-------|--------|-------|--------|
| **Time Limit** | 1s | 5min | 15min | 15min |
| **Network** | ❌ Blocked | Localhost | ✓ Allowed | ✓ Allowed |
| **Filesystem** | ❌ Blocked | ✓ Allowed | ✓ Allowed | ✓ Allowed |
| **Database** | ❌ Blocked | ✓ Allowed | ✓ Allowed | ✓ Allowed |
| **Subprocess** | ❌ Blocked | ✓ Allowed | ✓ Allowed | ✓ Allowed |
| **Sleep** | ❌ Blocked | ✓ Allowed | ✓ Allowed | ✓ Allowed |

## Installation

### pip

```bash
pip install pytest-test-categories
```

### uv

```bash
uv add pytest-test-categories
```

### Poetry

```bash
poetry add pytest-test-categories
```

## Quick Start

### Basic Usage

Mark your tests with size markers:

```python
import pytest

@pytest.mark.small
def test_unit():
    """Fast, hermetic unit test - no network, no filesystem, no database."""
    assert 1 + 1 == 2

@pytest.mark.small
def test_with_mocking(mocker):
    """Mocked tests are still hermetic - mocks intercept before the network layer."""
    mocker.patch("requests.get").return_value.json.return_value = {"status": "ok"}
    # Your code that uses requests.get() works without hitting the network

@pytest.mark.medium
def test_integration(tmp_path):
    """Integration test - can access localhost and filesystem."""
    db_path = tmp_path / "test.db"
    # ... test with local database
```

Or inherit from base test classes:

```python
from pytest_test_categories import SmallTest, MediumTest

class DescribeUserService(SmallTest):
    """All tests in this class are automatically marked as small."""

    def test_validates_email_format(self):
        assert is_valid_email("user@example.com")

    def test_rejects_invalid_email(self):
        assert not is_valid_email("not-an-email")

class DescribeUserRepository(MediumTest):
    """Tests requiring database access."""

    def test_saves_user(self, db_connection):
        # ... test with real database
```

### Enable Enforcement

By default, enforcement is off. Enable it in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
# Resource isolation: "off" (default), "warn", or "strict"
test_categories_enforcement = "strict"

# Distribution validation: "off" (default), "warn", or "strict"
test_categories_distribution_enforcement = "warn"
```

Run pytest as usual:

```bash
pytest
```

## Configuration

### pyproject.toml

```toml
[tool.pytest.ini_options]
# Enforcement modes: "strict" (fail), "warn" (warning), "off" (disabled)
test_categories_enforcement = "strict"
test_categories_distribution_enforcement = "warn"
```

### Command-Line Options

CLI options override `pyproject.toml` settings:

```bash
# Enforcement modes
pytest --test-categories-enforcement=strict
pytest --test-categories-distribution-enforcement=warn

# Reporting
pytest --test-size-report=basic      # Summary report
pytest --test-size-report=detailed   # Per-test details
pytest --test-size-report=json       # JSON output
pytest --test-size-report=json --test-size-report-file=report.json
```

**Note:** Time limits are fixed per Google's testing standards and cannot be customized. This ensures consistent test categorization across all projects.

## Enforcement Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `off` | No enforcement (default) | Initial exploration |
| `warn` | Emit warnings, tests continue | Migration period |
| `strict` | Fail tests on violations | Production enforcement |

### Recommended Migration Path

```toml
# Week 1: Discovery - see what would fail
test_categories_enforcement = "off"

# Week 2-4: Migration - fix violations incrementally
test_categories_enforcement = "warn"

# Week 5+: Enforced - violations fail the build
test_categories_enforcement = "strict"
```

## Philosophy: No Override Markers

pytest-test-categories intentionally does **not** provide per-test override markers like `@pytest.mark.allow_network`.

If a test needs network access, filesystem access, or other resources, it should be marked with the appropriate size:

```python
# Wrong: Trying to bypass restrictions
@pytest.mark.small
@pytest.mark.allow_network  # This marker does not exist!
def test_api_call():
    ...

# Correct: Use the appropriate test size
@pytest.mark.medium  # Medium tests can access localhost
def test_api_call():
    ...

# Or: Mock the dependency for small tests
@pytest.mark.small
def test_api_call(httpx_mock):
    httpx_mock.add_response(url="https://api.example.com/", json={"status": "ok"})
    ...
```

**Why no escape hatches?**

1. **Flaky tests are expensive** - escape hatches become the norm, defeating the purpose
2. **Categories have meaning** - if a "small" test can access the network, it's not really a small test
3. **Encourages better design** - mocking and dependency injection lead to more testable code

See the [Design Philosophy](https://pytest-test-categories.readthedocs.io/en/latest/architecture/design-philosophy.html) documentation for the full rationale.

## Test Distribution Targets

| Size | Target Percentage | Tolerance |
|------|-------------------|-----------|
| Small | 80% | +/- 5% |
| Medium | 15% | +/- 5% |
| Large/XLarge | 5% | +/- 3% |

When distribution enforcement is enabled, pytest will warn or fail if your test distribution falls outside these ranges.

## Reporting

### Terminal Reports

```bash
# Basic summary report
pytest --test-size-report=basic

# Detailed report with per-test information
pytest --test-size-report=detailed
```

### JSON Report Export

For CI/CD integration and custom tooling:

```bash
# Output JSON report to terminal
pytest --test-size-report=json

# Write JSON report to a file
pytest --test-size-report=json --test-size-report-file=report.json
```

#### JSON Report Structure

```json
{
  "timestamp": "2025-11-29T12:00:00.000000Z",
  "summary": {
    "total_tests": 150,
    "distribution": {
      "small": {"count": 120, "percentage": 80.0, "target": 80.0},
      "medium": {"count": 22, "percentage": 14.67, "target": 15.0},
      "large": {"count": 6, "percentage": 4.0, "target": 4.0},
      "xlarge": {"count": 2, "percentage": 1.33, "target": 1.0}
    },
    "violations": {
      "timing": 0,
      "hermeticity": {
        "network": 0,
        "filesystem": 0,
        "process": 0,
        "database": 0,
        "sleep": 0,
        "total": 0
      }
    }
  },
  "tests": [
    {
      "name": "tests/test_example.py::test_fast_function",
      "size": "small",
      "duration": 0.002,
      "status": "passed",
      "violations": []
    }
  ]
}
```

## Documentation

For comprehensive documentation, visit **[pytest-test-categories.readthedocs.io](https://pytest-test-categories.readthedocs.io)**:

- **[Getting Started](https://pytest-test-categories.readthedocs.io/en/latest/getting-started.html)** - Installation and first steps
- **[User Guide](https://pytest-test-categories.readthedocs.io/en/latest/user-guide/index.html)** - Test sizes, isolation, timing, and distribution
- **[Configuration](https://pytest-test-categories.readthedocs.io/en/latest/configuration.html)** - All configuration options
- **[Examples](https://pytest-test-categories.readthedocs.io/en/latest/examples/index.html)** - Common patterns and CI integration
- **[API Reference](https://pytest-test-categories.readthedocs.io/en/latest/api-reference/index.html)** - Markers, fixtures, and error messages
- **[Architecture](https://pytest-test-categories.readthedocs.io/en/latest/architecture/index.html)** - Design philosophy and ADRs

## Project Resources

- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** - Community standards
- **[SECURITY.md](SECURITY.md)** - Security policy
- **[ROADMAP.md](ROADMAP.md)** - Project vision and milestones
- **[GitHub Discussions](https://github.com/mikelane/pytest-test-categories/discussions)** - Questions and ideas
- **[Issue Tracker](https://github.com/mikelane/pytest-test-categories/issues)** - Bug reports and feature requests

## Contributing

We welcome contributions! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

### Quick Start for Contributors

1. **Fork and clone** the repository
2. **Create an issue** describing what you plan to work on
3. **Create a feature branch** from main
4. **Make your changes** following our coding standards
5. **Run pre-commit hooks** to ensure quality: `uv run pre-commit run --all-files`
6. **Open a pull request** linking to your issue

## License

This project is licensed under the [MIT License](LICENSE).

---

Happy testing!
