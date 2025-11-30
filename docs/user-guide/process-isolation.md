# Process Isolation for Hermetic Tests

Process isolation is a test enforcement mechanism that prevents small tests from spawning subprocesses during execution. This ensures tests are **hermetic** and run in a **single process** with no external dependencies.

When enabled, the pytest-test-categories plugin intercepts subprocess spawning and either blocks it or warns about it, depending on your configuration.

## Why Process Isolation Matters

Tests that spawn subprocesses introduce several problems:

### Non-Determinism

External processes have their own state and behavior:

- Process startup times vary across machines
- Environment variables may differ between systems
- Child process behavior is harder to control and predict
- Exit codes and output can vary based on system state

### I/O Overhead

Process creation involves significant system overhead:

- Fork/exec system calls are expensive
- Memory pages must be copied or marked copy-on-write
- File descriptors are duplicated
- Process scheduling adds latency

### Resource Leakage

Spawned processes may outlive tests if not properly managed:

- Zombie processes accumulate if not waited on
- Child processes may continue running after test failure
- Open file handles and network connections persist
- Memory is not reclaimed until all children exit

### Environment Coupling

Subprocesses inherit environment state:

- Environment variables affect behavior
- Working directory matters for relative paths
- PATH and other system settings vary
- Shell differences (bash vs sh vs zsh) cause inconsistencies

## Test Size Restrictions

Process isolation follows Google's test size definitions from "Software Engineering at Google":

| Test Size | Subprocess Spawning | Rationale |
|-----------|---------------------|-----------|
| Small     | **Blocked**         | Must be hermetic, single-process |
| Medium    | Allowed             | May spawn processes for integration |
| Large     | Allowed             | May run external commands |
| XLarge    | Allowed             | May orchestrate multiple processes |

### Small Tests

Small tests run in a single process:

- **Fast**: No process creation overhead
- **Hermetic**: No dependency on external executables
- **Deterministic**: No subprocess behavior variation
- **Parallelizable**: Safe to run concurrently without process conflicts

Process isolation enforces the single-process constraint by blocking subprocess spawning in small tests.

### Medium, Large, and XLarge Tests

These tests may spawn subprocesses freely, enabling:

- CLI testing with real command execution
- Integration tests that start local services
- End-to-end tests with multiple processes
- Performance tests that measure real execution

## How It Works

The plugin intercepts subprocess spawning by patching Python's subprocess and os modules:

### Patched Entry Points

The following process spawning entry points are intercepted:

**subprocess module:**
- `subprocess.Popen` - Base class for all subprocess operations
- `subprocess.run` - High-level convenience function
- `subprocess.call` - Run command, return exit code
- `subprocess.check_call` - Run command, raise on non-zero exit
- `subprocess.check_output` - Run command, return stdout

**os module:**
- `os.system` - Run command in shell
- `os.popen` - Open pipe to/from command

**multiprocessing module:**
- `multiprocessing.Process` - Spawn new Python interpreter process

### Spawn Interception

When a test attempts to spawn a subprocess:

1. The blocker intercepts the spawn call
2. It extracts the command and arguments
3. It checks if spawning is allowed based on test size
4. For violations, it either raises an exception (STRICT) or warns (WARN)

## Enabling Process Isolation

Process isolation is controlled by the `test_categories_enforcement` configuration option.

### Configuration via pyproject.toml

```toml
[tool.pytest.ini_options]
# Enable process isolation enforcement
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

In strict mode, subprocess violations immediately fail the test with a detailed error message:

```
[TC003] Subprocess Spawn Violation
Test: tests/test_cli.py::test_run_command
Category: SMALL

What happened:
  Attempted subprocess.run: python script.py --verbose

How to fix:
  1. Mock subprocess.run using pytest-mock (mocker.patch)
  2. Use dependency injection to provide a fake command executor
  3. Test the logic that prepares subprocess arguments, not the spawn itself
  4. Change test category to @pytest.mark.medium (if subprocess is required)

