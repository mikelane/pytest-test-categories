"""Test suite distribution analysis."""

from __future__ import annotations

import pytest

from pytest_test_categories.distribution.stats import TestCounts


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


class DescribeDistributionAnalysis:
    def it_counts_tests_by_size(self, pytester: pytest.Pytester) -> None:
        """Verify that we can count how many tests exist of each size."""
        # Given a test file with known test sizes
        pytester.makepyfile(
            test_simple="""
            import pytest

            def test_get_stats(distribution_stats):
                expected_counts = {
                    'small': 1,
                    'medium': 1,
                    'large': 0,
                    'xlarge': 0,
                }
                actual_counts = distribution_stats.counts.model_dump()
                assert actual_counts == expected_counts

            @pytest.mark.small
            def test_small():
                assert True

            @pytest.mark.medium
            def test_medium():
                assert True
        """
        )

        result = pytester.runpytest('test_simple.py', '-v')

        result.stdout.fnmatch_lines(['*3 passed*'])

    def it_calculates_percentages_from_counts(self, pytester: pytest.Pytester) -> None:
        """Verify that we can calculate the percentage distribution of test sizes."""
        pytester.makepyfile(
            test_distribution="""
            from pytest_test_categories.distribution.stats import TestCounts, DistributionStats

            def test_percentages(distribution_stats):
                # Given some test counts
                counts = TestCounts(
                    small=80,    # Should be 80%
                    medium=15,   # Should be 15%
                    large=4,     # Should be 4%
                    xlarge=1     # Should be 1%
                )
                stats = DistributionStats(counts=counts)

                # When calculating percentages
                percentages = stats.calculate_percentages()

                # Then they should match expected values
                assert percentages.small == 80.00
                assert percentages.medium == 15.00
                assert percentages.large == 4.00
                assert percentages.xlarge == 1.00
            """
        )

        result = pytester.runpytest('test_distribution.py', '-vv')

        assert result.ret == 0

    def it_calculates_round_percentages_evenly_from_counts(self, pytester: pytest.Pytester) -> None:
        """Verify that percentages are calculated and rounded to 2 decimal places."""
        pytester.makepyfile(
            test_distribution="""
            from pytest_test_categories.distribution.stats import TestCounts, DistributionStats

            def test_percentages(distribution_stats):
                # Given some test counts
                counts = TestCounts(
                    small=234,    # Should be 66.67%
                    medium=78,    # Should be 22.22%
                    large=25,     # Should be 7.12%
                    xlarge=14     # Should be 3.99%
                )
                stats = DistributionStats(counts=counts)

                # When calculating percentages
                percentages = stats.calculate_percentages()

                # Then they should match expected values
                assert percentages.small == 66.67
                assert percentages.medium == 22.22
                assert percentages.large == 7.12
                assert percentages.xlarge == 3.99
            """
        )

        result = pytester.runpytest('test_distribution.py', '-vv')

        assert result.ret == 0

    def it_handles_zero_counts(self, pytester: pytest.Pytester) -> None:
        """Verify that percentage calculations handle zero counts appropriately."""
        pytester.makepyfile(
            test_zero_counts="""
            from pytest_test_categories.distribution.stats import TestCounts, DistributionStats

            def test_zero_counts(distribution_stats):
                # Given a test distribution with no tests
                counts = TestCounts()  # All counts default to 0
                stats = DistributionStats(counts=counts)

                # When calculating percentages
                percentages = stats.calculate_percentages()

                # Then all percentages should be 0
                assert percentages.small == 0.00
                assert percentages.medium == 0.00
                assert percentages.large == 0.00
                assert percentages.xlarge == 0.00
            """
        )

        result = pytester.runpytest('test_zero_counts.py', '-vv')

        assert result.ret == 0

    def it_validates_compliant_distribution(self, pytester: pytest.Pytester) -> None:
        """Verify that a test distribution within target ranges is validated successfully."""
        pytester.makepyfile(
            test_distribution="""
            from pytest_test_categories.distribution.stats import TestCounts, DistributionStats

            def test_valid_distribution(distribution_stats):
                # Given a test suite with distribution within targets
                counts = TestCounts(
                    small=80,     # 80% - within 75-85% target
                    medium=15,    # 15% - within 10-20% target
                    large=4,      # 5% combined - within 2-8% target
                    xlarge=1
                )
                stats = DistributionStats(counts=counts)

                # When validating the distribution
                stats.validate_distribution()

                # Then no exception should be raised
                assert True  # If we get here, validation passed
            """
        )

        result = pytester.runpytest('test_distribution.py', '-vv')

        assert result.ret == 0

    @pytest.mark.parametrize(
        ('counts', 'expected_error'),
        [
            pytest.param(
                TestCounts(
                    small=70,  # 70% - below target
                    medium=25,  # 25%
                    large=4,  # 5% combined
                    xlarge=1,
                ),
                'Small test percentage (70.00%) outside target range 75.00%-85.00%',
                id='small below range',
            ),
            pytest.param(
                TestCounts(
                    small=90,  # 90% - above target
                    medium=8,  # 8%
                    large=1,  # 2% combined
                    xlarge=1,
                ),
                'Small test percentage (90.00%) outside target range 75.00%-85.00%',
                id='small above range',
            ),
            pytest.param(
                TestCounts(
                    small=85,  # 85%
                    medium=8,  # 8% - below target
                    large=6,  # 7% combined
                    xlarge=1,
                ),
                'Medium test percentage (8.00%) outside target range 10.00%-20.00%',
                id='medium below range',
            ),
            pytest.param(
                TestCounts(
                    small=75,  # 75%
                    medium=22,  # 22% - above target
                    large=2,  # 3% combined
                    xlarge=1,
                ),
                'Medium test percentage (22.00%) outside target range 10.00%-20.00%',
                id='medium above range',
            ),
            pytest.param(
                TestCounts(
                    small=85,  # 85%
                    medium=14,  # 14%
                    large=1,  # 1% combined - below target
                    xlarge=0,
                ),
                'Large/XLarge test percentage (1.00%) outside target range 2.00%-8.00%',
                id='large xlarge below range',
            ),
            pytest.param(
                TestCounts(
                    small=80,  # 80%
                    medium=10,  # 10%
                    large=8,  # 10% combined - above target
                    xlarge=2,
                ),
                'Large/XLarge test percentage (10.00%) outside target range 2.00%-8.00%',
                id='large/xlarge above range',
            ),
        ],
    )
    def it_fails_when_distribution_outside_target_ranges(
        self,
        pytester: pytest.Pytester,
        counts: TestCounts,
        expected_error: str,
    ) -> None:
        """Verify that validation fails when test percentages fall outside target ranges."""
        pytester.makepyfile(
            test_distribution=f"""
            import pytest
            from pytest_test_categories.distribution.stats import TestCounts, DistributionStats

            def test_invalid_distribution():
                # Given a test suite with invalid distribution
                counts = TestCounts(
                    small={counts.small},
                    medium={counts.medium},
                    large={counts.large},
                    xlarge={counts.xlarge}
                )
                stats = DistributionStats(counts=counts)

                # When validating the distribution
                with pytest.raises(ValueError) as exc_info:
                    stats.validate_distribution()

                # Then it should fail with appropriate error message
                assert "{expected_error}" in str(exc_info.value)
            """
        )

        result = pytester.runpytest('test_distribution.py', '-vv')
        assert result.ret == 0

    def it_validates_percentages_must_sum_to_100_percent(self, pytester: pytest.Pytester) -> None:
        """Verify that test percentages must sum to 100% (unless all zero)."""
        pytester.makepyfile(
            test_percentages="""
            import pytest
            from pytest_test_categories.distribution.stats import TestPercentages

            def test_invalid_total_percentage():
                # Given percentages that don't sum to 100%
                with pytest.raises(ValueError, match='Percentages must sum to 100% .*'):
                    TestPercentages(
                        small=80.0,    # Total sums to 95%
                        medium=10.0,
                        large=3.0,
                        xlarge=2.0
                    )

                # Zero percentages are allowed
                TestPercentages(
                    small=0.0,
                    medium=0.0,
                    large=0.0,
                    xlarge=0.0
                )

                # Small rounding differences are allowed
                TestPercentages(
                    small=80.004,    # Total = 100.004%
                    medium=15.0,
                    large=3.0,
                    xlarge=2.0
                )
            """
        )

        result = pytester.runpytest('test_percentages.py', '-vv')
        assert result.ret == 0

    def it_validates_distribution_after_collection(self, pytester: pytest.Pytester) -> None:
        """Verify that the plugin validates test distribution after collection."""
        pytester.makepyfile(
            test_distribution="""
            import pytest

            @pytest.mark.small
            def test_one():
                assert True
            """
        )

        result = pytester.runpytest('-vv')

        # The pytester test itself should pass
        assert result.ret == 0
        # But it should show a warning about distribution
        result.stdout.fnmatch_lines(['*PytestWarning: Test distribution does not meet targets*'])
