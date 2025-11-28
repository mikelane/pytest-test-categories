"""Feature tests for distribution enforcement.

This module tests end-to-end distribution enforcement behavior through pytest's
plugin system. It verifies that:
- OFF mode does nothing (silent, no validation)
- WARN mode emits warnings but allows build to continue
- STRICT mode fails collection when distribution is outside acceptable range

Uses pytester fixture for full pytest integration testing.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.medium


@pytest.fixture(autouse=True)
def conftest_file(pytester: pytest.Pytester) -> None:
    """Create a conftest file with the test categories plugin registered."""
    pytester.makeconftest("""
        import pytest
        from pytest_test_categories.distribution.stats import DistributionStats

        @pytest.fixture
        def distribution_stats(request):
            return request.config.distribution_stats
    """)


class DescribeDistributionEnforcementOff:
    """Tests for OFF enforcement mode (default behavior)."""

    def it_does_not_validate_distribution_when_off(self, pytester: pytest.Pytester) -> None:
        """OFF mode produces no warnings or errors for bad distribution."""
        pytester.makepyfile(
            test_bad_distribution="""
            import pytest

            # Intentionally bad distribution: only large tests
            @pytest.mark.large
            def test_large_one():
                assert True

            @pytest.mark.large
            def test_large_two():
                assert True

            @pytest.mark.large
            def test_large_three():
                assert True
            """
        )

        result = pytester.runpytest(
            '-v',
            '--test-categories-distribution-enforcement=off',
        )

        result.assert_outcomes(passed=3)
        # No distribution warning should appear
        assert 'distribution' not in result.stdout.str().lower() or 'summary' in result.stdout.str().lower()

    def it_uses_off_as_default_mode(self, pytester: pytest.Pytester) -> None:
        """Default behavior is OFF mode when no config is specified."""
        pytester.makepyfile(
            test_bad_distribution="""
            import pytest

            # Intentionally bad distribution: only large tests
            @pytest.mark.large
            def test_large_one():
                assert True

            @pytest.mark.large
            def test_large_two():
                assert True
            """
        )

        # Run without specifying enforcement mode
        result = pytester.runpytest('-v')

        # Tests should pass without distribution enforcement errors
        result.assert_outcomes(passed=2)


class DescribeDistributionEnforcementWarn:
    """Tests for WARN enforcement mode."""

    def it_emits_warning_for_bad_distribution(self, pytester: pytest.Pytester) -> None:
        """WARN mode emits warning but allows tests to pass."""
        pytester.makepyfile(
            test_bad_distribution="""
            import pytest

            # Intentionally bad distribution: only large tests (0% small)
            @pytest.mark.large
            def test_large_one():
                assert True

            @pytest.mark.large
            def test_large_two():
                assert True
            """
        )

        result = pytester.runpytest(
            '-v',
            '--test-categories-distribution-enforcement=warn',
        )

        # Tests should still pass
        result.assert_outcomes(passed=2)
        # Warning should be emitted
        result.stdout.fnmatch_lines(['*PytestWarning*distribution*'])

    def it_does_not_warn_for_good_distribution(self, pytester: pytest.Pytester) -> None:
        """WARN mode does not warn when distribution is acceptable."""
        pytester.makepyfile(
            test_good_distribution="""
            import pytest

            # Good distribution: 80% small, 15% medium, 5% large
            @pytest.mark.small
            def test_small_1(): assert True
            @pytest.mark.small
            def test_small_2(): assert True
            @pytest.mark.small
            def test_small_3(): assert True
            @pytest.mark.small
            def test_small_4(): assert True
            @pytest.mark.small
            def test_small_5(): assert True
            @pytest.mark.small
            def test_small_6(): assert True
            @pytest.mark.small
            def test_small_7(): assert True
            @pytest.mark.small
            def test_small_8(): assert True
            @pytest.mark.small
            def test_small_9(): assert True
            @pytest.mark.small
            def test_small_10(): assert True
            @pytest.mark.small
            def test_small_11(): assert True
            @pytest.mark.small
            def test_small_12(): assert True
            @pytest.mark.small
            def test_small_13(): assert True
            @pytest.mark.small
            def test_small_14(): assert True
            @pytest.mark.small
            def test_small_15(): assert True
            @pytest.mark.small
            def test_small_16(): assert True

            @pytest.mark.medium
            def test_medium_1(): assert True
            @pytest.mark.medium
            def test_medium_2(): assert True
            @pytest.mark.medium
            def test_medium_3(): assert True

            @pytest.mark.large
            def test_large_1(): assert True
            """
        )

        result = pytester.runpytest(
            '-v',
            '--test-categories-distribution-enforcement=warn',
        )

        result.assert_outcomes(passed=20)
        # No distribution warning
        assert 'does not meet targets' not in result.stdout.str()

    def it_can_be_configured_via_ini(self, pytester: pytest.Pytester) -> None:
        """WARN mode can be set via pytest.ini configuration."""
        pytester.makeini("""
            [pytest]
            test_categories_distribution_enforcement = warn
        """)
        pytester.makepyfile(
            test_bad_distribution="""
            import pytest

            @pytest.mark.large
            def test_large_one():
                assert True
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)
        result.stdout.fnmatch_lines(['*PytestWarning*distribution*'])


