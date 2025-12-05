# Troubleshooting Filesystem Violations

This guide helps you identify and fix filesystem access violations in your test suite.

## Understanding the Error Message

When a filesystem violation occurs in strict mode, you see an error like this:

```
============================================================
HermeticityViolationError
============================================================
Test: tests/test_reports.py::test_save_report
Category: SMALL
Violation: Filesystem access attempted

Details:
  Attempted write on: /home/user/project/output/report.txt

Small tests have restricted resource access. Options:
  - Use pyfakefs for comprehensive filesystem mocking (pip install pyfakefs)
  - Use io.StringIO or io.BytesIO for in-memory file-like objects
  - Mock file operations using pytest-mock (mocker.patch("builtins.open", ...))
  - Embed test data as Python constants or use importlib.resources
  - Change test category to @pytest.mark.medium (if filesystem access is required)

Documentation: See docs/architecture/adr-002-filesystem-isolation.md
============================================================
```

The error tells you:

- **Test**: The full pytest node ID of the failing test
- **Category**: The test size (SMALL, MEDIUM, etc.)
- **Details**: The operation type and path that the test attempted to access
- **Options**: Suggested fixes for the violation

## Common Violation Scenarios

### 1. Writing Output Files

**Symptom**: Write operation on a path outside allowed directories.

```
Attempted write on: /home/user/project/output/report.txt
```

**Cause**: Test code writes files directly to the project directory:

```python
from pathlib import Path

@pytest.mark.small
def test_generate_report():
    output = Path("output/report.txt")
    output.write_text("Report content")
    assert output.exists()
```

**Fix Option 1**: Use `pyfakefs` for in-memory filesystem:

```python
@pytest.mark.small
def test_generate_report(fs):  # pyfakefs fixture
    fs.create_dir("/output")
    output = "/output/report.txt"
    with open(output, "w") as f:
        f.write("Report content")
    with open(output) as f:
        assert f.read() == "Report content"
```

**Fix Option 2**: Use `@pytest.mark.medium` with `tmp_path`:

```python
from pathlib import Path

@pytest.mark.medium  # Medium tests can access filesystem
def test_generate_report(tmp_path):
    output = tmp_path / "report.txt"
    output.write_text("Report content")
    assert output.exists()
    assert output.read_text() == "Report content"
```

### 2. Reading Configuration Files

**Symptom**: Read operation on a configuration file path.

```
Attempted read on: /etc/myapp/config.ini
```

**Cause**: Test reads a real configuration file:

```python
@pytest.mark.small
def test_load_config():
    config = load_config("/etc/myapp/config.ini")
    assert config["database"]["host"] == "localhost"
```

**Fix**: Use a mock or StringIO:

```python
from io import StringIO

CONFIG_CONTENT = """
[database]
host = localhost
port = 5432
"""

@pytest.mark.small
def test_load_config():
    config = load_config_from_stream(StringIO(CONFIG_CONTENT))
    assert config["database"]["host"] == "localhost"
```

Or use pytest-mock:

```python
@pytest.mark.small
def test_load_config(mocker):
    config_content = "[database]\nhost = localhost\nport = 5432"
    mocker.patch("builtins.open", mocker.mock_open(read_data=config_content))

    config = load_config("/etc/myapp/config.ini")

    assert config["database"]["host"] == "localhost"
```

### 3. Creating Directories

**Symptom**: Create operation on a directory path.

```
Attempted create on: /home/user/project/logs/
```

**Cause**: Test creates directories in the project:

```python
from pathlib import Path

@pytest.mark.small
def test_setup_logging():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    setup_logging(log_dir)
```

**Fix Option 1**: Use `pyfakefs`:

```python
@pytest.mark.small
def test_setup_logging(fs):  # pyfakefs fixture
    fs.create_dir("/logs")
    setup_logging("/logs")
    # Verify in fake filesystem
```

**Fix Option 2**: Use `@pytest.mark.medium` with `tmp_path`:

```python
from pathlib import Path

@pytest.mark.medium  # Medium tests can access filesystem
def test_setup_logging(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    setup_logging(log_dir)
    assert (log_dir / "app.log").exists()
```

### 4. Checking File Existence

**Symptom**: Stat operation blocked.

```
Attempted stat on: /home/user/project/data/users.json
```

**Cause**: Test checks if a file exists (filesystem access blocked for small tests):

```python
from pathlib import Path

@pytest.mark.small
def test_data_file_exists():
    data_file = Path("data/users.json")
    assert data_file.exists()
```

**Fix**: If the test is verifying behavior, mock the existence check:

