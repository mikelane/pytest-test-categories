# Pytest Test Categories

A pytest plugin that enforces test timing constraints, resource isolation, and validates test size distributions based on Google's "Software Engineering at Google" best practices.

## Overview

**pytest-test-categories** helps you maintain a healthy, reliable test suite by:

- **Categorizing tests by size**: Mark tests as `small`, `medium`, `large`, or `xlarge` based on their execution characteristics
- **Enforcing time limits**: Automatically fail tests that exceed their allocated time limit
- **Validating test distribution**: Ensure your test suite follows the recommended test pyramid (80/15/5)
- **Enforcing resource isolation**: Block network, filesystem, database, subprocess, and sleep access in small tests to ensure hermeticity
- **Zero-overhead design**: Less than 1% overhead on test execution

## Test Size Categories

| Size | Time Limit | Network | Filesystem | Database | Subprocess | Sleep |
|------|------------|---------|------------|----------|------------|-------|
| Small | 1 second | Blocked | Blocked | Blocked | Blocked | Blocked |
| Medium | 5 minutes | Localhost | Allowed | Allowed | Allowed | Allowed |
| Large | 15 minutes | Allowed | Allowed | Allowed | Allowed | Allowed |
| XLarge | 15 minutes | Allowed | Allowed | Allowed | Allowed | Allowed |

## Quick Start

### Installation

```bash
pip install pytest-test-categories
```

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

Run pytest as usual:

```bash
pytest
```

## Documentation

```{toctree}
:maxdepth: 2
:caption: Getting Started

getting-started
```

```{toctree}
:maxdepth: 2
:caption: User Guide

user-guide/index
```

```{toctree}
:maxdepth: 2
:caption: Configuration

configuration
compatibility
ide-integration
```

```{toctree}
:maxdepth: 2
:caption: Examples & Patterns

examples/index
```

```{toctree}
:maxdepth: 2
:caption: API Reference

api-reference/index
```

```{toctree}
:maxdepth: 2
:caption: Architecture & Design

architecture/index
```

```{toctree}
:maxdepth: 2
:caption: Troubleshooting

troubleshooting/index
```

```{toctree}
:maxdepth: 2
:caption: Performance & Operations

performance
deployment
monitoring
```

```{toctree}
:maxdepth: 1
:caption: Project

changelog
contributing
```

## Target Test Distribution

Following Google's recommendations, a healthy test suite should have:

| Size | Target | Tolerance |
|------|--------|-----------|
| Small | 80% | +/- 5% |
| Medium | 15% | +/- 5% |
| Large/XLarge | 5% | +/- 3% |

## License

This project is licensed under the [MIT License](https://github.com/mikelane/pytest-test-categories/blob/main/LICENSE).

## Indices and tables

* {ref}`genindex`
* {ref}`modindex`
* {ref}`search`
