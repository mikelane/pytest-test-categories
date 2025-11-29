# Pytest Test Categories Plugin

[![Documentation Status](https://readthedocs.org/projects/pytest-test-categories/badge/?version=latest)](https://pytest-test-categories.readthedocs.io/en/latest/?badge=latest)

## Overview

**Pytest Test Categories** is a plugin designed to help developers enforce test timing constraints and size distributions in their test suites. This plugin provides an effective way to categorize tests by their execution time and ensures that the test distribution meets predefined targets for different test sizes.

The test size categories and their time limits are based on recommendations from Google's "Software Engineering at Google" book. The plugin offers size markers such as `small`, `medium`, `large`, and `xlarge`, each with specific time constraints.

## Features

- **Categorization of tests by size:** Mark tests with predefined size markers to categorize them based on execution time.
- **Time limit enforcement:** Automatically fail tests that exceed their allocated time limit.
- **Test distribution validation:** Ensure that your test suite's size distribution adheres to best practices.
- **Plugin configuration and hooks:** Integrates with pytest's hook system to provide seamless functionality.

## Test Size Categories and Time Limits

| Size    | Default Time Limit |
|---------|-------------------|
| Small   | 1 second          |
| Medium  | 5 minutes         |
| Large   | 15 minutes        |
| XLarge  | 15 minutes        |

### Configuring Custom Time Limits

Time limits can be customized via `pyproject.toml` or CLI options:

```toml
[tool.pytest.ini_options]
# Custom time limits (in seconds)
test_categories_small_time_limit = "2.0"
test_categories_medium_time_limit = "600.0"
test_categories_large_time_limit = "1800.0"
test_categories_xlarge_time_limit = "1800.0"
```

Or via command line (CLI options take precedence over ini settings):

```bash
pytest --test-categories-small-time-limit=2.0 --test-categories-medium-time-limit=600.0
```

Time limits must follow ordering constraints: `small < medium < large <= xlarge`

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for fast, reliable dependency management. You can install the project by running:

```bash
uv sync --all-groups
```

## Usage

Mark your tests with size markers to categorize them. For example:

```python
import pytest

@pytest.mark.small
def test_fast_function():
    assert some_function() == expected_result

@pytest.mark.medium
def test_moderate_function():
    assert some_other_function() == another_result
```

Run pytest as usual:

```bash
uv run pytest
```

## Development

This project follows best practices for testing, linting, and code quality.

### Install Development Dependencies

```bash
uv sync --all-groups
```

### Setup Pre-commit Hooks

To ensure code quality, set up pre-commit hooks:

```bash
uv run pre-commit install
```

### Running Tests

This project uses [tox](https://tox.wiki/) for testing across multiple Python versions (3.11, 3.12, 3.13, 3.14).

```bash
# Test all Python versions in parallel (fast mode, used by pre-commit)
uv run tox run-parallel -e py311-fast,py312-fast,py313-fast,py314-fast

# Test all Python versions sequentially (full output)
uv run tox

# Test a specific Python version
uv run tox -e py312

# Run tests directly with pytest (single version)
uv run pytest

# Run tests with coverage
uv run coverage run -m pytest
uv run coverage report
```

### Code Quality

Run pre-commit hooks to automatically format and lint code:

```bash
# Run all pre-commit hooks
uv run pre-commit run --all-files

# Run individual tools
uv run ruff check --fix .
uv run ruff format .
uv run isort .
```

## How It Works

The plugin hooks into several pytest phases to:

- Count tests by size during collection
- Validate the test distribution at the end of collection
- Enforce time limits during test execution
- Modify the test report to display size labels next to test names

### Key Hooks

- `pytest_configure`: Registers the plugin and size markers
- `pytest_collection_modifyitems`: Tracks the number of tests in each size category
- `pytest_collection_finish`: Validates the distribution of test sizes
- `pytest_runtest_protocol`: Tracks the execution time of each test

## Test Distribution Targets

| Size         | Target Percentage | Tolerance |
|--------------|-------------------|-----------|
| Small        | 80%               | 5%        |
| Medium       | 15%               | 5%        |
| Large/XLarge | 5%                | 3%        |

## Reporting Options

The plugin provides multiple reporting formats for analyzing test size distribution and timing.

### Terminal Reports

```bash
# Basic summary report
pytest --test-size-report=basic

# Detailed report with per-test information
pytest --test-size-report=detailed
```

### JSON Report Export

For CI/CD integration and custom tooling, the plugin supports JSON report output:

```bash
# Output JSON report to terminal
pytest --test-size-report=json

# Write JSON report to a file
pytest --test-size-report=json --test-size-report-file=report.json
```

#### JSON Report Structure

The JSON report includes:

```json
{
  "version": "0.7.0",
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
      "hermeticity": 0
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

This format enables:
- **CI/CD Integration**: Parse results in GitHub Actions, GitLab CI, or other pipelines
- **Dashboard Visualization**: Feed data into monitoring tools like Grafana or custom dashboards
- **Trend Analysis**: Track test distribution and timing over time
- **Quality Gates**: Enforce test size policies programmatically

## Resource Isolation

The plugin enforces resource isolation for small tests to ensure test hermeticity. When enabled, small tests that attempt network or filesystem access will fail immediately or emit warnings, depending on the enforcement mode.

| Test Size | Network Access | Filesystem Access |
|-----------|---------------|-------------------|
| Small     | **Blocked** | **Blocked*** |
| Medium    | Allowed | Allowed |
| Large     | Allowed | Allowed |
| XLarge    | Allowed | Allowed |

*Small tests can access `tmp_path`, system temp directories, and configured allowed paths.

### Configuration

Resource isolation enforcement is configured via `pyproject.toml`:

```toml
[tool.pytest.ini_options]
# Enforcement modes: "strict", "warn", "off"
test_categories_enforcement = "strict"

# Additional allowed paths for filesystem access in small tests
test_categories_allowed_paths = [
    "tests/fixtures/",
]
```

Or via command line (CLI option takes precedence over ini setting):

```bash
pytest --test-categories-enforcement=strict
pytest --test-categories-allowed-paths=tests/fixtures/
```

### Enforcement Modes

| Mode | Behavior |
|------|----------|
| `strict` | Fail tests immediately on violations |
| `warn` | Emit warnings but allow tests to continue |
| `off` | Disable isolation enforcement (default) |

### Per-Test Override (Planned)

The `allow_network` and `allow_filesystem` markers will allow access for specific tests:

```python
@pytest.mark.small
@pytest.mark.allow_network  # Planned - not yet available
def test_special_case_network():
    ...

@pytest.mark.small
@pytest.mark.allow_filesystem  # Planned - not yet available
def test_special_case_filesystem():
    ...
```

### Documentation

**Network Isolation:**
- [User Guide: Network Isolation](docs/user-guide/network-isolation.md)
- [Troubleshooting: Network Violations](docs/troubleshooting/network-violations.md)
- [Examples: Network Isolation](docs/examples/network-isolation.md)
- [ADR-001: Network Isolation Architecture](docs/architecture/adr-001-network-isolation.md)

**Filesystem Isolation:**
- [User Guide: Filesystem Isolation](docs/user-guide/filesystem-isolation.md)
- [Troubleshooting: Filesystem Violations](docs/troubleshooting/filesystem-violations.md)
- [Examples: Filesystem Isolation](docs/examples/filesystem-isolation.md)
- [ADR-002: Filesystem Isolation Architecture](docs/architecture/adr-002-filesystem-isolation.md)

## Project Resources

### Documentation
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Comprehensive contribution guidelines
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** - Community standards and expectations
- **[SECURITY.md](SECURITY.md)** - Security policy and vulnerability reporting
- **[ROADMAP.md](ROADMAP.md)** - Project vision, goals, and milestones
- **[CLAUDE.md](CLAUDE.md)** - Architecture and development documentation

### Community
- **[GitHub Discussions](https://github.com/mikelane/pytest-test-categories/discussions)** - Ask questions and share ideas
- **[Issue Templates](.github/ISSUE_TEMPLATE/)** - Report bugs, request features, suggest improvements
- **[GitHub Projects](https://github.com/mikelane/pytest-test-categories/projects)** - Track development progress

## Contributing

We welcome contributions from the community! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

### Quick Start for Contributors

1. **Fork and clone** the repository
2. **Create an issue** describing what you plan to work on
3. **Create a feature branch** from main
4. **Make your changes** following our coding standards
5. **Run pre-commit hooks** to ensure quality
6. **Open a pull request** linking to your issue

For detailed instructions, see [CONTRIBUTING.md](CONTRIBUTING.md).

**Note for maintainers**: This repository requires [CodeQL Advanced Setup](.github/CODEQL_SETUP.md) configuration. GitHub's default CodeQL setup must be disabled in repository settings for the security workflow to function correctly.

### Ways to Contribute

- **Report bugs** using the [bug report template](.github/ISSUE_TEMPLATE/bug_report.yml)
- **Request features** using the [feature request template](.github/ISSUE_TEMPLATE/feature_request.yml)
- **Improve documentation** using the [documentation template](.github/ISSUE_TEMPLATE/documentation.yml)
- **Submit code** following our development workflow
- **Review pull requests** and provide constructive feedback
- **Help others** in GitHub Discussions

## License

This project is available under a dual-license model:

- **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0):** You are free to use, modify, and distribute the project for non-commercial purposes, provided that you give appropriate credit.

- **Commercial License:** If you wish to use this project in a commercial setting, please contact me at [mikelane@gmail.com](mailto:mikelane@gmail.com) to obtain a commercial license.

See the [LICENSE](LICENSE) file for details.

---

Happy testing!