```python
@pytest.mark.small
def test_handles_missing_file(mocker):
    mocker.patch("pathlib.Path.exists", return_value=False)

    result = load_data_with_fallback("data/users.json")

    assert result == []  # Falls back to empty list
```

Or use `@pytest.mark.medium` with `tmp_path`:

```python
@pytest.mark.medium  # Medium tests can access filesystem
def test_data_file_loaded(tmp_path):
    data_file = tmp_path / "users.json"
    data_file.write_text('[{"name": "Alice"}]')

    result = load_data(data_file)

    assert result[0]["name"] == "Alice"
```

### 5. Reading Test Fixtures

**Symptom**: Read operation on fixture files.

```
Attempted read on: /home/user/project/tests/fixtures/sample.xml
```

**Cause**: Test reads fixture files from the repository:

```python
from pathlib import Path

@pytest.mark.small
def test_parse_xml():
    fixture = Path("tests/fixtures/sample.xml")
    result = parse_xml(fixture.read_text())
    assert result.root.tag == "document"
```

**Fix Option 1**: Embed fixture data in the test:

```python
SAMPLE_XML = """
<?xml version="1.0"?>
<document>
  <title>Test Document</title>
</document>
"""

@pytest.mark.small
def test_parse_xml():
    result = parse_xml(SAMPLE_XML)
    assert result.root.tag == "document"
```

**Fix Option 2**: Use importlib.resources for package fixtures:

```python
from importlib import resources

@pytest.mark.small
def test_parse_xml():
    sample_xml = resources.read_text("tests.fixtures", "sample.xml")
    result = parse_xml(sample_xml)
    assert result.root.tag == "document"
```

### 6. Deleting Files

**Symptom**: Delete operation on a non-allowed path.

```
Attempted delete on: /home/user/project/temp/cache.db
```

**Cause**: Test cleans up files outside allowed directories:

```python
from pathlib import Path

@pytest.mark.small
def test_clear_cache():
    cache_file = Path("temp/cache.db")
    cache_file.unlink(missing_ok=True)
    assert not cache_file.exists()
```

**Fix Option 1**: Use `pyfakefs`:

```python
@pytest.mark.small
def test_clear_cache(fs):  # pyfakefs fixture
    fs.create_file("/tmp/cache.db", contents=b"cached data")

    clear_cache("/tmp/cache.db")

    import os
    assert not os.path.exists("/tmp/cache.db")
```

**Fix Option 2**: Use `@pytest.mark.medium` with `tmp_path`:

```python
@pytest.mark.medium  # Medium tests can access filesystem
def test_clear_cache(tmp_path):
    cache_file = tmp_path / "cache.db"
    cache_file.write_bytes(b"cached data")

    clear_cache(cache_file)

    assert not cache_file.exists()
```

### 7. Listing Directory Contents

**Symptom**: List operation on a non-allowed path.

```
Attempted list on: /home/user/project/plugins/
```

**Cause**: Test lists files in a project directory:

```python
from pathlib import Path

@pytest.mark.small
def test_discover_plugins():
    plugin_dir = Path("plugins")
    plugins = list(plugin_dir.glob("*.py"))
    assert len(plugins) > 0
```

**Fix Option 1**: Use `pyfakefs`:

```python
@pytest.mark.small
def test_discover_plugins(fs):  # pyfakefs fixture
    fs.create_dir("/plugins")
    fs.create_file("/plugins/plugin_a.py", contents="# Plugin A")
    fs.create_file("/plugins/plugin_b.py", contents="# Plugin B")

    plugins = discover_plugins("/plugins")

    assert len(plugins) == 2
```

**Fix Option 2**: Use `@pytest.mark.medium` with `tmp_path`:

```python
@pytest.mark.medium  # Medium tests can access filesystem
def test_discover_plugins(tmp_path):
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()
    (plugin_dir / "plugin_a.py").write_text("# Plugin A")
    (plugin_dir / "plugin_b.py").write_text("# Plugin B")

    plugins = discover_plugins(plugin_dir)

    assert len(plugins) == 2
```

## Identifying Filesystem-Calling Code

### Step 1: Run Tests in Warn Mode

First, identify all violations without failing tests:

```bash
pytest --test-categories-enforcement=warn 2>&1 | grep -A3 "Filesystem access violation"
```

### Step 2: Add Debugging Output

If the source is unclear, add filesystem debugging:

```python
import builtins

# Temporarily patch to see call stack
original_open = builtins.open

def debug_open(file, *args, **kwargs):
    import traceback
    print(f"File open attempt: {file}")
    traceback.print_stack()
    return original_open(file, *args, **kwargs)

builtins.open = debug_open
```

