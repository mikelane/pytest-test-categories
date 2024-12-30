"""Core plugin implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


class TestCategories:
    """Test categories plugin."""

    def __init__(self) -> None:
        """Initialize the test categories plugin."""
        self.active = True

    def pytest_configure(self, config: pytest.Config) -> None:
        """Register the plugin and markers."""
        config.addinivalue_line(
            'markers',
            'small: mark test as SMALL size',
        )

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item: pytest.Item) -> Generator[None, None, None]:
        """Modify test report to show size category."""
        outcome = yield
        report = outcome.get_result()
        if report.when == 'call' and item.get_closest_marker('small'):
            report.nodeid = f'{report.nodeid} [SMALL]'


def pytest_configure(config: pytest.Config) -> None:
    """Register the plugin."""
    config.pluginmanager.register(TestCategories())
