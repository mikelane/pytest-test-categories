"""Test suite distribution analysis."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def conftest_file(pytester: pytest.Pytester) -> None:
    """Create a conftest file with the test categories plugin registered."""
    pytester.makeconftest("""
        import pytest
        from pytest_test_categories.plugin import TestCategories
        from pytest_test_categories.distribution.stats import DistributionStats

        def pytest_configure(config):
            plugin = TestCategories()
            config.pluginmanager.register(plugin)

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

        result = pytester.runpytest('test_distribution.py', '-v')

        # Test should fail since calculate_percentages() isn't implemented
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
