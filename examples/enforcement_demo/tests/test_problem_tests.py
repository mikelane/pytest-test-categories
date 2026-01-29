"""Tests demonstrating hermeticity violations (the "before" state).

These tests show common anti-patterns that cause flaky tests. Each test is
marked as @pytest.mark.small but violates hermeticity constraints:

- Sleep violations: Using time.sleep() to wait for conditions
- Network violations: Making real HTTP requests
- Filesystem violations: Reading/writing real files
- Subprocess violations: Spawning real processes
- Threading violations: Creating threads with timing assumptions

Run with different enforcement modes to see the behavior:

    # See violations as warnings (tests pass)
    pytest --test-categories-enforcement=warn tests/test_problem_tests.py -v

    # Violations fail tests
    pytest --test-categories-enforcement=strict tests/test_problem_tests.py -v

These tests are intentionally flaky to demonstrate why enforcement matters.
DO NOT use these patterns in real code!
"""

from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path

import pytest

from demo_app.cache import Cache
from demo_app.shell import ShellRunner
from demo_app.worker import BackgroundWorker, Job

# =============================================================================
# Sleep Violations - Using time.sleep() in small tests
# =============================================================================


class DescribeSleepViolations:
    """Tests that violate sleep constraints.

    Small tests should be fast and deterministic. Using time.sleep()
    introduces unnecessary delays and can cause flaky failures due to
    timing variations.
    """

    @pytest.mark.small
    def test_cache_expiration_with_sleep(self):
        """VIOLATION: Uses time.sleep() to wait for cache expiration.

        This test is flaky because:
        1. It wastes time (0.2 seconds per test adds up)
        2. Timing can vary causing intermittent failures
        3. It depends on system clock precision

        Run with: pytest --test-categories-enforcement=strict
        """
        cache = Cache(default_ttl=0.1)
        cache.set("key", "value")

        # VIOLATION: Sleep in small test
        time.sleep(0.2)

        result = cache.get("key")
        assert result is None, "Cache entry should have expired"

    @pytest.mark.small
    def test_polling_with_sleep(self):
        """VIOLATION: Uses sleep for polling a condition.

        This pattern is common but problematic:
        - Arbitrary sleep duration
        - May be too short (flaky) or too long (slow)
        """
        ready = {"value": False}

        def make_ready():
            ready["value"] = True

        # Simulate async operation
        threading.Timer(0.05, make_ready).start()

        # VIOLATION: Polling with sleep
        for _ in range(5):
            if ready["value"]:
                break
            time.sleep(0.05)

        assert ready["value"], "Should be ready"


# =============================================================================
# Network Violations - Making real HTTP requests in small tests
# =============================================================================


class DescribeNetworkViolations:
    """Tests that violate network constraints.

    Small tests should be hermetic - no external dependencies.
    Real network calls make tests:
    - Slow (network latency)
    - Flaky (network failures, rate limits, server changes)
    - Non-reproducible (different results over time)
    """

    @pytest.mark.small
    def test_fetch_from_real_api(self):
        """VIOLATION: Makes real HTTP request.

        This test fails in CI because it hits a real API.
        Even if it works today, it may fail tomorrow due to:
        - API changes
        - Rate limiting
        - Network issues
        - Authentication expiration

        Run with: pytest --test-categories-enforcement=strict
        """
        import urllib.request

        # VIOLATION: Real network request in small test
        try:
            with urllib.request.urlopen("https://httpbin.org/get", timeout=5) as response:  # noqa: S310
                data = response.read()
                assert b"httpbin" in data or len(data) > 0
        except Exception as e:
            # This is exactly why network tests are flaky!
            pytest.skip(f"Network request failed (proving the point): {e}")

    @pytest.mark.small
    def test_check_external_service_health(self):
        """VIOLATION: Checks real external service health.

        Health checks against real services are problematic:
        - Service may be down for maintenance
        - Network path may be blocked in CI
        - Response format may change
        """
        import socket

        # VIOLATION: Network connection in small test
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect(("google.com", 443))
            sock.close()
            connected = True
        except (OSError, TimeoutError):
            connected = False

        # This assertion proves nothing useful - service availability
        # is not what we're testing!
        assert connected or not connected  # Always passes, but still violates


# =============================================================================
# Filesystem Violations - Accessing real files in small tests
# =============================================================================


