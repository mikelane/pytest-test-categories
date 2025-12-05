# Filesystem Isolation Examples

## Prerequisites

To follow these examples, you may want to install optional mocking libraries:

```bash
# For comprehensive filesystem mocking
pip install pyfakefs

# For general mocking (usually already included with pytest)
pip install pytest-mock
```

These libraries are **not required** by pytest-test-categories but are recommended for writing
hermetic tests that mock filesystem operations.

---

This document provides practical examples of tests that violate filesystem isolation and how to fix them.

## Example 1: Writing Report Files

### Violating Test

This test writes a file directly to the project directory, violating small test requirements:

```python
# tests/test_reports.py
from pathlib import Path

import pytest


@pytest.mark.small
def test_generate_report():
    """Generate a report file."""
    report_path = Path("output/report.txt")
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text("Test Report\n==========\nAll tests passed.")

    assert report_path.exists()
    assert "All tests passed" in report_path.read_text()
```

**Error:**

```
HermeticityViolationError: Filesystem access attempted
Attempted create on: /home/user/project/output/
```

### Fixed Test Using pyfakefs

```python
# tests/test_reports.py
import pytest


@pytest.mark.small
def test_generate_report(fs):  # pyfakefs fixture
    """Generate a report file using fake filesystem."""
    # Arrange: Create output directory in fake filesystem
    fs.create_dir("/output")
    report_path = "/output/report.txt"

    # Act: Generate the report (writes to fake filesystem)
    with open(report_path, "w") as f:
        f.write("Test Report\n==========\nAll tests passed.")

    # Assert: Verify the report was created correctly
    with open(report_path) as f:
        content = f.read()
    assert "All tests passed" in content
```

### Fixed Test Using tmp_path (Medium Test)

```python
# tests/test_reports.py
from pathlib import Path

import pytest


@pytest.mark.medium  # Medium tests can access the filesystem
def test_generate_report(tmp_path):
    """Generate a report file using pytest's tmp_path fixture."""
    # Arrange: Create output directory in temp space
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    report_path = output_dir / "report.txt"

    # Act: Generate the report
    report_path.write_text("Test Report\n==========\nAll tests passed.")

    # Assert: Verify the report was created correctly
    assert report_path.exists()
    assert "All tests passed" in report_path.read_text()
```

### Fixed Test Using StringIO

```python
# tests/test_reports.py
from io import StringIO

import pytest


@pytest.mark.small
def test_generate_report_content():
    """Generate report content without filesystem access."""
    # Arrange: Create an in-memory buffer
    buffer = StringIO()

    # Act: Generate the report to the buffer
    generate_report(buffer)

    # Assert: Verify the report content
    content = buffer.getvalue()
    assert "Test Report" in content
    assert "All tests passed" in content
```

## Example 2: Reading Configuration Files

### Violating Test

This test reads a real configuration file:

```python
# tests/test_config.py
from pathlib import Path

import pytest

from myapp.config import load_config


@pytest.mark.small
def test_load_config():
    """Load configuration from file."""
    config = load_config(Path("/etc/myapp/config.yaml"))

    assert config["database"]["host"] == "localhost"
    assert config["database"]["port"] == 5432
```

**Error:**

```
HermeticityViolationError: Filesystem access attempted
Attempted read on: /etc/myapp/config.yaml
```

### Fixed Test Using Mock

```python
# tests/test_config.py
import pytest

from myapp.config import load_config


CONFIG_YAML = """
database:
  host: localhost
  port: 5432
  name: myapp_db
"""


@pytest.mark.small
def test_load_config_parses_yaml(mocker):
    """Load configuration from mocked file."""
    # Arrange: Mock the file open operation
    mocker.patch("builtins.open", mocker.mock_open(read_data=CONFIG_YAML))

    # Act: Load the configuration
    config = load_config("/etc/myapp/config.yaml")

    # Assert: Verify the configuration was parsed correctly
    assert config["database"]["host"] == "localhost"
    assert config["database"]["port"] == 5432
```

### Fixed Test Using tmp_path (Medium Test)

```python
# tests/test_config.py
from pathlib import Path

import pytest

from myapp.config import load_config


CONFIG_YAML = """
database:
  host: localhost
  port: 5432
  name: myapp_db
"""


@pytest.mark.medium  # Medium tests can access the filesystem
def test_load_config_from_file(tmp_path):
    """Load configuration from a real file in temp space."""
    # Arrange: Create config file in temp directory
    config_file = tmp_path / "config.yaml"
    config_file.write_text(CONFIG_YAML)

    # Act: Load the configuration
    config = load_config(config_file)

    # Assert: Verify the configuration
    assert config["database"]["host"] == "localhost"
    assert config["database"]["port"] == 5432
```