class DescribeDistributionEnforcementStrict:
    """Tests for STRICT enforcement mode."""

    def it_fails_collection_for_bad_distribution(self, pytester: pytest.Pytester) -> None:
        """STRICT mode fails when distribution is outside acceptable range."""
        pytester.makepyfile(
            test_bad_distribution="""
            import pytest

            # Intentionally bad distribution: 0% small (target is 80%)
            @pytest.mark.large
            def test_large_one():
                assert True

            @pytest.mark.large
            def test_large_two():
                assert True
            """
        )

        result = pytester.runpytest(
            '-v',
            '--test-categories-distribution-enforcement=strict',
        )

        # Collection should fail
        assert result.ret != 0
        # UsageError messages go to stderr
        result.stderr.fnmatch_lines(['*Distribution violation*'])

    def it_passes_for_good_distribution(self, pytester: pytest.Pytester) -> None:
        """STRICT mode passes when distribution is within acceptable range."""
        pytester.makepyfile(
            test_good_distribution="""
            import pytest

            # Good distribution: 80% small, 15% medium, 5% large
            @pytest.mark.small
            def test_small_1(): assert True
            @pytest.mark.small
            def test_small_2(): assert True
            @pytest.mark.small
            def test_small_3(): assert True
            @pytest.mark.small
            def test_small_4(): assert True
            @pytest.mark.small
            def test_small_5(): assert True
            @pytest.mark.small
            def test_small_6(): assert True
            @pytest.mark.small
            def test_small_7(): assert True
            @pytest.mark.small
            def test_small_8(): assert True
            @pytest.mark.small
            def test_small_9(): assert True
            @pytest.mark.small
            def test_small_10(): assert True
            @pytest.mark.small
            def test_small_11(): assert True
            @pytest.mark.small
            def test_small_12(): assert True
            @pytest.mark.small
            def test_small_13(): assert True
            @pytest.mark.small
            def test_small_14(): assert True
            @pytest.mark.small
            def test_small_15(): assert True
            @pytest.mark.small
            def test_small_16(): assert True

            @pytest.mark.medium
            def test_medium_1(): assert True
            @pytest.mark.medium
            def test_medium_2(): assert True
            @pytest.mark.medium
            def test_medium_3(): assert True

            @pytest.mark.large
            def test_large_1(): assert True
            """
        )

        result = pytester.runpytest(
            '-v',
            '--test-categories-distribution-enforcement=strict',
        )

        result.assert_outcomes(passed=20)

    def it_shows_clear_error_message(self, pytester: pytest.Pytester) -> None:
        """STRICT mode shows actionable error message with current vs expected."""
        pytester.makepyfile(
            test_bad_distribution="""
            import pytest

            # 50% small (too low), 30% medium (too high), 20% large (too high)
            @pytest.mark.small
            def test_small_1(): assert True
            @pytest.mark.small
            def test_small_2(): assert True
            @pytest.mark.small
            def test_small_3(): assert True
            @pytest.mark.small
            def test_small_4(): assert True
            @pytest.mark.small
            def test_small_5(): assert True

            @pytest.mark.medium
            def test_medium_1(): assert True
            @pytest.mark.medium
            def test_medium_2(): assert True
            @pytest.mark.medium
            def test_medium_3(): assert True

            @pytest.mark.large
            def test_large_1(): assert True
            @pytest.mark.large
            def test_large_2(): assert True
            """
        )

        result = pytester.runpytest(
            '-v',
            '--test-categories-distribution-enforcement=strict',
        )

        assert result.ret != 0
        # Error message should include distribution details (in stderr for UsageError)
        output = result.stderr.str()
        assert 'small' in output.lower()
        assert 'target' in output.lower() or '%' in output

    def it_can_be_configured_via_ini(self, pytester: pytest.Pytester) -> None:
        """STRICT mode can be set via pytest.ini configuration."""
        pytester.makeini("""
            [pytest]
            test_categories_distribution_enforcement = strict
        """)
        pytester.makepyfile(
            test_bad_distribution="""
            import pytest

            @pytest.mark.large
            def test_large_one():
                assert True
            """
        )

        result = pytester.runpytest('-v')

        assert result.ret != 0
        # UsageError messages go to stderr
        result.stderr.fnmatch_lines(['*Distribution violation*'])

    def it_cli_overrides_ini(self, pytester: pytest.Pytester) -> None:
        """CLI option overrides ini configuration."""
        pytester.makeini("""
            [pytest]
            test_categories_distribution_enforcement = strict
        """)
        pytester.makepyfile(
            test_bad_distribution="""
            import pytest

            @pytest.mark.large
            def test_large_one():
                assert True
            """
        )

        # CLI sets OFF, which should override strict ini setting
        result = pytester.runpytest(
            '-v',
            '--test-categories-distribution-enforcement=off',
        )

        # Should pass because CLI off overrides ini strict
        result.assert_outcomes(passed=1)

    def it_provides_bypass_instruction(self, pytester: pytest.Pytester) -> None:
        """STRICT mode error message includes bypass instruction."""
        pytester.makepyfile(
            test_bad_distribution="""
            import pytest

            @pytest.mark.large
            def test_large_one():
                assert True
            """
        )

        result = pytester.runpytest(
            '-v',
            '--test-categories-distribution-enforcement=strict',
        )

        assert result.ret != 0
        # Should tell user how to bypass (in stderr for UsageError)
        output = result.stderr.str()
        assert '--test-categories-distribution-enforcement=off' in output or 'bypass' in output.lower()


