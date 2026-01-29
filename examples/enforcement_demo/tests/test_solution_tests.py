"""Tests demonstrating hermetic solutions (the "after" state).

These tests show how to properly test code that has external dependencies
while maintaining hermeticity. Each test is marked as @pytest.mark.small
and passes even in strict enforcement mode.

Key patterns demonstrated:
- Time injection for testing TTL/expiration logic
- HTTP mocking for API client tests
- pyfakefs for filesystem operations
- Dependency injection for subprocess/executor testing
- Synchronous testing of async/threaded logic

Run with strict enforcement to verify these are truly hermetic:

    pytest --test-categories-enforcement=strict tests/test_solution_tests.py -v

"""

from __future__ import annotations

import io
import json
from typing import Any

import pytest

from demo_app.api_client import ApiClient, User
from demo_app.cache import Cache
from demo_app.config import AppConfig, load_config_from_stream
from demo_app.shell import ShellRunner
from demo_app.worker import Job, process_job

# =============================================================================
# Sleep Solutions - Using controllable time instead of sleep
# =============================================================================


class DescribeCacheWithControllableTime:
    """Tests that use time injection instead of sleep.

    The key insight: don't test that time passes, test that your
    code responds correctly to time values.
    """

    @pytest.mark.small
    def test_cache_stores_and_retrieves_value(self, controllable_time):
        """Test basic cache operations without time dependency."""
        time_func, _ = controllable_time
        cache = Cache(time_func=time_func)

        cache.set("user:1", {"name": "Alice"})
        result = cache.get("user:1")

        assert result == {"name": "Alice"}

    @pytest.mark.small
    def test_cache_expires_after_ttl(self, controllable_time):
        """Test TTL expiration using controllable time.

        Instead of sleeping, we advance the fake clock past the TTL.
        This is instantaneous and deterministic.
        """
        time_func, advance = controllable_time
        cache = Cache(time_func=time_func, default_ttl=60.0)

        cache.set("key", "value")

        # Advance time past TTL
        advance(61.0)

        result = cache.get("key")
        assert result is None, "Entry should have expired"

    @pytest.mark.small
    def test_cache_entry_valid_before_ttl(self, controllable_time):
        """Test that entries are valid before TTL expires."""
        time_func, advance = controllable_time
        cache = Cache(time_func=time_func, default_ttl=60.0)

        cache.set("key", "value")

        # Advance time but not past TTL
        advance(59.0)

        result = cache.get("key")
        assert result == "value", "Entry should still be valid"

    @pytest.mark.small
    def test_cache_custom_ttl(self, controllable_time):
        """Test custom TTL per entry."""
        time_func, advance = controllable_time
        cache = Cache(time_func=time_func, default_ttl=60.0)

        cache.set("short", "value", ttl=10.0)
        cache.set("long", "value", ttl=120.0)

        advance(15.0)

        assert cache.get("short") is None, "Short TTL entry should expire"
        assert cache.get("long") == "value", "Long TTL entry should be valid"


# =============================================================================
# Network Solutions - Using mocks and dependency injection
# =============================================================================


class DescribeApiClientWithMocking:
    """Tests that use HTTP mocking or dependency injection.

    Two approaches:
    1. pytest-httpx/responses for mocking at the HTTP layer
    2. Dependency injection for mocking at the client layer
    """

    @pytest.mark.small
    def test_get_user_with_injected_http(self):
        """Test API client with injected HTTP function.

        The ApiClient accepts an optional http_get function,
        allowing us to inject a fake without external libraries.
        """

        def fake_http_get(url: str) -> dict[str, Any]:
            # Verify the URL is correct
            assert "/users/42" in url
            return {"id": 42, "name": "Alice", "email": "alice@example.com"}

        client = ApiClient("https://api.example.com", http_get=fake_http_get)
        user = client.get_user(42)

        assert user.id == 42
        assert user.name == "Alice"
        assert user.email == "alice@example.com"

    @pytest.mark.small
    def test_list_users_with_injected_http(self):
        """Test listing users with injected HTTP function."""

        def fake_http_get(url: str) -> list[dict[str, Any]]:
            assert "/users" in url
            return [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
            ]

        client = ApiClient("https://api.example.com", http_get=fake_http_get)
        users = client.list_users()

        assert len(users) == 2
        assert users[0].name == "Alice"
        assert users[1].name == "Bob"

    @pytest.mark.small
    def test_health_check_success(self):
        """Test successful health check."""

        def fake_http_get(url: str) -> dict[str, Any]:
            return {"status": "ok"}

        client = ApiClient("https://api.example.com", http_get=fake_http_get)
        assert client.health_check() is True

    @pytest.mark.small
    def test_health_check_failure(self):
        """Test health check when API returns error status."""

        def fake_http_get(url: str) -> dict[str, Any]:
            return {"status": "error", "message": "Database unavailable"}

        client = ApiClient("https://api.example.com", http_get=fake_http_get)
        assert client.health_check() is False

    @pytest.mark.small
    def test_health_check_network_error(self):
        """Test health check when network fails."""

        def fake_http_get(url: str) -> dict[str, Any]:
            raise ConnectionError("Network unreachable")

        client = ApiClient("https://api.example.com", http_get=fake_http_get)
        assert client.health_check() is False

    @pytest.mark.small
    def test_user_model_creation(self):
        """Test User model directly - no network needed."""
        user = User(id=1, name="Alice", email="alice@example.com")

        assert user.id == 1
        assert user.name == "Alice"
        assert user.email == "alice@example.com"


