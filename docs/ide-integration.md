# IDE Integration Guide

This guide covers how to effectively use pytest-test-categories with popular IDEs, including PyCharm and VS Code.

## Overview

pytest-test-categories integrates seamlessly with IDEs that support pytest. The plugin registers custom markers (`small`, `medium`, `large`, `xlarge`) that appear in test explorers and can be used to filter test runs.

## PyCharm Integration

### Automatic Detection

PyCharm automatically detects pytest-test-categories when it is installed in your project environment. The plugin's markers are registered through pytest's standard marker registration mechanism, making them visible in PyCharm's test explorer.

### Viewing Size Markers in Test Explorer

When you open the test explorer (View > Tool Windows > Python Tests), tests are displayed with their markers. The size labels (`[SMALL]`, `[MEDIUM]`, `[LARGE]`, `[XLARGE]`) are appended to test IDs during collection.

**What you will see:**
- Test names include size labels: `test_addition[SMALL]`
- The test tree shows the hierarchical structure of your tests
- Marker information appears in the test node display

### Creating Run Configurations with Marker Filters

To run only tests of a specific size:

1. Open **Run > Edit Configurations**
2. Click **+** and select **pytest**
3. In the **Additional Arguments** field, add the marker filter:
   ```
   -m small
   ```
4. Name the configuration (e.g., "Small Tests Only")
5. Click **Apply** and **OK**

**Common filter configurations:**

| Configuration Name | Additional Arguments | Description |
|-------------------|---------------------|-------------|
| Small Tests | `-m small` | Run only small (unit) tests |
| Medium Tests | `-m medium` | Run only medium (integration) tests |
| Large Tests | `-m large` | Run only large (e2e) tests |
| Fast Tests | `-m "small or medium"` | Run all tests under 5 minutes |
| Slow Tests | `-m "large or xlarge"` | Run only slow tests |

### Running Tests by Size from the Context Menu

Right-click on a test file or directory in the Project view and select:
- **Run 'pytest in ...'** to run all tests
- **Run 'pytest in ...' with Parameters** to add marker filters

Alternatively, create multiple run configurations for different test sizes and switch between them using the configuration dropdown in the toolbar.

### Configuring pytest in PyCharm

Ensure PyCharm uses the correct pytest configuration:

1. Open **Settings/Preferences > Tools > Python Integrated Tools**
2. Set **Default test runner** to **pytest**
3. Optionally, add default pytest arguments in the **Additional Arguments** field

### PyCharm Gotchas and Tips

**Marker Registration Warnings**

If PyCharm shows warnings about unknown markers, ensure your `pyproject.toml` or `pytest.ini` includes the marker definitions:

```toml
[tool.pytest.ini_options]
markers = [
    "small: Fast, hermetic unit tests (< 1s)",
    "medium: Integration tests with local services (< 5min)",
    "large: End-to-end tests (< 15min)",
    "xlarge: Extended tests (< 15min)",
]
```

Note: pytest-test-categories automatically registers these markers, but explicit declaration helps PyCharm's static analysis.

**Test Discovery Issues**

If tests are not discovered:

1. Verify the project interpreter is correctly configured
2. Check that pytest-test-categories is installed in the active environment
3. Ensure `testpaths` in your pytest configuration points to your test directory
4. Invalidate caches: **File > Invalidate Caches / Restart**

**Coverage Integration**

When using coverage with pytest-test-categories, use `coverage run` instead of `pytest --cov`:

```bash
coverage run -m pytest -m small
coverage report
```

This ensures module-level code is tracked correctly.

**Parallel Test Execution**

PyCharm supports parallel test execution with pytest-xdist. To run tests in parallel:

1. Edit your run configuration
2. Add `-n auto` to **Additional Arguments**
3. Combine with marker filters: `-m small -n auto`

## VS Code Integration

### Prerequisites

Install the following extensions:
- **Python** (by Microsoft) - Required for Python support
- **Python Test Explorer for Visual Studio Code** (optional but recommended for enhanced test UI)

### Automatic Detection

VS Code's Python extension automatically detects pytest and pytest-test-categories when properly configured. The plugin's markers are recognized and can be used for filtering.

### Configuring Python Testing

1. Open **Command Palette** (Ctrl+Shift+P / Cmd+Shift+P)
2. Search for **Python: Configure Tests**
3. Select **pytest** as the test framework
4. Select the test directory (typically `tests`)

VS Code creates or updates `.vscode/settings.json` with pytest configuration.

### Recommended settings.json Configuration

Create or update `.vscode/settings.json` in your project:

```json
{
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "python.testing.pytestArgs": [
        "tests"
    ],
    "python.testing.autoTestDiscoverOnSaveEnabled": true
}
```

### Running Tests by Size

**Using the Test Explorer:**

1. Open the Testing sidebar (flask icon or Ctrl+Shift+T)
2. Tests are displayed hierarchically with their markers
3. Right-click on a test or folder to run/debug

**Using marker filters:**

To run tests of a specific size, modify `python.testing.pytestArgs`:

```json
{
    "python.testing.pytestArgs": [
        "tests",
        "-m", "small"
    ]
}
```

**Creating multiple configurations:**

Use VS Code's multi-root workspaces or create task configurations in `.vscode/tasks.json`:

```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Run Small Tests",
            "type": "shell",
            "command": "pytest",
            "args": ["-m", "small", "-v"],
            "group": "test",
            "problemMatcher": []
        },
        {
            "label": "Run Medium Tests",
            "type": "shell",
            "command": "pytest",
            "args": ["-m", "medium", "-v"],
            "group": "test",
            "problemMatcher": []
        },
        {
            "label": "Run All Fast Tests",
            "type": "shell",
            "command": "pytest",
            "args": ["-m", "small or medium", "-v"],
            "group": "test",
            "problemMatcher": []
        }
    ]
}
```

