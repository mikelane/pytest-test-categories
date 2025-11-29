"""Integration tests for configurable time limits feature.

This module tests the complete end-to-end behavior of configurable time limits
using pytester to simulate real pytest runs with custom configurations.

NOTE: Integration tests that require the new CLI options (--test-categories-*-time-limit)
cannot run in a worktree environment because pytester uses the installed plugin version
from the main repository, which may not have these new options yet.

The configurable time limits feature is fully tested through:
1. Unit tests in test_time_limit_config_module.py (TimeLimitConfig model)
2. Unit tests in test_time_limit_options_module.py (CLI/ini option parsing)
3. Unit tests in test_configurable_timing_validation_module.py (validation with config)

After the feature is merged, additional integration tests can be added to verify
end-to-end behavior with the new CLI options.
"""

from __future__ import annotations

import pytest


@pytest.mark.medium
class DescribeConfigurableTimeLimitsIntegration:
    """Integration tests for configurable time limits via pytester."""

    def it_uses_default_limits_when_no_config_provided(self, pytester: pytest.Pytester) -> None:
        """Use default 1s limit for small tests when no config provided.

        This test verifies that the default time limits work correctly.
        Tests for custom time limits are implemented as unit tests since
        the pytester subprocess uses the installed plugin version.
        """
        pytester.makepyfile(
            test_example="""
            import pytest
            import time

            @pytest.mark.small
            def test_small_fast():
                '''Pass with default 1s limit.'''
                time.sleep(0.1)

            @pytest.mark.small
            def test_small_slow():
                '''Fail by exceeding default 1s limit.'''
                time.sleep(1.5)
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1, failed=1)
        result.stdout.fnmatch_lines(['*test_small_slow*FAILED*'])
        result.stdout.fnmatch_lines(['*SMALL test exceeded time limit of 1.0 seconds*'])
