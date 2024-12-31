"""Test timing violation detection."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(autouse=True)
def plugin_conftest(request: pytest.FixtureRequest) -> Path:
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


@pytest.fixture
def test_file(request: pytest.FixtureRequest, pytester: pytest.Pytester) -> Path:
    """Create a test file with the specified test size marker."""
    size = request.param
    return pytester.makepyfile(f"""
        import pytest

        @pytest.mark.{size}
        def test_example():
            assert True
    """)


class DescribeTimerViolations:
    @pytest.mark.parametrize(
        ('plugin_conftest', 'test_file', 'expected_message'),
        [
            pytest.param(
                1.1,
                'small',
                '*TimingViolationError: SMALL test exceeded time limit of 1.0 seconds*',
                id='small test over time limit',
            ),
            pytest.param(
                300.1,
                'medium',
                '*TimingViolationError: MEDIUM test exceeded time limit of 300.0 seconds*',
                id='medium test over time limit',
            ),
            pytest.param(
                900.1,
                'large',
                '*TimingViolationError: LARGE test exceeded time limit of 900.0 seconds*',
                id='large test over time limit',
            ),
            pytest.param(
                900.1,
                'xlarge',
                '*TimingViolationError: XLARGE test exceeded time limit of 900.0 seconds*',
                id='xlarge test over time limit',
            ),
        ],
        indirect=['plugin_conftest', 'test_file'],
    )
    def it_fails_tests_that_exceed_time_limit(
        self,
        pytester: pytest.Pytester,
        test_file: Path,
        expected_message: str,
    ) -> None:
        """Verify that tests exceeding their time limit fail with TimingViolationError."""
        result = pytester.runpytest('-v', test_file)
        result.stdout.fnmatch_lines([expected_message])

    @pytest.mark.parametrize(
        ('plugin_conftest', 'test_file'),
        [
            pytest.param(1.0, 'small', id='small test within time limit'),
            pytest.param(300.0, 'medium', id='medium test within time limit'),
            pytest.param(900.0, 'large', id='large test within time limit'),
            pytest.param(900.0, 'xlarge', id='xlarge test within time limit'),
        ],
        indirect=True,
    )
    def it_passes_tests_that_do_not_exceed_time_limit(
        self,
        pytester: pytest.Pytester,
        test_file: Path,
    ) -> None:
        """Verify that tests that do not exceed the time limit pass."""
        result = pytester.runpytest('-v', test_file)
        result.stdout.fnmatch_lines(['*PASSED*'])