Run these tasks via **Terminal > Run Task** or the Command Palette.

### Launch Configurations for Debugging

Create `.vscode/launch.json` for debugging tests by size:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Small Tests",
            "type": "debugpy",
            "request": "launch",
            "module": "pytest",
            "args": ["-m", "small", "-v", "--no-header"],
            "console": "integratedTerminal",
            "justMyCode": false
        },
        {
            "name": "Debug Current Test File",
            "type": "debugpy",
            "request": "launch",
            "module": "pytest",
            "args": ["${file}", "-v"],
            "console": "integratedTerminal",
            "justMyCode": false
        },
        {
            "name": "Debug Failed Tests",
            "type": "debugpy",
            "request": "launch",
            "module": "pytest",
            "args": ["--lf", "-v"],
            "console": "integratedTerminal",
            "justMyCode": false
        }
    ]
}
```

### VS Code Gotchas and Tips

**Test Discovery Not Working**

If tests are not appearing in the Test Explorer:

1. Check the Python interpreter is correctly selected (bottom status bar)
2. Verify pytest-test-categories is installed: `pip list | grep pytest-test-categories`
3. Run **Python: Discover Tests** from the Command Palette
4. Check the **Output** panel (select "Python Test Log") for errors

**Marker Filtering in Test Explorer**

The built-in Test Explorer does not have a UI for marker filtering. Use one of these workarounds:

1. Modify `python.testing.pytestArgs` in settings
2. Use task configurations (as shown above)
3. Run pytest directly in the terminal: `pytest -m small`

**Coverage Visualization**

For coverage visualization, install the **Coverage Gutters** extension and configure:

```json
{
    "coverage-gutters.coverageFileNames": [
        "coverage.xml"
    ]
}
```

Generate coverage with:
```bash
coverage run -m pytest
coverage xml
```

**Working with uv**

If your project uses [uv](https://github.com/astral-sh/uv) for dependency management, configure VS Code to use the uv-managed environment:

1. Run `uv sync` to create the virtual environment
2. Open Command Palette > **Python: Select Interpreter**
3. Choose the interpreter from `.venv/bin/python`

Or configure explicitly in settings:

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python"
}
```

## General Troubleshooting

### Markers Not Recognized

**Symptom:** IDE shows "unknown marker" warnings or tests are not filtered correctly.

**Solution:**
1. Ensure pytest-test-categories is installed in the active environment
2. Add explicit marker definitions to `pyproject.toml`:
   ```toml
   [tool.pytest.ini_options]
   markers = [
       "small: Fast, hermetic unit tests (< 1s)",
       "medium: Integration tests with local services (< 5min)",
       "large: End-to-end tests (< 15min)",
       "xlarge: Extended tests (< 15min)",
   ]
   ```
3. Restart the IDE or refresh test discovery

### Size Labels Not Appearing

**Symptom:** Test IDs do not show `[SMALL]`, `[MEDIUM]`, etc.

**Solution:**
1. Verify the plugin is active by running `pytest --co` (collect only) in the terminal
2. Check that tests have size markers applied
3. Unmarked tests will show a warning but no size label

### Timing Violations in IDE

**Symptom:** Tests fail with `TimingViolationError` when run from IDE but pass from terminal.

**Possible causes:**
1. IDE debugger overhead - debugging adds significant time
2. IDE running tests sequentially instead of in parallel
3. Different environment configuration

**Solutions:**
1. When debugging, temporarily use a larger test size marker
2. Configure parallel execution (`-n auto`) if using pytest-xdist
3. Verify IDE uses the same Python environment as terminal

### Test Distribution Warnings

**Symptom:** Warnings about test distribution appear in IDE output.

**This is expected behavior.** The plugin validates that your test suite follows the recommended distribution (80% small, 15% medium, 5% large/xlarge). These warnings help you maintain a healthy test pyramid.

To suppress distribution warnings during development, set in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
test_categories_distribution_enforcement = "off"
```

## Example Project Configuration

For a complete working example, here is a typical project configuration:

### pyproject.toml

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "it_*.py"]
python_functions = ["test_*", "it_*"]
python_classes = ["Test*", "Describe*"]
addopts = ["-v", "--tb=short"]

markers = [
    "small: Fast, hermetic unit tests (< 1s)",
    "medium: Integration tests with local services (< 5min)",
    "large: End-to-end tests (< 15min)",
    "xlarge: Extended tests (< 15min)",
]

# Plugin configuration
test_categories_enforcement = "warn"
test_categories_distribution_enforcement = "warn"
```

### .vscode/settings.json

```json
{
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"],
    "python.testing.autoTestDiscoverOnSaveEnabled": true,
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python"
}
```

### Sample Test File

```python
import pytest

@pytest.mark.small
def test_unit_function():
    """Small tests complete in under 1 second."""
    assert 1 + 1 == 2

@pytest.mark.medium
def test_with_database(db_connection):
    """Medium tests can access local services."""
    result = db_connection.execute("SELECT 1")
    assert result is not None

@pytest.mark.large
def test_end_to_end(staging_server):
    """Large tests can access external services."""
    response = staging_server.health_check()
    assert response.status_code == 200
```

## Next Steps

- Review the [Configuration Guide](configuration.md) for all available options
- Learn about [Timing Enforcement](user-guide/timing-enforcement.md)
- Explore [Distribution Validation](user-guide/distribution-validation.md)
- Set up [Test Reporting](user-guide/reporting.md)