### Step 3: Use pytest Verbose Mode

Run the specific test with verbose output:

```bash
pytest tests/test_reports.py::test_save_report -vvs
```

### Step 4: Check Fixture Dependencies

Filesystem access often happens in fixtures:

```python
@pytest.fixture
def config():
    # This fixture reads a real file!
    with open("config.yaml") as f:
        return yaml.safe_load(f)
```

Review all fixtures used by the failing test.

### Step 5: Check Module-Level Code

Filesystem access may happen at import time:

```python
# src/myapp/settings.py
from pathlib import Path

# This runs when the module is imported!
CONFIG_PATH = Path("/etc/myapp/config.ini")
if CONFIG_PATH.exists():  # <-- Filesystem access during import
    DEFAULT_CONFIG = CONFIG_PATH.read_text()
```

Consider deferring such access or using lazy initialization.

## Migration Guide

### Phase 1: Assessment

1. Enable warn mode in CI:

   ```toml
   [tool.pytest.ini_options]
   test_categories_enforcement = "warn"
   ```

2. Collect all warnings from a full test run
3. Categorize violations by type (read, write, fixture, etc.)
4. Estimate effort to fix each category

### Phase 2: Quick Wins

1. Use `pyfakefs` for tests that need filesystem semantics
2. Use `io.StringIO`/`io.BytesIO` for file-like objects
3. Convert string literals to embedded Python constants
4. Change tests that genuinely need filesystem to `@pytest.mark.medium`

### Phase 3: Refactoring

1. Introduce dependency injection for file operations
2. Create abstraction layers for filesystem access
3. Use `pyfakefs` for comprehensive filesystem mocking
4. Move test data into embedded constants or package resources

### Phase 4: Enforcement

1. Switch to strict mode in CI:

   ```toml
   [tool.pytest.ini_options]
   test_categories_enforcement = "strict"
   ```

2. Add pre-commit hook to catch violations locally
3. Document filesystem mocking patterns for the team (pyfakefs, io.StringIO)
4. Update test templates to use pyfakefs or io.StringIO by default

## Debugging Access Patterns

### Using strace/dtruss (Linux/macOS)

For deep debugging, trace system calls:

```bash
# Linux
strace -e openat,stat,unlink -f python -m pytest tests/test_reports.py::test_save_report

# macOS
sudo dtruss -f -t open python -m pytest tests/test_reports.py::test_save_report
```

### Using Python's Audit Hooks

Python 3.8+ supports audit hooks for monitoring:

```python
import sys

def audit_hook(event, args):
    if event.startswith("open"):
        print(f"Audit: {event} {args}")

sys.addaudithook(audit_hook)
```

### Using Coverage with Branch Tracking

Run coverage to see which code paths access files:

```bash
coverage run --branch -m pytest tests/test_reports.py::test_save_report
coverage report --show-missing
```

## Temporary Workarounds

### Recategorize the Test

If a test genuinely requires filesystem access, it's not a small test - recategorize it:

```python
@pytest.mark.medium  # Recategorized: requires filesystem access
def test_file_integration():
    """This test needs filesystem access, so it's a medium test."""
    ...
```

The test size defines the constraints, not the other way around.

### Skip in CI Only

For tests that work locally but fail in CI due to filesystem restrictions:

```python
import os

@pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="Filesystem access blocked in CI"
)
@pytest.mark.small
def test_requires_filesystem():
    ...
```

This is a temporary measure - fix the underlying issue.

### Change Test Size Temporarily

As a last resort, change the test size:

```python
@pytest.mark.medium  # TODO: Refactor to small test (issue #123)
def test_config_loading():
    """Currently reads real config file. Should use mock."""
    ...
```

Document the technical debt and create a tracking issue.

## Getting Help

If you encounter a violation you cannot resolve:

1. Check the [examples documentation](../examples/filesystem-isolation.md)
2. Review the [ADR for filesystem isolation](../architecture/adr-002-filesystem-isolation.md)
3. Open a [GitHub Discussion](https://github.com/mikelane/pytest-test-categories/discussions) with:
   - The full error message
   - The test code (sanitized if needed)
   - What you have tried

## Related Documentation

- [User Guide: Filesystem Isolation](../user-guide/filesystem-isolation.md)
- [Examples: Filesystem Isolation](../examples/filesystem-isolation.md)
- [ADR-002: Filesystem Isolation](../architecture/adr-002-filesystem-isolation.md)
