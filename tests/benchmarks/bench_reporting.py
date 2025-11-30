"""Benchmarks for report generation.

These benchmarks measure the overhead of:
- Distribution statistics calculation
- JSON report generation
- Basic and detailed report formatting

Target: Report generation < 100ms for 10,000 tests
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from pytest_test_categories.distribution.stats import DistributionStats, TestCounts
from pytest_test_categories.json_report import JsonReport
from pytest_test_categories.reporting import TestSizeReport
from pytest_test_categories.types import TestSize

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_benchmark.fixture import BenchmarkFixture


class DescribeBenchDistributionStats:
    """Benchmarks for distribution statistics calculation."""

    @pytest.mark.medium
    def it_benchmarks_percentage_calculation(
        self,
        benchmark: BenchmarkFixture,
        distribution_with_ideal: DistributionStats,
    ) -> None:
        """Benchmark percentage calculation for 1000 tests."""

        def calculate_percentages() -> tuple[float, float, float, float]:
            percentages = distribution_with_ideal.calculate_percentages()
            return percentages.small, percentages.medium, percentages.large, percentages.xlarge

        result = benchmark(calculate_percentages)
        assert result[0] == 80.0
        assert result[1] == 15.0

    @pytest.mark.medium
    def it_benchmarks_percentage_calculation_10k_tests(
        self,
        benchmark: BenchmarkFixture,
        distribution_with_10k_tests: DistributionStats,
    ) -> None:
        """Benchmark percentage calculation for 10,000 tests."""

        def calculate_percentages() -> tuple[float, float, float, float]:
            percentages = distribution_with_10k_tests.calculate_percentages()
            return percentages.small, percentages.medium, percentages.large, percentages.xlarge

        result = benchmark(calculate_percentages)
        assert result[0] == 80.0
        assert result[1] == 15.0

    @pytest.mark.medium
    def it_benchmarks_distribution_validation(
        self,
        benchmark: BenchmarkFixture,
        distribution_with_ideal: DistributionStats,
    ) -> None:
        """Benchmark distribution validation for ideal distribution."""

        def validate_distribution() -> None:
            distribution_with_ideal.validate_distribution()

        benchmark(validate_distribution)

    @pytest.mark.medium
    def it_benchmarks_stats_creation(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark DistributionStats creation."""

        def create_stats() -> DistributionStats:
            return DistributionStats(
                counts=TestCounts(
                    small=8000,
                    medium=1500,
                    large=400,
                    xlarge=100,
                )
            )

        result = benchmark(create_stats)
        assert result.counts.small == 8000

    @pytest.mark.medium
    def it_benchmarks_update_counts(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark updating distribution stats with new counts."""
        test_size_counts = {
            TestSize.SMALL: 800,
            TestSize.MEDIUM: 150,
            TestSize.LARGE: 40,
            TestSize.XLARGE: 10,
        }

        def update_counts() -> DistributionStats:
            return DistributionStats.update_counts(test_size_counts)

        result = benchmark(update_counts)
        assert result.counts.small == 800


class DescribeBenchTestSizeReport:
    """Benchmarks for TestSizeReport operations."""

    @pytest.mark.medium
    def it_benchmarks_add_test_to_report(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark adding a single test to report."""
        report = TestSizeReport()

        def add_test() -> None:
            report.add_test('test_module.py::test_func', TestSize.SMALL, duration=0.001, outcome='passed')

        benchmark(add_test)

    @pytest.mark.medium
    def it_benchmarks_adding_1000_tests(self, benchmark: BenchmarkFixture) -> None:
        """Benchmark adding 1000 tests to report."""

        def add_1000_tests() -> TestSizeReport:
            report = TestSizeReport()
            for i in range(1000):
                size = [TestSize.SMALL, TestSize.MEDIUM, TestSize.LARGE, TestSize.XLARGE][i % 4]
                report.add_test(f'test_{i}.py::test_func', size, duration=0.01 * (i % 100), outcome='passed')
            return report

        result = benchmark(add_1000_tests)
        assert result.get_total_tests() == 1000

    @pytest.mark.medium
    def it_benchmarks_adding_10000_tests(
        self,
        benchmark: BenchmarkFixture,
        test_size_report_factory: Callable[[int], TestSizeReport],
    ) -> None:
        """Benchmark adding 10000 tests to report (target: < 100ms)."""

        def create_10k_report() -> TestSizeReport:
            return test_size_report_factory(10000)

        result = benchmark(create_10k_report)
        assert result.get_total_tests() == 10000

    @pytest.mark.medium
    def it_benchmarks_get_size_counts(
        self,
        benchmark: BenchmarkFixture,
        test_size_report_factory: Callable[[int], TestSizeReport],
    ) -> None:
        """Benchmark getting size counts from report."""
        report = test_size_report_factory(1000)

        def get_counts() -> dict[str, int]:
            return report.get_size_counts()

        result = benchmark(get_counts)
        assert sum(result.values()) == 1000

    @pytest.mark.medium
    def it_benchmarks_get_size_percentages(
        self,
        benchmark: BenchmarkFixture,
        test_size_report_factory: Callable[[int], TestSizeReport],
    ) -> None:
        """Benchmark getting size percentages from report."""
        report = test_size_report_factory(1000)

        def get_percentages() -> dict[str, float]:
            return report.get_size_percentages()

        result = benchmark(get_percentages)
        total = sum(result.values())
        assert 99.9 <= total <= 100.1


class DescribeBenchJsonReport:
    """Benchmarks for JSON report generation."""

    @pytest.mark.medium
    def it_benchmarks_json_report_creation_100_tests(
        self,
        benchmark: BenchmarkFixture,
        test_size_report_factory: Callable[[int], TestSizeReport],
    ) -> None:
        """Benchmark JSON report creation for 100 tests."""
        test_report = test_size_report_factory(100)
        stats = DistributionStats(counts=TestCounts(small=80, medium=15, large=4, xlarge=1))

        def create_json_report() -> JsonReport:
            return JsonReport.from_test_size_report(
                test_report=test_report,
                distribution_stats=stats,
                version='0.7.0',
            )

        result = benchmark(create_json_report)
        assert result.summary.total_tests == 100

    @pytest.mark.medium
    def it_benchmarks_json_report_creation_1000_tests(
        self,
        benchmark: BenchmarkFixture,
        test_size_report_factory: Callable[[int], TestSizeReport],
    ) -> None:
        """Benchmark JSON report creation for 1000 tests."""
        test_report = test_size_report_factory(1000)
        stats = DistributionStats(counts=TestCounts(small=800, medium=150, large=40, xlarge=10))

        def create_json_report() -> JsonReport:
            return JsonReport.from_test_size_report(
                test_report=test_report,
                distribution_stats=stats,
                version='0.7.0',
            )

        result = benchmark(create_json_report)
        assert result.summary.total_tests == 1000

    @pytest.mark.medium
    def it_benchmarks_json_report_creation_10000_tests(
        self,
        benchmark: BenchmarkFixture,
        test_size_report_factory: Callable[[int], TestSizeReport],
    ) -> None:
        """Benchmark JSON report creation for 10000 tests (target: < 100ms)."""
        test_report = test_size_report_factory(10000)
        stats = DistributionStats(counts=TestCounts(small=8000, medium=1500, large=400, xlarge=100))

        def create_json_report() -> JsonReport:
            return JsonReport.from_test_size_report(
                test_report=test_report,
                distribution_stats=stats,
                version='0.7.0',
            )

        result = benchmark(create_json_report)
        assert result.summary.total_tests == 10000

    @pytest.mark.medium
    def it_benchmarks_json_serialization_1000_tests(
        self,
        benchmark: BenchmarkFixture,
        test_size_report_factory: Callable[[int], TestSizeReport],
    ) -> None:
        """Benchmark JSON serialization for 1000 tests."""
        test_report = test_size_report_factory(1000)
        stats = DistributionStats(counts=TestCounts(small=800, medium=150, large=40, xlarge=10))
        json_report = JsonReport.from_test_size_report(
            test_report=test_report,
            distribution_stats=stats,
            version='0.7.0',
        )

        def serialize_report() -> str:
            return json_report.model_dump_json(indent=2)

        result = benchmark(serialize_report)
        assert len(result) > 0

    @pytest.mark.medium
    def it_benchmarks_json_serialization_10000_tests(
        self,
        benchmark: BenchmarkFixture,
        test_size_report_factory: Callable[[int], TestSizeReport],
    ) -> None:
        """Benchmark JSON serialization for 10000 tests (target: < 100ms)."""
        test_report = test_size_report_factory(10000)
        stats = DistributionStats(counts=TestCounts(small=8000, medium=1500, large=400, xlarge=100))
        json_report = JsonReport.from_test_size_report(
            test_report=test_report,
            distribution_stats=stats,
            version='0.7.0',
        )

        def serialize_report() -> str:
            return json_report.model_dump_json(indent=2)

        result = benchmark(serialize_report)
        assert len(result) > 0
