# Filesystem Isolation for Hermetic Tests

> **PLANNED FEATURE - Coming in v0.5.0**
>
> This documentation describes filesystem isolation features that are **currently being implemented**.
> The design is documented in [ADR-002](../architecture/adr-002-filesystem-isolation.md).
> Implementation will follow in Issues #92 (port interface), #93 (adapters), and #95 (pytest integration).
>
> Track progress: [Epic #66](https://github.com/mikelane/pytest-test-categories/issues/66)

## What is Filesystem Isolation?

Filesystem isolation is a test enforcement mechanism that prevents small tests from accessing the filesystem during execution. This ensures tests are **hermetic** - running entirely in memory with no external dependencies.

When enabled, the pytest-test-categories plugin intercepts filesystem operations and either blocks them or warns about them, depending on your configuration.

## Why Filesystem Isolation Matters

Tests that access the filesystem introduce several problems:

### Side Effects

Filesystem-dependent tests create unpredictable side effects:

- Files created by one test may persist and affect subsequent tests
- Tests may overwrite or delete files needed by other tests
- Parallel test execution leads to race conditions on shared files
- CI environments may have different filesystem layouts than local development

### State Leakage

External filesystem state makes tests non-deterministic:

- Tests depend on specific files existing at specific paths
- Configuration files vary between environments
- Data files may change between test runs
- Paths are often platform-specific (Windows vs. Unix)

### Slow Tests

Disk I/O adds latency that compounds across your test suite:

- File operations are orders of magnitude slower than memory operations
- SSDs are fast but still 1000x slower than RAM
- Network filesystems (NFS, CIFS) add significant latency
- Disk contention increases as tests run in parallel

### Non-Hermeticity

Tests that read or write external files are not self-contained:

- Cannot run reliably in isolated CI containers
- May fail when paths differ between developers
- Difficult to parallelize safely
- Hard to reproduce failures

## Google's Test Size Definitions

The filesystem isolation feature implements Google's test size definitions from "Software Engineering at Google":

| Test Size | Filesystem Access | Rationale |
|-----------|------------------|-----------|
| Small     | **Blocked** (except allowed paths) | Must be hermetic, run in memory only |
| Medium    | Allowed          | May use local filesystem for integration tests |
| Large     | Allowed          | Integration tests may access real filesystems |
| XLarge    | Allowed          | End-to-end tests may access real filesystems |

### Small Tests

Small tests are the foundation of a healthy test suite. They must be:

- **Fast**: Complete in under 1 second
- **Hermetic**: No external dependencies
- **Deterministic**: Same input always produces same output
- **Parallelizable**: Safe to run concurrently with other tests

Filesystem isolation enforces hermeticity by blocking filesystem access in small tests, except for explicitly allowed paths.

### Medium, Large, and XLarge Tests

Medium, large, and XLarge tests may access the filesystem freely, enabling:

- File-based integration tests
- Configuration file parsing tests
- Log file generation tests
- Data import/export tests

## How It Works

The plugin intercepts filesystem operations by patching Python's built-in functions and modules:

### Patched Entry Points

The following filesystem entry points are intercepted:

- `builtins.open` - Primary file open function
- `io.open` - Alias for built-in open
- `pathlib.Path.open` - pathlib file access
- `pathlib.Path.read_text`, `Path.read_bytes` - Direct read methods
- `pathlib.Path.write_text`, `Path.write_bytes` - Direct write methods
- `os.open`, `os.mkdir`, `os.remove`, etc. - Low-level operations

### Operation Categories

Filesystem operations are categorized as:

| Operation | Description | Examples |
|-----------|-------------|----------|
| READ | Read file contents | `open()` for reading, `Path.read_text()` |
| WRITE | Write file contents | `open()` for writing, `Path.write_text()` |
| CREATE | Create files/directories | `mkdir()`, `touch()`, `open('x')` |
| DELETE | Remove files/directories | `os.remove()`, `Path.unlink()`, `shutil.rmtree()` |
| MODIFY | Change file attributes | `chmod()`, `chown()`, `rename()` |
| STAT | Read file metadata | `stat()`, `exists()`, `is_file()` |
| LIST | List directory contents | `listdir()`, `scandir()`, `iterdir()` |

All operations are blocked on non-allowed paths for small tests, including STAT operations. This ensures tests do not depend on external filesystem state.

## Default Allowed Paths

Certain paths are automatically allowed, even for small tests:

### System Temp Directory

The system temporary directory (`tempfile.gettempdir()`) and all its subdirectories are allowed. This includes:

- `/tmp` on Linux/macOS
- `C:\Users\<user>\AppData\Local\Temp` on Windows

### pytest's basetemp Directory

The pytest `tmp_path` fixture creates directories under pytest's basetemp. These are automatically allowed:

- Default location: `{tempdir}/pytest-of-{username}/`
- Custom location: Set via `--basetemp` CLI option

### pytest Fixture Paths

When your test uses `tmp_path` or `tmp_path_factory` fixtures, those paths are automatically added to the allowed list for that specific test.

```python
@pytest.mark.small
def test_with_temp_file(tmp_path):
    # tmp_path is automatically allowed
    test_file = tmp_path / "data.txt"
    test_file.write_text("hello")  # OK - under tmp_path
    assert test_file.read_text() == "hello"
```

## Enabling Filesystem Isolation

Filesystem isolation is controlled by the `test_categories_enforcement` configuration option, the same option used for network isolation.

### Configuration via pyproject.toml

```toml
[tool.pytest.ini_options]
# Enable filesystem and network isolation enforcement
test_categories_enforcement = "strict"
```

### Configuration via pytest.ini

```ini
[pytest]
test_categories_enforcement = strict
```

### Configuration via Command Line

```bash
pytest --test-categories-enforcement=strict
```

## Enforcement Modes

The plugin supports three enforcement modes:

### STRICT Mode

```toml
test_categories_enforcement = "strict"
```

In strict mode, filesystem violations immediately fail the test with a detailed error message:

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
  1. Use pytest's tmp_path fixture for temporary files
  2. Mock file operations using pytest-mock (mocker fixture) or pyfakefs
  3. Use io.StringIO or io.BytesIO for in-memory file-like objects
  4. Embed test data as Python constants or use importlib.resources
  5. Change test category to @pytest.mark.medium (if filesystem access is required)

Documentation: See docs/architecture/adr-002-filesystem-isolation.md
============================================================
```

Use strict mode in CI pipelines to catch violations before merge.

### WARN Mode

```toml
test_categories_enforcement = "warn"
```

In warn mode, filesystem violations emit a warning but allow the test to continue:

```
PytestWarning: Filesystem access violation in test_save_report:
attempted write on /home/user/project/output/report.txt
```

Use warn mode during migration to identify violations without breaking the build.

### OFF Mode

```toml
test_categories_enforcement = "off"
```

In off mode, filesystem isolation is disabled entirely. Use this for:

- Legacy test suites not yet ready for enforcement
- Specific test runs that require filesystem access
- Debugging filesystem-related test issues

## Adding Custom Allowed Paths

You can configure additional paths that are always allowed for small tests.

### Configuration via pyproject.toml

```toml
[tool.pytest.ini_options]
test_categories_enforcement = "strict"

# Additional allowed paths for filesystem access
test_categories_allowed_paths = [
    "tests/fixtures/",
    "src/mypackage/data/",
]
```

### Configuration via Command Line

```bash
pytest --test-categories-allowed-paths=tests/fixtures/,src/mypackage/data/
```

Paths can be:
- Absolute paths: `/home/user/project/fixtures/`
- Relative paths: `tests/fixtures/` (resolved from project root)
- User-relative paths: `~/project/data/` (expanded with `~`)

## Understanding Error Messages

When a filesystem violation occurs, the error message provides:

1. **Test identification**: The full pytest node ID
2. **Category**: The test size (SMALL, MEDIUM, etc.)
3. **Operation**: The type of operation attempted (read, write, etc.)
4. **Path**: The path that was accessed
5. **Remediation options**: Specific suggestions for fixing the violation

### Example Error Analysis

```
Attempted write on: /home/user/project/output/report.txt
```

This tells you:
- The test tried to **write** a file (not just read)
- The path is **outside** all allowed directories
- You need to either mock the write or use `tmp_path`

## Common Remediation Strategies

### 1. Use tmp_path Fixture

The simplest fix for tests that need temporary files:

```python
@pytest.mark.small
def test_save_report(tmp_path):
    output_file = tmp_path / "report.txt"
    save_report(output_file)
    assert output_file.exists()
```

### 2. Use io.StringIO or io.BytesIO

For tests that need file-like objects but not actual files:

```python
from io import StringIO

@pytest.mark.small
def test_csv_writer():
    buffer = StringIO()
    write_csv(buffer, data)
    assert "header1,header2" in buffer.getvalue()
```

### 3. Mock File Operations

Use pytest-mock to intercept file operations:

```python
@pytest.mark.small
def test_config_loader(mocker):
    mock_open = mocker.patch("builtins.open", mocker.mock_open(read_data="key=value"))
    config = load_config("/etc/myapp/config.ini")
    assert config["key"] == "value"
```

### 4. Use pyfakefs

For comprehensive filesystem mocking:

```python
@pytest.mark.small
def test_with_fake_filesystem(fs):  # pyfakefs fixture
    fs.create_file("/etc/myapp/config.ini", contents="key=value")
    config = load_config("/etc/myapp/config.ini")
    assert config["key"] == "value"
```

### 5. Embed Test Data

For read-only test data, embed it in your test code:

```python
TEST_CONFIG = """
[database]
host = localhost
port = 5432
"""

@pytest.mark.small
def test_config_parser():
    config = parse_config(StringIO(TEST_CONFIG))
    assert config["database"]["host"] == "localhost"
```

### 6. Use importlib.resources

For package data files:

```python
from importlib import resources

@pytest.mark.small
def test_load_schema():
    schema_text = resources.read_text("mypackage.schemas", "user.json")
    schema = json.loads(schema_text)
    assert "properties" in schema
```

### 7. Change Test Size

If the test legitimately requires filesystem access, change its category:

```python
@pytest.mark.medium  # Medium tests can access filesystem
def test_large_file_processing():
    with open("/data/large_dataset.csv") as f:
        process_file(f)
```

## Best Practices

### 1. Start with WARN Mode

When first enabling filesystem isolation, use warn mode to identify all violations:

```bash
pytest --test-categories-enforcement=warn 2>&1 | grep "Filesystem access violation"
```

### 2. Fix Violations Systematically

Address violations in order of test frequency:

1. Fix small tests first (they run most often)
2. Use tmp_path for tests that need real files
3. Use mocking for tests that don't need real filesystem
4. Change test size only when filesystem access is essential

### 3. Use Dependency Injection

Design code to accept file paths or file-like objects as parameters:

```python
# Production code
def save_report(data: dict, output: Path | TextIO) -> None:
    if isinstance(output, Path):
        output.write_text(json.dumps(data))
    else:
        output.write(json.dumps(data))

# Test code - small test with mock
@pytest.mark.small
def test_save_report_to_stream():
    buffer = StringIO()
    save_report({"key": "value"}, buffer)
    assert '"key"' in buffer.getvalue()

# Test code - medium test with real file
@pytest.mark.medium
def test_save_report_to_file(tmp_path):
    output_file = tmp_path / "report.json"
    save_report({"key": "value"}, output_file)
    assert output_file.exists()
```

### 4. Consider Test Size Carefully

If a test genuinely requires filesystem access, consider whether it belongs in a different size category:

- **Small**: Pure functions, in-memory operations, mocked I/O
- **Medium**: File operations with tmp_path, config file parsing
- **Large**: Integration with real filesystem paths

## Related Documentation

- [Architecture Decision Record: Filesystem Isolation](../architecture/adr-002-filesystem-isolation.md)
- [Troubleshooting Filesystem Violations](../troubleshooting/filesystem-violations.md)
- [Filesystem Isolation Examples](../examples/filesystem-isolation.md)
- [Configuration Reference](../configuration.md)