### Fixed Test Using Dependency Injection

```python
# src/myapp/config.py
from io import StringIO
from pathlib import Path
from typing import TextIO

import yaml


def load_config(source: Path | TextIO) -> dict:
    """Load configuration from a file path or file-like object.

    Args:
        source: Either a Path to a config file, or a file-like object.

    Returns:
        Configuration dictionary.

    """
    if isinstance(source, Path):
        with open(source) as f:
            return yaml.safe_load(f)
    else:
        return yaml.safe_load(source)
```

```python
# tests/test_config.py
from io import StringIO

import pytest

from myapp.config import load_config


CONFIG_YAML = """
database:
  host: localhost
  port: 5432
"""


@pytest.mark.small
def test_load_config_from_stream():
    """Load configuration from a stream (no filesystem access)."""
    # Arrange: Create config as StringIO
    config_stream = StringIO(CONFIG_YAML)

    # Act: Load from stream
    config = load_config(config_stream)

    # Assert: Verify configuration
    assert config["database"]["host"] == "localhost"
```

## Example 3: File Processing Pipeline

### Violating Test

This test processes files from the project directory:

```python
# tests/test_processor.py
from pathlib import Path

import pytest

from myapp.processor import process_data_files


@pytest.mark.small
def test_process_data_files():
    """Process all data files in a directory."""
    data_dir = Path("data/input")
    output_dir = Path("data/output")

    results = process_data_files(data_dir, output_dir)

    assert len(results) > 0
    assert all(r.success for r in results)
```

**Error:**

```
HermeticityViolationError: Filesystem access attempted
Attempted list on: /home/user/project/data/input/
```

### Fixed Test Using tmp_path (Medium Test)

```python
# tests/test_processor.py
from pathlib import Path

import pytest

from myapp.processor import process_data_files


@pytest.mark.medium  # Medium tests can access the filesystem
def test_process_data_files(tmp_path):
    """Process all data files in a directory."""
    # Arrange: Create test directory structure
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    # Create test data files
    (input_dir / "file1.csv").write_text("id,name\n1,Alice\n2,Bob")
    (input_dir / "file2.csv").write_text("id,name\n3,Charlie")

    # Act: Process the files
    results = process_data_files(input_dir, output_dir)

    # Assert: Verify processing results
    assert len(results) == 2
    assert all(r.success for r in results)
    assert (output_dir / "file1_processed.csv").exists()
    assert (output_dir / "file2_processed.csv").exists()
```

### Fixed Test Using pyfakefs

```python
# tests/test_processor.py
import pytest

from myapp.processor import process_data_files


@pytest.mark.small
def test_process_data_files_with_fake_fs(fs):
    """Process data files using a fake filesystem."""
    # Arrange: Create fake directory structure
    fs.create_dir("/data/input")
    fs.create_dir("/data/output")
    fs.create_file("/data/input/file1.csv", contents="id,name\n1,Alice\n2,Bob")
    fs.create_file("/data/input/file2.csv", contents="id,name\n3,Charlie")

    # Act: Process the files
    results = process_data_files("/data/input", "/data/output")

    # Assert: Verify processing
    assert len(results) == 2
    assert all(r.success for r in results)
```

## Example 4: Log File Testing

### Violating Test

This test checks log file creation:

```python
# tests/test_logging.py
from pathlib import Path

import pytest

from myapp.logging import setup_logging, get_logger


@pytest.mark.small
def test_logging_creates_file():
    """Logging creates a log file."""
    log_dir = Path("logs")
    setup_logging(log_dir)
    logger = get_logger("test")

    logger.info("Test message")

    log_file = log_dir / "app.log"
    assert log_file.exists()
    assert "Test message" in log_file.read_text()
```

**Error:**

```
HermeticityViolationError: Filesystem access attempted
Attempted create on: /home/user/project/logs/
```

### Fixed Test Using tmp_path (Medium Test)

```python
# tests/test_logging.py
from pathlib import Path

import pytest

from myapp.logging import setup_logging, get_logger


@pytest.mark.medium  # Medium tests can access the filesystem
def test_logging_creates_file(tmp_path):
    """Logging creates a log file in temp directory."""
    # Arrange: Set up logging in temp directory
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    setup_logging(log_dir)
    logger = get_logger("test")

    # Act: Write a log message
    logger.info("Test message")

    # Assert: Verify the log file
    log_file = log_dir / "app.log"
    assert log_file.exists()
    assert "Test message" in log_file.read_text()
```

### Fixed Test Using StringIO Handler

