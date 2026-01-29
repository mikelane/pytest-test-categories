"""Shared fixtures for enforcement demo tests.

This conftest provides fixtures that demonstrate both problematic patterns
(for test_problem_tests.py) and proper solutions (for test_solution_tests.py).
"""

from __future__ import annotations

import pytest

from demo_app.shell import FakeCommandExecutor


@pytest.fixture
def fake_executor() -> FakeCommandExecutor:
    """Provide a fake command executor for testing shell commands.

    This fixture demonstrates dependency injection for subprocess testing.
    Instead of spawning real processes, tests can use this fake executor
    to verify command-building logic.

    Example:
        def test_git_command(fake_executor):
            fake_executor.add_response(['git', '--version'], stdout='git version 2.40.0')
            runner = ShellRunner(_executor=fake_executor)
            assert runner.git_version() == 'git version 2.40.0'

    """
    return FakeCommandExecutor()


@pytest.fixture
def sample_config_data() -> dict:
    """Provide sample configuration data for testing.

    This fixture provides configuration data as a Python dict,
    avoiding the need for filesystem access in small tests.

    """
    return {
        "debug": True,
        "log_level": "DEBUG",
        "database_url": "postgresql://localhost/test",
        "api_key": "test-api-key-12345",
        "max_retries": 5,
        "timeout": 60.0,
    }


@pytest.fixture
def controllable_time():
    """Provide a controllable time function for cache testing.

    This fixture demonstrates the time injection pattern for testing
    time-dependent code without using sleep.

    Example:
        def test_cache_expiration(controllable_time):
            current_time, advance = controllable_time
            cache = Cache(time_func=current_time)

            cache.set('key', 'value', ttl=60)
            advance(61)  # Advance past TTL

            assert cache.get('key') is None

    """

    class ControllableTime:
        def __init__(self) -> None:
            self._current = 1000.0  # Start at arbitrary time

        def __call__(self) -> float:
            return self._current

        def advance(self, seconds: float) -> None:
            self._current += seconds

    time_obj = ControllableTime()
    return time_obj, time_obj.advance
