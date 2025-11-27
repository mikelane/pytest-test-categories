# User Guide

This user guide provides comprehensive documentation for using pytest-test-categories in your projects.

## Core Concepts

pytest-test-categories is built around the test size taxonomy from Google's "Software Engineering at Google" book. The plugin helps you maintain a healthy test suite by enforcing timing constraints and validating test distribution.

## Topics

```{toctree}
:maxdepth: 2

test-sizes
timing-enforcement
distribution-validation
reporting
network-isolation
```

## Quick Reference

### Test Size Markers

| Marker | Time Limit | Network | Use Case |
|--------|------------|---------|----------|
| `@pytest.mark.small` | 1 second | Blocked | Unit tests |
| `@pytest.mark.medium` | 5 minutes | Allowed | Integration tests |
| `@pytest.mark.large` | 15 minutes | Allowed | E2E tests |
| `@pytest.mark.xlarge` | 15 minutes | Allowed | Extended tests |

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