Documentation: https://pytest-test-categories.readthedocs.io/errors/TC003
```

Use strict mode in CI pipelines to catch violations before merge.

### WARN Mode

```toml
test_categories_enforcement = "warn"
```

In warn mode, subprocess violations emit a warning but allow the test to continue:

```
PytestWarning: Subprocess spawn violation in test_run_command:
attempted subprocess.run: python script.py --verbose
```

Use warn mode during migration to identify violations without breaking the build.

### OFF Mode

```toml
test_categories_enforcement = "off"
```

In off mode, process isolation is disabled entirely.

## Per-Test Overrides

Individual tests can override the global enforcement using markers:

### Allow Subprocess Spawning

```python
import pytest

@pytest.mark.small
@pytest.mark.allow_subprocess
def test_special_case():
    """This small test is allowed to spawn subprocesses."""
    import subprocess
    result = subprocess.run(["echo", "hello"], capture_output=True)
    assert result.returncode == 0
```

Use sparingly and document why the override is necessary.

## Common Remediation Strategies

### 1. Mock subprocess.run

The most common pattern for CLI testing:

```python
import pytest

@pytest.mark.small
def test_git_status(mocker):
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = b"On branch main\nnothing to commit"

    from myapp.git import get_status
    status = get_status()

    assert "main" in status
    mock_run.assert_called_once_with(
        ["git", "status"],
        capture_output=True,
        check=False,
    )
```

### 2. Test Command Building Logic

Instead of testing subprocess execution, test the logic that builds commands:

```python
import pytest

# Production code
def build_ffmpeg_command(input_path: str, output_path: str, quality: int) -> list[str]:
    return [
        "ffmpeg",
        "-i", input_path,
        "-q:v", str(quality),
        output_path,
    ]

# Test the command building, not the execution
@pytest.mark.small
def test_build_ffmpeg_command():
    cmd = build_ffmpeg_command("input.mp4", "output.mp4", quality=2)

    assert cmd[0] == "ffmpeg"
    assert "-i" in cmd
    assert "input.mp4" in cmd
    assert "-q:v" in cmd
    assert "2" in cmd
```

### 3. Use Dependency Injection

Design code to accept a command executor:

```python
from typing import Protocol
import subprocess
import pytest

# Define interface
class CommandExecutor(Protocol):
    def run(self, args: list[str]) -> subprocess.CompletedProcess: ...

# Production implementation
class RealExecutor:
    def run(self, args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(args, capture_output=True, check=True)

# Test implementation
class FakeExecutor:
    def __init__(self, outputs: dict[str, str]):
        self.outputs = outputs
        self.calls: list[list[str]] = []

    def run(self, args: list[str]) -> subprocess.CompletedProcess:
        self.calls.append(args)
        key = " ".join(args)
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=self.outputs.get(key, b"").encode(),
        )

# Production code using dependency injection
def deploy(executor: CommandExecutor) -> str:
    result = executor.run(["kubectl", "apply", "-f", "deployment.yaml"])
    return result.stdout.decode()

# Small test with fake executor
@pytest.mark.small
def test_deploy():
    executor = FakeExecutor({"kubectl apply -f deployment.yaml": "deployed"})
    result = deploy(executor)
    assert "deployed" in result
```

### 4. Use pytest's pytester Fixture

For testing pytest plugins that need to run pytest:

```python
import pytest

@pytest.mark.medium  # pytester spawns subprocesses
def test_my_plugin(pytester):
    pytester.makepyfile("""
        def test_example():
            assert True
    """)
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)
```

Note: Tests using `pytester` should be marked as `@pytest.mark.medium` because `pytester.runpytest()` spawns a subprocess.

### 5. Change Test Size

If the test legitimately requires subprocess execution:

```python
import subprocess
import pytest

