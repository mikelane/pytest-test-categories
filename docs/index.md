# pytest-test-categories

A pytest plugin that enforces test timing constraints and validates test size distributions based on Google's "Software Engineering at Google" best practices.

## Overview

**pytest-test-categories** helps you maintain a healthy test suite by:

- **Categorizing tests by size**: Mark tests as `small`, `medium`, `large`, or `xlarge` based on their execution characteristics
- **Enforcing time limits**: Automatically fail tests that exceed their allocated time limit
- **Validating test distribution**: Ensure your test suite follows the recommended test pyramid
- **Enforcing network isolation**: Block network access in small tests to ensure hermeticity (planned feature)

## Test Size Categories

| Size | Time Limit | Network Access | Use Case |
|------|------------|----------------|----------|
| Small | 1 second | Blocked | Unit tests, pure functions |
| Medium | 5 minutes | Allowed | Integration tests with local services |
| Large | 15 minutes | Allowed | End-to-end tests |
| XLarge | 15 minutes | Allowed | Extended tests |

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
def test_fast_function():
    assert some_function() == expected_result

@pytest.mark.medium
def test_database_integration():
    # Test with local database
    pass
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
```

```{toctree}
:maxdepth: 2
:caption: Examples

examples/index
```

```{toctree}
:maxdepth: 2
:caption: Reference

api/index
```

```{toctree}
:maxdepth: 2
:caption: Architecture

architecture/index
```

```{toctree}
:maxdepth: 2
:caption: Troubleshooting

troubleshooting/index
```

```{toctree}
:maxdepth: 2
:caption: Operations

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

This project is available under a dual-license model:

- **CC BY-NC 4.0**: Free for non-commercial use with attribution
- **Commercial License**: Contact [mikelane@gmail.com](mailto:mikelane@gmail.com) for commercial licensing

## Indices and tables

* {ref}`genindex`
* {ref}`modindex`
* {ref}`search`
