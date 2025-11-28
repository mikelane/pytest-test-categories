# Troubleshooting

This section helps you diagnose and fix common issues with pytest-test-categories.

## Topics

```{toctree}
:maxdepth: 2

network-violations
filesystem-violations
```

## Common Issues

### Tests Missing Size Markers

**Symptom:**
```
PytestWarning: Test 'test_something' has no size marker.
```

**Solution:**
Add a size marker to your test:

```python
@pytest.mark.small  # or medium, large, xlarge
def test_something():
    pass
```

Or use a base test class:

```python
from pytest_test_categories import SmallTest

class TestMyFeature(SmallTest):
    def test_something(self):
        pass
```

### Timing Violations

**Symptom:**
```
TimingViolationError: Test exceeded time limit
Test: test_slow_operation
Size: SMALL
Duration: 2.34 seconds
Limit: 1.00 second
```

**Solutions:**

1. **Optimize the test**: Remove unnecessary operations, use mocks
2. **Change test size**: If the test legitimately needs more time, use `@pytest.mark.medium`
3. **Split the test**: Break into smaller, focused tests

### Distribution Warnings

**Symptom:**
```
WARNING: Test distribution outside target range.
Small tests: 65% (target: 80% +/- 5%)
```

**Solutions:**

1. Review which tests could be converted to smaller categories
2. Mock external dependencies instead of using real ones
3. Use dependency injection for testability

### Plugin Not Loading

**Symptom:**
Tests run but no size markers are recognized.

**Solutions:**

1. Verify installation:
   ```bash
   pip show pytest-test-categories
   ```

2. Check pytest plugins:
   ```bash
   pytest --co -q
   # Should show [SMALL], [MEDIUM], etc. labels
   ```

3. Verify entry point in pyproject.toml:
   ```toml
   [project.entry-points.pytest11]
   test_categories = "pytest_test_categories.plugin"
   ```

### Conflicts with Other Plugins

If pytest-test-categories conflicts with another plugin:

1. Check pytest plugin order:
   ```bash
   pytest --trace-config
   ```

2. Try adjusting hook order with `tryfirst=True` or `trylast=True`

3. Report the conflict as a [GitHub issue](https://github.com/mikelane/pytest-test-categories/issues)

## Getting Help

If you encounter an issue not covered here:

1. Search [existing issues](https://github.com/mikelane/pytest-test-categories/issues)
2. Check [GitHub Discussions](https://github.com/mikelane/pytest-test-categories/discussions)
3. Open a new issue with:
   - pytest-test-categories version
   - pytest version
   - Python version
   - Minimal reproduction case
   - Full error message
