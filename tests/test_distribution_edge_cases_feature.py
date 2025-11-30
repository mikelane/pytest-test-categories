"""Test distribution validation edge cases and boundary conditions."""

from __future__ import annotations

import pytest


@pytest.mark.medium  # pytester creates subprocesses which adds overhead
class DescribeDistributionEdgeCases:
    """Test edge cases and boundary conditions for distribution validation."""

    def it_accepts_distribution_at_lower_boundary_small_75_percent(self, pytester: pytest.Pytester) -> None:
        """It accepts exactly 75% small tests (lower boundary)."""
        # Given a test suite with exactly 75% small tests (lower boundary of 75-85% target)
        # 75% small, 20% medium, 5% large/xlarge = 15 small, 4 medium, 1 large (20 total)
        pytester.makepyfile(
            test_boundary="""
            import pytest

            @pytest.mark.small
            def test_s1(): pass
            @pytest.mark.small
            def test_s2(): pass
            @pytest.mark.small
            def test_s3(): pass
            @pytest.mark.small
            def test_s4(): pass
            @pytest.mark.small
            def test_s5(): pass
            @pytest.mark.small
            def test_s6(): pass
            @pytest.mark.small
            def test_s7(): pass
            @pytest.mark.small
            def test_s8(): pass
            @pytest.mark.small
            def test_s9(): pass
            @pytest.mark.small
            def test_s10(): pass
            @pytest.mark.small
            def test_s11(): pass
            @pytest.mark.small
            def test_s12(): pass
            @pytest.mark.small
            def test_s13(): pass
            @pytest.mark.small
            def test_s14(): pass
            @pytest.mark.small
            def test_s15(): pass

            @pytest.mark.medium
            def test_m1(): pass
            @pytest.mark.medium
            def test_m2(): pass
            @pytest.mark.medium
            def test_m3(): pass
            @pytest.mark.medium
            def test_m4(): pass

            @pytest.mark.large
            def test_l1(): pass
            """
        )

        # When running pytest
        result = pytester.runpytest('-v')

        # Then all tests should pass and no distribution warnings should appear
        result.assert_outcomes(passed=20)
        # Should not have distribution warning since distribution is within all targets
        assert result.ret == 0

    def it_accepts_distribution_at_upper_boundary_small_85_percent(self, pytester: pytest.Pytester) -> None:
        """It accepts exactly 85% small tests (upper boundary)."""
        # Given a test suite with exactly 85% small tests (upper boundary of 75-85% target)
        # 85% small, 10% medium, 5% large/xlarge = 17 small, 2 medium, 1 large (20 total)
        pytester.makepyfile(
            test_boundary="""
            import pytest

            @pytest.mark.small
            def test_s1(): pass
            @pytest.mark.small
            def test_s2(): pass
            @pytest.mark.small
            def test_s3(): pass
            @pytest.mark.small
            def test_s4(): pass
            @pytest.mark.small
            def test_s5(): pass
            @pytest.mark.small
            def test_s6(): pass
            @pytest.mark.small
            def test_s7(): pass
            @pytest.mark.small
            def test_s8(): pass
            @pytest.mark.small
            def test_s9(): pass
            @pytest.mark.small
            def test_s10(): pass
            @pytest.mark.small
            def test_s11(): pass
            @pytest.mark.small
            def test_s12(): pass
            @pytest.mark.small
            def test_s13(): pass
            @pytest.mark.small
            def test_s14(): pass
            @pytest.mark.small
            def test_s15(): pass
            @pytest.mark.small
            def test_s16(): pass
            @pytest.mark.small
            def test_s17(): pass

            @pytest.mark.medium
            def test_m1(): pass
            @pytest.mark.medium
            def test_m2(): pass

            @pytest.mark.large
            def test_l1(): pass
            """
        )

        # When running pytest
        result = pytester.runpytest('-v')

        # Then all tests should pass and no distribution warnings should appear
        result.assert_outcomes(passed=20)
        assert result.ret == 0

    def it_rejects_distribution_just_below_lower_boundary_small_74_percent(self, pytester: pytest.Pytester) -> None:
        """It rejects 74% small tests (just below 75% lower boundary)."""
        # Given a test suite with 74% small tests (just below 75% boundary)
        # 100 tests: 74 small, 20 medium, 6 large
        small_tests = '\n            '.join(
            [f'@pytest.mark.small\n            def test_s{i}(): pass' for i in range(1, 75)]
        )
        medium_tests = '\n            '.join(
            [f'@pytest.mark.medium\n            def test_m{i}(): pass' for i in range(1, 21)]
        )
        large_tests = '\n            '.join(
            [f'@pytest.mark.large\n            def test_l{i}(): pass' for i in range(1, 7)]
        )

        pytester.makepyfile(
            test_boundary=f"""
            import pytest

            {small_tests}

            {medium_tests}

            {large_tests}
            """
        )

        # When running pytest (with distribution enforcement enabled)
        result = pytester.runpytest('-v', '--test-categories-distribution-enforcement=warn')

        # Then it should show a distribution warning
        result.assert_outcomes(passed=100)
        result.stdout.fnmatch_lines(['*PytestWarning: *TC007* Test distribution does not meet targets*'])

    def it_accepts_perfect_80_15_5_distribution(self, pytester: pytest.Pytester) -> None:
        """It accepts the ideal 80% small, 15% medium, 5% large/xlarge distribution."""
        # Given a test suite with perfect distribution
        # 100 tests: 80 small, 15 medium, 5 large
        small_tests = '\n            '.join(
            [f'@pytest.mark.small\n            def test_s{i}(): pass' for i in range(1, 81)]
        )
        medium_tests = '\n            '.join(
            [f'@pytest.mark.medium\n            def test_m{i}(): pass' for i in range(1, 16)]
        )
        large_tests = '\n            '.join(
            [f'@pytest.mark.large\n            def test_l{i}(): pass' for i in range(1, 6)]
        )

        pytester.makepyfile(
            test_distribution=f"""
            import pytest

            {small_tests}

            {medium_tests}

            {large_tests}
            """
        )

        # When running pytest
        result = pytester.runpytest('-v')

        # Then all tests should pass with perfect distribution message
        result.assert_outcomes(passed=100)
        result.stdout.fnmatch_lines(['*Great job! Your test distribution is on track*'])
        assert result.ret == 0

    def it_accepts_distribution_at_large_xlarge_upper_boundary_8_percent(self, pytester: pytest.Pytester) -> None:
        """It accepts exactly 8% large/xlarge tests (upper boundary)."""
        # Given a test suite with exactly 8% large/xlarge (upper boundary of 2-8% target)
        # 100 tests: 80 small, 12 medium, 8 large
        small_tests = '\n            '.join(
            [f'@pytest.mark.small\n            def test_s{i}(): pass' for i in range(1, 81)]
        )
        medium_tests = '\n            '.join(
            [f'@pytest.mark.medium\n            def test_m{i}(): pass' for i in range(1, 13)]
        )
        large_tests = '\n            '.join(
            [f'@pytest.mark.large\n            def test_l{i}(): pass' for i in range(1, 9)]
        )

        pytester.makepyfile(
            test_boundary=f"""
            import pytest

            {small_tests}

            {medium_tests}

            {large_tests}
            """
        )

        # When running pytest
        result = pytester.runpytest('-v')

        # Then all tests should pass without warnings
        result.assert_outcomes(passed=100)
        assert result.ret == 0

    def it_rejects_distribution_just_above_large_xlarge_upper_boundary_9_percent(
        self, pytester: pytest.Pytester
    ) -> None:
        """It rejects 9% large/xlarge tests (just above 8% upper boundary)."""
        # Given a test suite with 9% large/xlarge (just above 8% boundary)
        # 100 tests: 80 small, 11 medium, 9 large
        small_tests = '\n            '.join(
            [f'@pytest.mark.small\n            def test_s{i}(): pass' for i in range(1, 81)]
        )
        medium_tests = '\n            '.join(
            [f'@pytest.mark.medium\n            def test_m{i}(): pass' for i in range(1, 12)]
        )
        large_tests = '\n            '.join(
            [f'@pytest.mark.large\n            def test_l{i}(): pass' for i in range(1, 10)]
        )

        pytester.makepyfile(
            test_boundary=f"""
            import pytest

            {small_tests}

            {medium_tests}

            {large_tests}
            """
        )

        # When running pytest (with distribution enforcement enabled)
        result = pytester.runpytest('-v', '--test-categories-distribution-enforcement=warn')

        # Then it should show a distribution warning
        result.assert_outcomes(passed=100)
        result.stdout.fnmatch_lines(['*PytestWarning: *TC007* Test distribution does not meet targets*'])
        result.stdout.fnmatch_lines(['*Large/XLarge tests are 9*% of the suite*'])
