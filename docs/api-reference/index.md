# API Reference

This section provides comprehensive API documentation for pytest-test-categories.

## Overview

pytest-test-categories provides a complete API for categorizing tests by size, enforcing resource isolation, validating test distribution, and generating reports.

## Contents

### [Markers Reference](markers.md)

Documentation for all pytest markers provided by the plugin:

- **Size Markers**: `@pytest.mark.small`, `@pytest.mark.medium`, `@pytest.mark.large`, `@pytest.mark.xlarge`
- **Base Test Classes**: `SmallTest`, `MediumTest`, `LargeTest`, `XLargeTest`
- **Marker Inheritance**: Class-level, module-level, and precedence rules

### [Fixtures Reference](fixtures.md)

Guidance on fixture usage with pytest-test-categories:

- **Recommended Fixtures**: Best practices for each test size
- **Fixture Scope**: Scope recommendations by test category
- **Compatibility**: Integration with pytest-mock, pytest-django, etc.

### [Error Messages Reference](error-messages.md)

Comprehensive index of all error codes and messages:

- **TC001-TC005**: Resource isolation violations (network, filesystem, process, database, sleep)
- **TC006**: Timing violations
- **TC007**: Distribution warnings
- **Exception Hierarchy**: All exception classes and their relationships

## Quick Links

| Topic | Description |
|-------|-------------|
| [Configuration](../configuration.md) | All CLI and ini options |
| [Markers](markers.md) | Size markers and base classes |
| [Fixtures](fixtures.md) | Fixture recommendations |
| [Errors](error-messages.md) | Error codes and resolution |

## Module Reference

### Core Modules

| Module | Description |
|--------|-------------|
| `pytest_test_categories.plugin` | Pytest hook implementations |
| `pytest_test_categories.types` | Core type definitions (TestSize, TestTimer, etc.) |
| `pytest_test_categories.timing` | Time limit configuration and validation |
| `pytest_test_categories.test_bases` | Base test classes for inheritance |

### Exception Modules

| Module | Description |
|--------|-------------|
| `pytest_test_categories.errors` | Error code registry |
| `pytest_test_categories.exceptions` | Exception classes for violations |

### Service Modules

| Module | Description |
|--------|-------------|
| `pytest_test_categories.services.test_discovery` | Test size marker discovery |
| `pytest_test_categories.services.timing_validation` | Timing validation logic |
| `pytest_test_categories.services.distribution_validation` | Distribution validation |
| `pytest_test_categories.services.test_reporting` | Report generation |

### Adapter Modules

| Module | Description |
|--------|-------------|
| `pytest_test_categories.adapters.network` | Network blocking implementation |
| `pytest_test_categories.adapters.filesystem` | Filesystem blocking implementation |
| `pytest_test_categories.adapters.process` | Subprocess blocking implementation |
| `pytest_test_categories.adapters.database` | Database blocking implementation |
| `pytest_test_categories.adapters.sleep` | Sleep blocking implementation |

## Public API

### Markers

```python
import pytest

# Size markers
@pytest.mark.small      # Unit tests, 1s limit
@pytest.mark.medium     # Integration tests, 5min limit
@pytest.mark.large      # E2E tests, 15min limit
@pytest.mark.xlarge     # Extended tests, 15min limit

# With parameters
@pytest.mark.medium(allow_external_systems=True)
```

### Base Classes

```python
from pytest_test_categories import SmallTest, MediumTest, LargeTest, XLargeTest

class MyUnitTests(SmallTest):
    def test_example(self):
        pass
```

### Types

```python
from pytest_test_categories.types import TestSize

# Enum values
TestSize.SMALL
TestSize.MEDIUM
TestSize.LARGE
TestSize.XLARGE

# Properties
size.marker_name  # 'small', 'medium', etc.
size.label        # '[SMALL]', '[MEDIUM]', etc.
size.network_mode # NetworkMode enum value
```

### Exceptions

```python
from pytest_test_categories.exceptions import (
    HermeticityViolationError,
    NetworkAccessViolationError,
    FilesystemAccessViolationError,
    SubprocessViolationError,
    DatabaseViolationError,
    SleepViolationError,
)
from pytest_test_categories.timing import TimingViolationError
from pytest_test_categories.services.distribution_validation import DistributionViolationError
```

## Version Compatibility

| pytest-test-categories | Python | pytest |
|------------------------|--------|--------|
| 1.x | 3.11+ | 7.0+ |

## Source Code

The complete source code is available on GitHub:

- Repository: [github.com/mikelane/pytest-test-categories](https://github.com/mikelane/pytest-test-categories)
- Source: [`src/pytest_test_categories/`](https://github.com/mikelane/pytest-test-categories/tree/main/src/pytest_test_categories)