# =============================================================================
# Filesystem Solutions - Using in-memory objects and pyfakefs
# =============================================================================


class DescribeConfigWithInMemory:
    """Tests that use in-memory file-like objects.

    io.StringIO provides a file-like interface without touching
    the filesystem - perfect for small tests.
    """

    @pytest.mark.small
    def test_load_config_from_stream(self, sample_config_data):
        """Test config loading from file-like object."""
        config_json = json.dumps(sample_config_data)
        stream = io.StringIO(config_json)

        config = load_config_from_stream(stream)

        assert config.debug is True
        assert config.log_level == "DEBUG"
        assert config.database_url == "postgresql://localhost/test"

    @pytest.mark.small
    def test_config_defaults(self):
        """Test that config uses sensible defaults."""
        stream = io.StringIO("{}")  # Empty config

        config = load_config_from_stream(stream)

        assert config.debug is False
        assert config.log_level == "INFO"
        assert config.max_retries == 3

    @pytest.mark.small
    def test_config_partial_override(self):
        """Test partial config override."""
        stream = io.StringIO('{"debug": true, "max_retries": 10}')

        config = load_config_from_stream(stream)

        assert config.debug is True  # Overridden
        assert config.max_retries == 10  # Overridden
        assert config.log_level == "INFO"  # Default

    @pytest.mark.small
    def test_app_config_model(self):
        """Test AppConfig model directly - no file I/O needed."""
        config = AppConfig(
            debug=True,
            log_level="DEBUG",
            database_url="postgresql://db/test",
        )

        assert config.debug is True
        assert config.log_level == "DEBUG"
        assert config.timeout == 30.0  # Default value


# =============================================================================
# Subprocess Solutions - Using fake executors
# =============================================================================


class DescribeShellRunnerWithFakeExecutor:
    """Tests that use the FakeCommandExecutor.

    The key pattern: test the command-building logic, not the execution.
    Actual subprocess execution belongs in medium tests.
    """

    @pytest.mark.small
    def test_git_version_with_fake_executor(self, fake_executor):
        """Test git version retrieval with fake executor."""
        fake_executor.add_response(
            ["git", "--version"],
            stdout="git version 2.40.0",
        )

        runner = ShellRunner(_executor=fake_executor)
        version = runner.git_version()

        assert version == "git version 2.40.0"
        assert fake_executor.executed_commands == [("git", "--version")]

    @pytest.mark.small
    def test_git_not_installed(self, fake_executor):
        """Test handling when git is not installed."""
        fake_executor.add_response(
            ["git", "--version"],
            return_code=127,
            stderr="command not found: git",
        )

        runner = ShellRunner(_executor=fake_executor)
        version = runner.git_version()

        assert version == "unknown"

    @pytest.mark.small
    def test_list_directory_with_fake_executor(self, fake_executor):
        """Test directory listing with fake executor."""
        fake_executor.add_response(
            ["ls", "-1", "/home/user"],
            stdout="Documents\nDownloads\nPictures",
        )

        runner = ShellRunner(_executor=fake_executor)
        files = runner.list_directory("/home/user")

        assert files == ["Documents", "Downloads", "Pictures"]
        assert fake_executor.executed_commands == [("ls", "-1", "/home/user")]

    @pytest.mark.small
    def test_disk_usage_with_fake_executor(self, fake_executor):
        """Test disk usage with fake executor."""
        fake_executor.add_response(
            ["du", "-sh", "/var/log"],
            stdout="2.5G\t/var/log",
        )

        runner = ShellRunner(_executor=fake_executor)
        usage = runner.disk_usage("/var/log")

        assert usage == "2.5G\t/var/log"

    @pytest.mark.small
    def test_command_failure(self, fake_executor):
        """Test handling of command failure."""
        fake_executor.add_response(
            ["ls", "-1", "/nonexistent"],
            return_code=2,
            stderr="ls: cannot access: No such file or directory",
        )

        runner = ShellRunner(_executor=fake_executor)
        files = runner.list_directory("/nonexistent")

        assert files == []


