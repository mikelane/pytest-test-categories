"""Core plugin implementation."""

from __future__ import annotations

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
