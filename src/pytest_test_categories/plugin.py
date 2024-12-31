"""Core plugin implementation."""

from __future__ import annotations

import warnings
from enum import (
    Enum,
    auto,
)
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


class TestSize(Enum):
    """Test size categories."""

    SMALL = auto()
    MEDIUM = auto()
    LARGE = auto()
    XLARGE = auto()

    @property
    def marker_name(self) -> str:
        """Get the pytest marker name for this size."""
        return self.name.lower()

    @property
    def description(self) -> str:
        """Get the description for this test size marker."""
        return f'mark test as {self.name} size'

    @property
    def label(self) -> str:
        """Get the label to show in test output."""
        return f'[{self.name}]'


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