# =============================================================================
# Threading Solutions - Testing logic synchronously
# =============================================================================


class DescribeWorkerLogicSynchronously:
    """Tests that test the work logic without threading.

    The key insight: separate the "what" (job processing logic) from
    the "how" (threading, queuing). Test each independently.
    """

    @pytest.mark.small
    def test_process_job_success(self):
        """Test successful job processing - no threads needed."""
        job = Job(id="job-1", payload={"data": "test-value"})

        result = process_job(job)

        assert result.status == "completed"
        assert result.result == {"processed": True, "input": {"data": "test-value"}}
        assert result.error is None

    @pytest.mark.small
    def test_process_job_with_error(self):
        """Test job processing error handling."""
        job = Job(id="job-2", payload={"error": "Something went wrong"})

        result = process_job(job)

        assert result.status == "failed"
        assert result.error == "Something went wrong"
        assert result.result is None

    @pytest.mark.small
    def test_job_model_initial_state(self):
        """Test Job model initial state."""
        job = Job(id="test", payload={"key": "value"})

        assert job.id == "test"
        assert job.status == "pending"
        assert job.result is None
        assert job.error is None

    @pytest.mark.small
    def test_multiple_jobs_processed_independently(self):
        """Test that job processing is stateless."""
        jobs = [
            Job(id="1", payload={"a": 1}),
            Job(id="2", payload={"b": 2}),
            Job(id="3", payload={"error": "fail"}),
        ]

        results = [process_job(job) for job in jobs]

        assert results[0].status == "completed"
        assert results[1].status == "completed"
        assert results[2].status == "failed"


# =============================================================================
# Integration Tests - Medium tests for actual external interactions
# =============================================================================


class DescribeMediumIntegrationTests:
    """Medium tests that actually use external resources.

    These tests are marked @pytest.mark.medium and are allowed to:
    - Use localhost network
    - Access the filesystem
    - Spawn subprocesses
    - Use threads with proper synchronization
    """

    @pytest.mark.medium
    def test_background_worker_integration(self):
        """Test BackgroundWorker with real threading.

        This is a medium test because it uses real threads.
        Note: Uses proper synchronization instead of sleep.
        """
        from demo_app.worker import BackgroundWorker

        worker = BackgroundWorker()
        worker.start()

        job = Job(id="integration-1", payload={"data": "test"})
        worker.submit(job)

        # Proper synchronization - wait for completion event
        completed = worker.wait_for_completion(timeout=5.0)
        worker.stop()

        assert completed, "Worker should complete within timeout"
        assert len(worker.processed_jobs) == 1
        assert worker.processed_jobs[0].status == "completed"

    @pytest.mark.medium
    def test_shell_runner_with_real_command(self):
        """Test ShellRunner with actual subprocess.

        This is a medium test because it spawns a real process.
        Uses a portable command that works on most systems.
        """
        runner = ShellRunner()  # Real executor
        result = runner.run("echo", "hello")

        assert result.success
        assert "hello" in result.stdout

    @pytest.mark.medium
    def test_config_with_temp_file(self, tmp_path):
        """Test config loading with real filesystem.

        This is a medium test because it uses tmp_path (real filesystem).
        Note: tmp_path is pytest's built-in fixture for temp directories.
        """
        from demo_app.config import load_config, save_config

        config_file = tmp_path / "config.json"
        original = AppConfig(debug=True, log_level="DEBUG")

        save_config(original, config_file)
        loaded = load_config(config_file)

        assert loaded.debug == original.debug
        assert loaded.log_level == original.log_level
