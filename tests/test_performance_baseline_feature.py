"""Integration tests for performance baseline feature.

These tests use pytester to test the plugin's handling of custom timeout
parameters in markers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def baseline_test_file(pytester: pytest.Pytester, request: pytest.FixtureRequest) -> Path:
    """Create a test file with custom timeout baseline.

    Params:
        size: Test size marker (small, medium, large, xlarge)
        timeout: Custom timeout in seconds
    """
    params = request.param
    size = params['size']
    timeout = params['timeout']

    return pytester.makepyfile(
        test_baseline=f"""
        import pytest

        @pytest.mark.{size}(timeout={timeout})
        def test_with_baseline():
            assert True
        """
    )


@pytest.fixture
def no_baseline_test_file(pytester: pytest.Pytester, request: pytest.FixtureRequest) -> Path:
    """Create a test file without custom timeout baseline.

    Params:
        size: Test size marker (small, medium, large, xlarge)
    """
    size = request.param
    return pytester.makepyfile(
        test_no_baseline=f"""
        import pytest

        @pytest.mark.{size}
        def test_without_baseline():
            assert True
        """
    )


@pytest.mark.medium
class DescribePerformanceBaselineIntegration:
    """Integration tests for performance baseline feature."""

    @pytest.mark.parametrize(
        'baseline_test_file',
        [
            pytest.param({'size': 'small', 'timeout': 0.1}, id='small-with-100ms-baseline'),
            pytest.param({'size': 'medium', 'timeout': 5.0}, id='medium-with-5s-baseline'),
        ],
        indirect=True,
    )
    def it_accepts_timeout_parameter_in_marker(
        self,
        pytester: pytest.Pytester,
        baseline_test_file: Path,
    ) -> None:
        """Accept timeout parameter in size marker without error."""
        result = pytester.runpytest('-v', baseline_test_file)
        # Test should pass (no syntax error from timeout parameter)
        result.assert_outcomes(passed=1)

    @pytest.mark.parametrize(
        'no_baseline_test_file',
        [
            pytest.param('small', id='small-without-baseline'),
            pytest.param('medium', id='medium-without-baseline'),
        ],
        indirect=True,
    )
    def it_works_without_timeout_parameter(
        self,
        pytester: pytest.Pytester,
        no_baseline_test_file: Path,
    ) -> None:
        """Work correctly when no timeout parameter is specified."""
        result = pytester.runpytest('-v', no_baseline_test_file)
        result.assert_outcomes(passed=1)


@pytest.mark.medium
class DescribePerformanceBaselineViolation:
    """Test baseline violations are reported correctly."""

    def it_reports_baseline_violation_for_slow_test(
        self,
        pytester: pytest.Pytester,
    ) -> None:
        """Report PerformanceBaselineViolationError when test exceeds baseline."""
        # Create a test that uses time.sleep to exceed the baseline
        pytester.makepyfile(
            test_slow="""
            import time
            import pytest

            @pytest.mark.small(timeout=0.01)
            def test_exceeds_baseline():
                time.sleep(0.05)  # Sleep 50ms, exceeds 10ms baseline
                assert True
            """
        )

        result = pytester.runpytest('-v')
        # Test should fail due to baseline violation
        result.assert_outcomes(failed=1)
        # Check for performance baseline error message
        result.stdout.fnmatch_lines(['*Performance Baseline*'])

    def it_passes_when_test_completes_within_baseline(
        self,
        pytester: pytest.Pytester,
    ) -> None:
        """Pass when test completes within custom baseline."""
        pytester.makepyfile(
            test_fast="""
            import pytest

            @pytest.mark.small(timeout=1.0)
            def test_within_baseline():
                # Very fast test, well within 1s baseline
                assert True
            """
        )

        result = pytester.runpytest('-v')
        result.assert_outcomes(passed=1)

    def it_shows_both_baseline_and_category_limit_in_error(
        self,
        pytester: pytest.Pytester,
    ) -> None:
        """Include both baseline and category limit in error message."""
        pytester.makepyfile(
            test_baseline_error="""
            import time
            import pytest

            @pytest.mark.small(timeout=0.01)
            def test_shows_limits():
                time.sleep(0.05)
                assert True
            """
        )

        result = pytester.runpytest('-v')
        result.assert_outcomes(failed=1)
        # Error should mention both the baseline (0.01s) and category limit (1.0s)
        output = result.stdout.str()
        assert '0.0' in output  # baseline (0.01)
        assert '1.0' in output  # category limit


@pytest.mark.medium
class DescribeBaselineValidation:
    """Test baseline validation rules."""

    def it_rejects_baseline_exceeding_category_limit(
        self,
        pytester: pytest.Pytester,
    ) -> None:
        """Reject baseline that exceeds category limit."""
        pytester.makepyfile(
            test_invalid_baseline="""
            import pytest

            @pytest.mark.small(timeout=2.0)  # Exceeds 1.0s SMALL limit
            def test_invalid():
                assert True
            """
        )

        result = pytester.runpytest('-v')
        # Test should fail due to invalid baseline configuration
        result.assert_outcomes(failed=1)
        result.stdout.fnmatch_lines(['*baseline*category limit*'])
