"""Core plugin implementation."""

from __future__ import annotations

import warnings
from collections import defaultdict
from typing import (
    TYPE_CHECKING,
    Final,
    NamedTuple,
)

import pytest
from pydantic import (
    BaseModel,
    ConfigDict,
)

from pytest_test_categories import timing
from pytest_test_categories.distribution.stats import (
    DistributionStats,
    TestPercentages,
)
from pytest_test_categories.types import (
    TestSize,
    TestTimer,
)

if TYPE_CHECKING:
    from collections.abc import (
        Generator,
        Iterator,
    )


class SizedItem(NamedTuple):
    """Test item with its associated size."""

    size: TestSize
    item: pytest.Item


class TestCategories(BaseModel):
    """Test categories plugin."""

    MULTIPLE_MARKERS_ERROR: Final[str] = 'Test cannot have multiple size markers: {}'
    DISTRIBUTION_WARNING: Final[str] = 'Test distribution does not meet targets: {}'
    MAX_LARGE_XLARGE_PCT: Final[float] = 8.0
    MIN_SMALL_PCT: Final[float] = 75.0
    MAX_MEDIUM_PCT: Final[float] = 20.0
    CRITICAL_SMALL_PCT: Final[float] = 50.0  # Threshold for severe warning
    active: bool = True
    timer: TestTimer | None = None
    distribution_stats: DistributionStats = DistributionStats()
    model_config = ConfigDict(frozen=True)

    def _iter_sized_items(self, items: list[pytest.Item]) -> Iterator[SizedItem]:
        """Iterate through test items yielding those with size markers.

        Args:
            items: List of test items to process.

        Yields:
            Pairs of (TestSize, Item) for items with size markers.

        """
        for item in items:
            found_sizes = [size for size in TestSize if item.get_closest_marker(size.marker_name)]

            if not found_sizes:
                warnings.warn(
                    f'Test has no size marker: {item.nodeid}',
                    pytest.PytestWarning,
                    stacklevel=2,
                )
                continue

            if len(found_sizes) > 1:
                raise pytest.UsageError(
                    self.MULTIPLE_MARKERS_ERROR.format(', '.join(size.marker_name for size in found_sizes))
                )

            yield SizedItem(found_sizes[0], item)

    def _count_tests_by_size(self, items: list[pytest.Item]) -> dict[str, int]:
        """Count the number of tests in each size category.

        Args:
            items: List of test items to count.

        Returns:
            Dictionary mapping size marker names to counts.

        """
        counts = defaultdict(int)
        for sized_item in self._iter_sized_items(items):
            counts[sized_item.size.marker_name] += 1
        return counts

    def pytest_configure(self, config: pytest.Config) -> None:
        """Register the plugin and markers."""
        if not hasattr(config, 'distribution_stats'):
            config.distribution_stats = self.distribution_stats

        for size in TestSize:
            config.addinivalue_line('markers', f'{size.marker_name}: {size.description}')

    @pytest.hookimpl(tryfirst=True)
    def pytest_collection_modifyitems(self, config: pytest.Config, items: list[pytest.Item]) -> None:
        """Count tests by size during collection."""
        config.distribution_stats = DistributionStats.update_counts(counts=self._count_tests_by_size(items))

        for sized_item in self._iter_sized_items(items):
            sized_item.item._nodeid = f'{sized_item.item._nodeid} {sized_item.size.label}'  # noqa: SLF001

    @pytest.hookimpl
    def pytest_collection_finish(self, session: pytest.Session) -> None:
        """Validate test distribution after collection."""
        try:
            session.config.distribution_stats.validate_distribution()
        except ValueError as e:
            warnings.warn(self.DISTRIBUTION_WARNING.format(e), pytest.PytestWarning, stacklevel=2)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_protocol(self, item: pytest.Item) -> Generator[None, None, None]:  # noqa: ARG002
        """Track test timing."""
        if self.timer is not None:
            self.timer.start()

        yield

        if self.timer is not None:
            self.timer.stop()

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item: pytest.Item) -> Generator[None, None, None]:
        """Modify test report to show size category and validate timing."""
        found_sizes = [size.marker_name for size in TestSize if item.get_closest_marker(size.marker_name)]

        if not found_sizes:
            warnings.warn(
                f'Test has no size marker: {item.nodeid}',
                pytest.PytestWarning,
                stacklevel=2,
            )

        outcome = yield
        report = outcome.get_result()

        test_size = next(
            (size for size in TestSize if item.get_closest_marker(size.marker_name)),
            None,
        )
        if test_size and report.when == 'call' and self.timer and report.passed:
            timing.validate(test_size, self.timer.duration())

    @staticmethod
    def _pluralize_test(count: int) -> str:
        """Return 'test' or 'tests' based on count."""
        return 'test' if count == 1 else 'tests'

    def _format_distribution_row(self, size: str, count: int, percentage: float) -> str:
        """Format a single row of the distribution table.

        Args:
            size: The test size category name
            count: Number of tests in this category
            percentage: Percentage of tests in this category

        Returns:
            Formatted row string

        """
        row_format = '      {:<8} {:>3} {:<5} ({:.2f}%)'
        return row_format.format(size, count, self._pluralize_test(count), percentage)

    def _get_status_message(self, percentages: TestPercentages) -> list[str]:
        """Get the status message based on distribution percentages.

        Args:
            percentages: The current test distribution percentages

        Returns:
            List of lines to display

        """
        large_xlarge_percentage = percentages.large + percentages.xlarge

        # Check for most severe issues first
        if large_xlarge_percentage > self.MAX_LARGE_XLARGE_PCT:
            return [
                'Status: Warning! Distribution needs improvement:',
                f'  Large/XLarge tests are {large_xlarge_percentage:.0f}% of the suite (target: 2-8%)',
                '  This indicates too many complex tests. Consider:',
                '  • Breaking large tests into smaller focused tests',
                '  • Moving test setup into fixtures',
                '  • Using test parameterization for repeated scenarios',
            ]

        # If small tests are way below target (>25% below minimum), that's the primary issue
        if percentages.small < self.CRITICAL_SMALL_PCT:
            return [
                'Status: Warning! Distribution needs improvement:',
                f'  Small tests are only {percentages.small:.2f}% of the suite (target: 75-85%)',
                '  This indicates tests may be too complex. Consider:',
                '  • Breaking down medium tests into smaller units',
                '  • Testing more specific behaviors individually',
                '  • Moving complex setup into fixtures or helpers',
            ]

        # If medium tests are significantly over target or small tests moderately under, report the worse deviation
        small_deviation = self.MIN_SMALL_PCT - percentages.small if percentages.small < self.MIN_SMALL_PCT else 0
        medium_deviation = percentages.medium - self.MAX_MEDIUM_PCT if percentages.medium > self.MAX_MEDIUM_PCT else 0

        if medium_deviation > small_deviation:
            return [
                'Status: Warning! Distribution needs improvement:',
                f'  Medium tests are {percentages.medium:.2f}% of the suite (target: 10-20%)',
                '  This suggests test complexity is creeping up. Consider:',
                '  • Identifying shared setup that could be simplified',
                '  • Looking for tests that could be split into smaller units',
                '  • Reviewing test dependencies and fixture usage',
            ]
        if small_deviation > 0:
            return [
                'Status: Warning! Distribution needs improvement:',
                f'  Small tests are only {percentages.small:.2f}% of the suite (target: 75-85%)',
                '  This indicates tests may be too complex. Consider:',
                '  • Breaking down medium tests into smaller units',
                '  • Testing more specific behaviors individually',
                '  • Moving complex setup into fixtures or helpers',
            ]

        return ['Status: Great job! Your test distribution is on track.']

    @pytest.hookimpl
    def pytest_terminal_summary(self, terminalreporter: pytest.TerminalReporter) -> None:
        """Add test size distribution summary to the terminal report."""
        distribution_stats = terminalreporter.config.distribution_stats
        counts = distribution_stats.counts
        percentages = distribution_stats.calculate_percentages()

        terminalreporter.section('Test Suite Distribution Summary', sep='=')
        terminalreporter.write_line('    Test Size Distribution:')

        for size, count, percentage in [
            ('Small', counts.small, percentages.small),
            ('Medium', counts.medium, percentages.medium),
            ('Large', counts.large, percentages.large),
            ('XLarge', counts.xlarge, percentages.xlarge),
        ]:
            terminalreporter.write_line(self._format_distribution_row(size, count, percentage))

        # Write status message
        terminalreporter.write_line('')
        for line in self._get_status_message(percentages):
            terminalreporter.write_line(line)

        terminalreporter.write_sep('=')


def pytest_configure(config: pytest.Config) -> None:
    """Register the plugin."""
    config.pluginmanager.register(TestCategories())  # pragma: no cover
