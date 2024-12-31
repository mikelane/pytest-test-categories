"""Core plugin implementation."""

from __future__ import annotations

import warnings
from typing import (
    TYPE_CHECKING,
    Final,
)

import pytest
from pydantic import (
    BaseModel,
    ConfigDict,
)

from pytest_test_categories.types import (
    TestSize,
    TestTimer,
    TimingViolationError,
)

if TYPE_CHECKING:
    from collections.abc import Generator


class TestCategories(BaseModel):
    """Test categories plugin."""

    MULTIPLE_MARKERS_ERROR: Final[str] = 'Test cannot have multiple size markers: {}'
    active: bool = True
    timer: TestTimer | None = None

    model_config = ConfigDict(frozen=True)

    def pytest_configure(self, config: pytest.Config) -> None:
        """Register the plugin and markers."""
        for size in TestSize:
            config.addinivalue_line('markers', f'{size.marker_name}: {size.description}')

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
        """Modify test report to show size category."""
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

        duration = self.timer.duration()
        if test_size == TestSize.SMALL and duration > 1.0:
            msg = f'SMALL test exceeded time limit of 1.0 seconds ' f'(took {duration:.1f} seconds)'
            raise TimingViolationError(msg)


def pytest_configure(config: pytest.Config) -> None:
    """Register the plugin."""
    config.pluginmanager.register(TestCategories())
