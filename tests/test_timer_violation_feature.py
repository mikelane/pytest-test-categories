"""Test timing violation detection."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(autouse=True)
def plugin_conftest(request: pytest.FixtureRequest) -> Path:
    """Create a conftest.py file that registers the plugin with a mock timer.

    Args:
        request: The pytest request object containing the parametrized duration.

    Returns:
        The path to the created conftest file.

    """
    pytester = request.getfixturevalue('pytester')
    duration = getattr(request, 'param', 1.0)

    return pytester.makeconftest(f"""
        def pytest_configure(config):
            from pytest_test_categories.plugin import TestCategories
            from pytest_test_categories.types import TestTimer, TimerState

            class TestMockTimer(TestTimer):
                desired_duration: float = {duration}

                def __hash__(self) -> int:
                    return hash((self.state, self.desired_duration))

                def start(self) -> None:
                    self.state = TimerState.RUNNING

                def stop(self) -> None:
                    self.state = TimerState.STOPPED

                def duration(self) -> float:
                    return self.desired_duration

            plugin = TestCategories(timer=TestMockTimer())
            config.pluginmanager.register(plugin)
    """)


class DescribeTimerViolations:
    @pytest.mark.parametrize(
        'plugin_conftest',
        [
            pytest.param(1.1, id='small_test_slightly_over_limit'),
        ],
        indirect=True,
    )
    def it_fails_tests_that_exceed_time_limit(
        self,
        pytester: pytest.Pytester,
    ) -> None:
        """Verify that SMALL tests exceeding 1 second fail with TimingViolationError."""
        # Create test file
        test_file = pytester.makepyfile("""
            import pytest

            @pytest.mark.small
            def test_example():
                assert True
        """)

        result = pytester.runpytest('-v', test_file)

        result.stdout.fnmatch_lines(['*TimingViolationError: SMALL test exceeded time limit of 1.0 seconds*'])