@pytest.mark.medium  # Medium tests can spawn processes
def test_cli_integration():
    result = subprocess.run(
        ["myapp", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "1.0.0" in result.stdout
```

### 6. Mock os.system and os.popen

For legacy code using shell commands:

```python
import pytest

@pytest.mark.small
def test_legacy_command(mocker):
    mock_system = mocker.patch("os.system")
    mock_system.return_value = 0

    from myapp.legacy import run_backup
    result = run_backup()

    assert result is True
    mock_system.assert_called_once()
```

### 7. Mock multiprocessing.Process

For code using multiprocessing:

```python
import pytest

@pytest.mark.small
def test_parallel_processing(mocker):
    mock_process = mocker.patch("multiprocessing.Process")
    mock_instance = mocker.MagicMock()
    mock_process.return_value = mock_instance

    from myapp.parallel import start_worker
    start_worker()

    mock_process.assert_called_once()
    mock_instance.start.assert_called_once()
```

## Best Practices

### 1. Start with WARN Mode

When first enabling process isolation, use warn mode to identify all violations:

```bash
pytest --test-categories-enforcement=warn 2>&1 | grep "Subprocess spawn violation"
```

### 2. Separate Command Logic from Execution

Design your code to separate:

- **Command building**: Pure functions that return command lists
- **Command execution**: Thin wrappers around subprocess

This makes the command building easily testable in small tests:

```python
# command_builder.py - easily testable
def build_docker_command(image: str, cmd: list[str]) -> list[str]:
    return ["docker", "run", "--rm", image] + cmd

# executor.py - integration tested
def execute(command: list[str]) -> int:
    import subprocess
    return subprocess.run(command).returncode
```

### 3. Use Fixtures for Medium Test Setup

Create fixtures that manage subprocess lifecycle:

```python
import subprocess
import pytest

@pytest.fixture
def redis_server():
    """Start a Redis server for medium tests."""
    proc = subprocess.Popen(["redis-server", "--port", "6380"])
    yield proc
    proc.terminate()
    proc.wait()

@pytest.mark.medium
def test_redis_integration(redis_server):
    import redis
    r = redis.Redis(port=6380)
    r.set("key", "value")
    assert r.get("key") == b"value"
```

### 4. Consider Container-Based Testing

For complex integration scenarios, use containers:

```python
import pytest

@pytest.fixture(scope="session")
def docker_compose():
    """Start services via docker-compose."""
    import subprocess
    subprocess.run(["docker-compose", "up", "-d"], check=True)
    yield
    subprocess.run(["docker-compose", "down"], check=True)

@pytest.mark.large
def test_full_stack(docker_compose):
    # Test against containerized services
    ...
```

## Troubleshooting

### "SubprocessViolationError" when using pytester

The `pytester` fixture spawns a subprocess to run pytest. Tests using `pytester` must be marked as medium:

```python
@pytest.mark.medium  # Required for pytester
def test_my_plugin(pytester):
    ...
```

### "subprocess.run not being mocked correctly"

Ensure you're patching the right location:

```python
# Wrong - patches the subprocess module directly
mocker.patch("subprocess.run")

# Right - patches where it's imported
mocker.patch("myapp.commands.subprocess.run")

# Or patch at usage location
mocker.patch.object(myapp.commands, "subprocess")
```

### "Test passes but warns about multiprocessing"

Some libraries use multiprocessing internally:
- `concurrent.futures.ProcessPoolExecutor`
- Parallel data processing libraries
- Machine learning frameworks

**Solution**: Mock the library's parallel execution or use `@pytest.mark.medium`.

## Related Documentation

- [Architecture Decision Record: Process Isolation](../architecture/adr-003-process-isolation.md)
- [Test Sizes](test-sizes.md)
- [Network Isolation](network-isolation.md)
- [Filesystem Isolation](filesystem-isolation.md)
- [Configuration Reference](../configuration.md)