class DescribeDistributionEnforcementEdgeCases:
    """Edge case tests for distribution enforcement."""

    def it_handles_empty_test_suite(self, pytester: pytest.Pytester) -> None:
        """Handles empty test suite gracefully in strict mode."""
        pytester.makepyfile(
            test_empty="""
            # No tests defined
            pass
            """
        )

        result = pytester.runpytest(
            '-v',
            '--test-categories-distribution-enforcement=strict',
        )

        # Empty test suite has 0 tests of each category
        # Distribution validation may fail (0% small vs 80% target) or pass (no tests to validate)
        # Exit code 4 is UsageError (from distribution violation), 5 is no tests collected
        # The important thing is it doesn't crash with an unexpected exception
        assert result.ret in [0, 1, 2, 4, 5]

    def it_handles_tests_without_markers(self, pytester: pytest.Pytester) -> None:
        """Handles tests without size markers."""
        pytester.makepyfile(
            test_unmarked="""
            def test_no_marker():
                assert True
            """
        )

        result = pytester.runpytest(
            '-v',
            '--test-categories-distribution-enforcement=strict',
        )

        # Unmarked tests don't count toward distribution
        # With 0 marked tests, distribution validation may fail or pass
        # Exit code 4 is UsageError (from distribution violation)
        # The important thing is it doesn't crash with an unexpected exception
        assert result.ret in [0, 1, 2, 4, 5]