```python
# tests/test_logging.py
import logging
from io import StringIO

import pytest

from myapp.logging import get_logger


@pytest.mark.small
def test_logging_output():
    """Logging outputs correct messages (no file access)."""
    # Arrange: Create a StringIO handler
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(logging.Formatter("%(message)s"))

    logger = get_logger("test")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Act: Write a log message
    logger.info("Test message")

    # Assert: Verify the log output
    log_content = log_stream.getvalue()
    assert "Test message" in log_content
```

## Example 5: Database Fixture Files

### Violating Test

This test loads SQL fixtures from the repository:

```python
# tests/test_database.py
from pathlib import Path

import pytest

from myapp.database import execute_sql


@pytest.mark.small
def test_create_tables(mocker):
    """Create database tables from SQL file."""
    mock_conn = mocker.Mock()
    sql_file = Path("tests/fixtures/schema.sql")

    execute_sql(mock_conn, sql_file.read_text())

    mock_conn.execute.assert_called()
```

**Error:**

```
HermeticityViolationError: Filesystem access attempted
Attempted read on: /home/user/project/tests/fixtures/schema.sql
```

### Fixed Test With Embedded SQL

```python
# tests/test_database.py
import pytest

from myapp.database import execute_sql


SCHEMA_SQL = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    total DECIMAL(10, 2)
);
"""


@pytest.mark.small
def test_create_tables(mocker):
    """Create database tables from SQL."""
    # Arrange: Create mock connection
    mock_conn = mocker.Mock()

    # Act: Execute the schema SQL
    execute_sql(mock_conn, SCHEMA_SQL)

    # Assert: Verify SQL was executed
    assert mock_conn.execute.called
    # Verify CREATE TABLE was in the executed SQL
    executed_sql = mock_conn.execute.call_args[0][0]
    assert "CREATE TABLE users" in executed_sql
```

## Example 6: Using Medium Test Size

Sometimes filesystem access is genuinely required. In these cases, use a medium test:

### Legitimate Filesystem Test

```python
# tests/integration/test_file_io.py
from pathlib import Path

import pytest

from myapp.file_io import safe_write, atomic_replace


@pytest.mark.medium  # Medium tests can access the filesystem
def test_atomic_file_replacement(tmp_path):
    """Test atomic file replacement with real filesystem."""
    # Arrange: Create original file
    target = tmp_path / "config.json"
    target.write_text('{"version": 1}')

    # Act: Atomically replace the file
    atomic_replace(target, '{"version": 2}')

    # Assert: File was updated atomically
    assert target.read_text() == '{"version": 2}'


@pytest.mark.medium
def test_safe_write_creates_backup(tmp_path):
    """Test safe write creates backup file."""
    # Arrange: Create original file
    target = tmp_path / "data.txt"
    target.write_text("original content")

    # Act: Safe write with backup
    safe_write(target, "new content", backup=True)

    # Assert: Backup was created
    backup = tmp_path / "data.txt.bak"
    assert backup.exists()
    assert backup.read_text() == "original content"
    assert target.read_text() == "new content"
```

## Configuration Examples

### pyproject.toml

```toml
[tool.pytest.ini_options]
# Markers for test sizes
markers = [
    "small: Fast, hermetic unit tests (< 1s)",
    "medium: Integration tests with local services (< 5min)",
    "large: End-to-end tests (< 15min)",
    "xlarge: Extended tests (< 15min)",
]

# Enable strict filesystem and network isolation
test_categories_enforcement = "strict"
```

### pytest.ini

```ini
[pytest]
markers =
    small: Fast, hermetic unit tests (< 1s)
    medium: Integration tests with local services (< 5min)
    large: End-to-end tests (< 15min)
    xlarge: Extended tests (< 15min)

test_categories_enforcement = strict
```

### CI Pipeline Example

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          pip install uv
          uv sync --all-groups

      - name: Run tests with filesystem isolation
        run: |
          uv run pytest --test-categories-enforcement=strict
```

### Gradual Migration Example

```yaml
# .github/workflows/test.yml
jobs:
  # Warn about violations but don't fail
  test-with-warnings:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests (warn mode)
        run: |
          uv run pytest --test-categories-enforcement=warn 2>&1 | tee test-output.txt
          grep "Filesystem access violation" test-output.txt > violations.txt || true
          if [ -s violations.txt ]; then
            echo "::warning::Filesystem violations detected (see violations.txt)"
            cat violations.txt
          fi

  # Strict enforcement on main branch
  test-strict:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Run tests (strict mode)
        run: |
          uv run pytest --test-categories-enforcement=strict
```

## Related Documentation

- [User Guide: Filesystem Isolation](../user-guide/filesystem-isolation.md)
- [Troubleshooting: Filesystem Violations](../troubleshooting/filesystem-violations.md)
- [ADR-002: Filesystem Isolation](../architecture/adr-002-filesystem-isolation.md)
