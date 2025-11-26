# Pytest Test Categories Plugin

## Overview

**Pytest Test Categories** is a plugin designed to help developers enforce test timing constraints and size distributions in their test suites. This plugin provides an effective way to categorize tests by their execution time and ensures that the test distribution meets predefined targets for different test sizes.

The test size categories and their time limits are based on recommendations from Google's "Software Engineering at Google" book. The plugin offers size markers such as `small`, `medium`, `large`, and `xlarge`, each with specific time constraints.

## Features

- **Categorization of tests by size:** Mark tests with predefined size markers to categorize them based on execution time.
- **Time limit enforcement:** Automatically fail tests that exceed their allocated time limit.
- **Test distribution validation:** Ensure that your test suite's size distribution adheres to best practices.
- **Plugin configuration and hooks:** Integrates with pytest's hook system to provide seamless functionality.

## Test Size Categories and Time Limits

| Size    | Time Limit  |
|---------|-------------|
| Small   | 1 second    |
| Medium  | 5 minutes   |
| Large   | 15 minutes  |
| XLarge  | 15 minutes  |

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

## Network Isolation (v0.4.0+)

The plugin enforces network isolation based on test size to ensure test hermeticity:

| Test Size | Network Access |
|-----------|---------------|
| Small     | **Blocked** - Must be hermetic |
| Medium    | Localhost only |
| Large     | Allowed |
| XLarge    | Allowed |

### Configuration

Configure network isolation enforcement via `pyproject.toml`:

```toml
[tool.pytest.ini_options]
# Enforcement modes: "strict", "warn", "off"
test_categories_enforcement = "strict"
```

Or via `pytest.ini`:

```ini
[pytest]
test_categories_enforcement = strict
```

Or via command line:

```bash
pytest --test-categories-enforcement=strict
```

### Enforcement Modes

| Mode | Behavior |
|------|----------|
| `strict` | Fail tests immediately on network violations |
| `warn` | Emit warnings but allow tests to continue |
| `off` | Disable network isolation enforcement |

### Per-Test Override

Allow network access for specific tests using the `allow_network` marker:

```python
@pytest.mark.small
@pytest.mark.allow_network  # Override: allow network for this test
def test_special_case():
    ...
```

### Documentation

- [User Guide: Network Isolation](docs/user-guide/network-isolation.md)
- [Troubleshooting: Network Violations](docs/troubleshooting/network-violations.md)
- [Examples: Network Isolation](docs/examples/network-isolation.md)
- [ADR-001: Network Isolation Architecture](docs/architecture/adr-001-network-isolation.md)

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
