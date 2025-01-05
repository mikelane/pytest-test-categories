"""Core plugin implementation."""

from __future__ import annotations

import warnings
from collections import defaultdict
from typing import (
    TYPE_CHECKING,
    Final,
)

import pytest
from pydantic import (
    BaseModel,
    ConfigDict,
)

from pytest_test_categories import timing
from pytest_test_categories.distribution.stats import DistributionStats
from pytest_test_categories.types import (
    TestSize,
    TestTimer,
)

if TYPE_CHECKING:
    from collections.abc import Generator


class TestCategories(BaseModel):
    """Test categories plugin."""

    MULTIPLE_MARKERS_ERROR: Final[str] = 'Test cannot have multiple size markers: {}'
    DISTRIBUTION_WARNING: Final[str] = 'Test distribution does not meet targets: {}'
    active: bool = True
    timer: TestTimer | None = None
    distribution_stats: DistributionStats = DistributionStats()
    model_config = ConfigDict(frozen=True)

    def _count_tests_by_size(self, items: list[pytest.Item]) -> dict[str, int]:
        """Count the number of tests in each size category.

        Args:
            items: List of test items to count.

        Returns:
            Dictionary mapping size marker names to counts.

        """
        counts = defaultdict(int)
        for item in items:
            for size in TestSize:
                if item.get_closest_marker(size.marker_name):
                    counts[size.marker_name] += 1
                    break
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

        if len(found_sizes) > 1:
            raise pytest.UsageError(self.MULTIPLE_MARKERS_ERROR.format(', '.join(found_sizes)))

        outcome = yield
        report = outcome.get_result()

        if report.when != 'call':
            return

        test_size = next(
            (size for size in TestSize if item.get_closest_marker(size.marker_name)),
            None,
        )
        if not test_size:
            return

        report.nodeid = f'{report.nodeid} {test_size.label}'

        if not self.timer or not report.passed:
            return

        timing.validate(test_size, self.timer.duration())


def pytest_configure(config: pytest.Config) -> None:
    """Register the plugin."""
    config.pluginmanager.register(TestCategories())  # pragma: no cover