class DescribeFilesystemViolations:
    """Tests that violate filesystem constraints.

    Small tests should not depend on the filesystem because:
    - Files may not exist in all environments
    - Paths differ between systems
    - Tests may interfere with each other
    - Cleanup is error-prone
    """

    @pytest.mark.small
    def test_read_system_file(self):
        """VIOLATION: Reads a system file.

        This test assumes /etc/passwd exists with certain content.
        Fails on Windows, containers without the file, etc.

        Run with: pytest --test-categories-enforcement=strict
        """
        # VIOLATION: Reading real filesystem
        path = Path("/etc/passwd")
        if path.exists():
            content = path.read_text()
            assert "root" in content or len(content) > 0
        else:
            pytest.skip("System file not available")

    @pytest.mark.small
    def test_write_to_current_directory(self):
        """VIOLATION: Writes to current working directory.

        Writing to CWD is problematic:
        - May conflict with other tests
        - May leave artifacts if cleanup fails
        - Different CWD in different environments

        Run with: pytest --test-categories-enforcement=strict
        """
        test_file = Path("test_output_file.txt")

        try:
            # VIOLATION: Writing to filesystem
            test_file.write_text("test data")
            assert test_file.exists()
            content = test_file.read_text()
            assert content == "test data"
        finally:
            # Cleanup - but what if this fails?
            if test_file.exists():
                test_file.unlink()


# =============================================================================
# Subprocess Violations - Spawning real processes in small tests
# =============================================================================


class DescribeSubprocessViolations:
    """Tests that violate subprocess constraints.

    Small tests should not spawn subprocesses because:
    - External tools may not be installed
    - Tool versions may differ
    - Process spawning is slow
    - Output format may vary
    """

    @pytest.mark.small
    def test_run_shell_command(self):
        """VIOLATION: Runs a real shell command.

        This test assumes 'ls' is available with certain behavior.
        Fails on Windows, minimal containers, etc.

        Run with: pytest --test-categories-enforcement=strict
        """
        # VIOLATION: Subprocess spawn in small test
        result = subprocess.run(["ls", "-la"], capture_output=True, text=True, check=False)

        # This tests the ls command, not our code!
        assert result.returncode == 0 or result.returncode != 0

    @pytest.mark.small
    def test_shell_runner_real_execution(self):
        """VIOLATION: Uses ShellRunner with real subprocess.

        Even with our abstraction, this test still spawns a real process.

        Run with: pytest --test-categories-enforcement=strict
        """
        runner = ShellRunner()  # Uses RealCommandExecutor by default

        # VIOLATION: This calls subprocess.run internally
        version = runner.git_version()

        # May be 'unknown' if git isn't installed
        assert version is not None


# =============================================================================
# Threading Violations - Creating threads with timing assumptions
# =============================================================================


class DescribeThreadingViolations:
    """Tests that violate threading constraints.

    Threading in small tests is problematic because:
    - Race conditions cause flaky failures
    - Timing assumptions don't hold under load
    - Threads may not complete in time
    - Hard to reason about test isolation
    """

    @pytest.mark.small
    def test_background_worker_with_timing(self):
        """VIOLATION: Tests threading with timing assumptions.

        This test is flaky because it assumes the worker
        processes jobs within a specific time window.

        Run with: pytest --test-categories-enforcement=strict
        """
        worker = BackgroundWorker()
        worker.start()

        job = Job(id="test-1", payload={"data": "test"})
        worker.submit(job)

        # VIOLATION: Sleep to wait for thread + timing assumption
        time.sleep(0.2)

        worker.stop()

        # Flaky: job may or may not be processed depending on timing
        processed = worker.processed_jobs
        assert len(processed) >= 0  # Always passes but demonstrates the issue

    @pytest.mark.small
    def test_concurrent_operations(self):
        """VIOLATION: Tests concurrent operations with threads.

        This test creates threads and hopes they complete in order.

        Run with: pytest --test-categories-enforcement=strict
        """
        results = []

        def append_value(value: str) -> None:
            results.append(value)

        # VIOLATION: Creating threads in small test
        threads = [threading.Thread(target=append_value, args=(f"value-{i}",)) for i in range(3)]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=1.0)

        # Order is non-deterministic!
        assert len(results) == 3


# =============================================================================
# Combined Violations - Multiple anti-patterns together
# =============================================================================


class DescribeCombinedViolations:
    """Tests that combine multiple violations.

    In real codebases, problematic tests often have multiple issues.
    These examples show how violations compound.
    """

    @pytest.mark.small
    def test_fetch_save_and_wait(self):
        """VIOLATION: Network + Filesystem + Sleep combined.

        This test has three violations:
        1. Makes a network request
        2. Writes to filesystem
        3. Uses sleep

        Run with: pytest --test-categories-enforcement=strict
        """
        import socket
        from pathlib import Path

        # VIOLATION 1: Network
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.connect(("localhost", 9999))  # Unlikely to be running
            sock.close()
            data = "connected"
        except (OSError, TimeoutError, ConnectionRefusedError):
            data = "not connected"

        # VIOLATION 2: Filesystem
        output = Path("combined_test_output.txt")
        try:
            output.write_text(data)

            # VIOLATION 3: Sleep
            time.sleep(0.05)

            content = output.read_text()
            assert content in ("connected", "not connected")
        finally:
            if output.exists():
                output.unlink()
