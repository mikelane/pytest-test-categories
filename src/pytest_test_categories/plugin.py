"""Core plugin implementation."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

import pytest

from pytest_test_categories.types import TestSize

if TYPE_CHECKING:
    from collections.abc import Generator


class TestCategories:
    """Test categories plugin."""

    MULTIPLE_MARKERS_ERROR = 'Test cannot have multiple size markers: {}'

    def __init__(self) -> None:
        """Initialize the test categories plugin."""
        self.active = True

    def pytest_configure(self, config: pytest.Config) -> None:
        """Register the plugin and markers."""
        for size in TestSize:
            config.addinivalue_line('markers', f'{size.marker_name}: {size.description}')

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

        if report.when == 'call':
            for size in TestSize:
                if item.get_closest_marker(size.marker_name):
                    report.nodeid = f'{report.nodeid} {size.label}'
                    break


def pytest_configure(config: pytest.Config) -> None:
    """Register the plugin."""
    config.pluginmanager.register(TestCategories())
