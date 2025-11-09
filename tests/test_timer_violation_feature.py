"""Test timing violation detection."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from pytest_test_categories.types import (
    TestTimer,
    TimerState,
)

if TYPE_CHECKING:
    from pathlib import Path


class MockTimer(TestTimer):
    """Mock timer implementation for testing."""

    desired_duration: float = 1.0

    def start(self) -> None:
        """Start the mock timer."""
        self.state = TimerState.RUNNING

    def stop(self) -> None:
        """Stop the mock timer."""
        self.state = TimerState.STOPPED

    def duration(self) -> float:
        """Get the predefined duration."""
        return self.desired_duration


@pytest.fixture(autouse=True)
def plugin_conftest(pytester: pytest.Pytester, request: pytest.FixtureRequest) -> None:
    """Create plugin conftest with mock timer."""
    duration = getattr(request, 'param', 1.0)

    # Create test file with the right marker
    pytester.makepyfile(
        test_example="""
        import pytest

        @pytest.mark.small
        def test_example():
            assert True
        """
    )

    # Create the plugin code in a separate file
    pytester.makepyfile(
        test_categories_plugin=f"""
        from pydantic import Field
        from pytest_test_categories.types import TestTimer, TimerState, TimingViolationError, TestSize
        from pytest_test_categories.plugin import _get_session_state
        from pytest_test_categories import timing
        import pytest

        # Store the desired duration at module level
        MOCK_DURATION = {duration}

        class TestMockTimer(TestTimer):
            desired_duration: float = Field(default=1.0)

            def __init__(self, *, state=TimerState.READY, duration=1.0):
                super().__init__(state=state)
                self.desired_duration = duration
                print(f'Created TestMockTimer with duration {{duration}}')

            def start(self) -> None:
                if self.state != TimerState.READY:
                    self.state = TimerState.READY
                super().start()
                print('Timer started')

            def stop(self) -> None:
                super().stop()
                print('Timer stopped')

            def duration(self) -> float:
                if self.state != TimerState.STOPPED:
                    raise RuntimeError('Timer must be stopped to get duration')
                print(f'Reporting duration: {{self.desired_duration}}')
                return self.desired_duration

        @pytest.hookimpl(hookwrapper=True, tryfirst=True)
        def pytest_runtest_protocol(item, nextitem):
            session_state = _get_session_state(item.config)
            # Create a unique timer for this test item - use tryfirst to run before the real plugin
            timer = TestMockTimer(state=TimerState.READY, duration=MOCK_DURATION)
            session_state.timers[item.nodeid] = timer

            try:
                timer.start()
                print('Protocol: Timer started')
                yield
            finally:
                if timer.state == TimerState.RUNNING:
                    timer.stop()
                    print('Protocol: Timer stopped')

        @pytest.hookimpl(hookwrapper=True)
        def pytest_runtest_makereport(item, call):
            session_state = _get_session_state(item.config)
            timer = session_state.timers.get(item.nodeid)

            if call.when == 'call' and timer and timer.state == TimerState.RUNNING:
                timer.stop()
                print('Makereport: Timer stopped')

            outcome = yield
            report = outcome.get_result()

            if report.when == 'call':
                test_size = next(
                    (size for size in TestSize if item.get_closest_marker(size.marker_name)),
                    None,
                )

                if test_size and timer and timer.state == TimerState.STOPPED:
                    try:
                        duration = timer.duration()
                        print(f'Validating timing for {{test_size}}: {{duration}}')
                        timing.validate(test_size, duration)
                    except TimingViolationError as e:
                        print(f'Timing violation detected: {{e}}')
                        report.outcome = 'failed'
                        report.longrepr = str(e)
                    finally:
                        # Clean up the timer after use
                        if item.nodeid in session_state.timers:
                            del session_state.timers[item.nodeid]
        """
    )

    # Create conftest.py to register the plugin
    pytester.makeconftest("""
        pytest_plugins = ['test_categories_plugin']
    """)


@pytest.fixture
def test_file(pytester: pytest.Pytester, request: pytest.FixtureRequest) -> Path:
    """Create a test file with the specified size marker."""
    size = request.param
    return pytester.makepyfile(
        test_example=f"""
        import pytest

        @pytest.mark.{size}
        def test_example():
            assert True
        """
    )


class DescribeTimerViolations:
    @pytest.mark.parametrize(
        ('plugin_conftest', 'test_file', 'expected_message'),
        [
            pytest.param(
                1.1,
                'small',
                '*SMALL test exceeded time limit of 1.0 seconds*',
                id='small test over time limit',
            ),
            pytest.param(
                300.1,
                'medium',
                '*MEDIUM test exceeded time limit of 300.0 seconds*',
                id='medium test over time limit',
            ),
            pytest.param(
                900.1,
                'large',
                '*LARGE test exceeded time limit of 900.0 seconds*',
                id='large test over time limit',
            ),
            pytest.param(
                900.1,
                'xlarge',
                '*XLARGE test exceeded time limit of 900.0 seconds*',
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
