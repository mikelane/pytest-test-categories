"""Production adapters for pytest following hexagonal architecture.

This module provides production adapters that wrap pytest objects and implement
the port interfaces. These adapters are used in real pytest runs.

The adapter pattern allows code to work with pytest objects through abstract interfaces
rather than directly depending on pytest's internal implementation.
"""

from __future__ import annotations

import warnings
from typing import (
    TYPE_CHECKING,
    cast,
)

from pytest_test_categories.distribution.stats import DistributionStats
from pytest_test_categories.types import (
    ConfigStatePort,
    OutputWriterPort,
    PluginState,
    TestItemPort,
    WarningSystemPort,
)

if TYPE_CHECKING:
    import pytest


class PytestItemAdapter(TestItemPort):
    """Production adapter that wraps pytest.Item.

    This adapter implements the TestItemPort interface by delegating to a real
    pytest.Item object. It's used in production (real pytest runs) to provide
    an abstraction layer over pytest's internal Item implementation.

    This follows the hexagonal architecture pattern where:
    - TestItemPort is the Port (abstract interface)
    - PytestItemAdapter is the Production Adapter (real implementation)
    - FakeTestItem is the Test Adapter (test double)

    Example:
        >>> item = PytestItemAdapter(pytest_item)
        >>> print(item.nodeid)
        'test_module.py::test_function'
        >>> marker = item.get_marker('small')

    """

    def __init__(self, item: pytest.Item) -> None:
        """Initialize adapter with a pytest.Item.

        Args:
            item: The pytest.Item to wrap.

        """
        self._item = item

    @property
    def nodeid(self) -> str:
        """Get the wrapped item's node ID.

        Returns:
            The test item's unique identifier.

        """
        return self._item.nodeid

    def get_marker(self, name: str) -> object | None:
        """Get a marker from the wrapped item.

        Delegates to pytest.Item.get_closest_marker() to retrieve markers
        defined on the test function, class, or module.

        Args:
            name: The marker name to retrieve.

        Returns:
            The marker object if found, None otherwise.

        """
        return self._item.get_closest_marker(name)

    def set_nodeid(self, nodeid: str) -> None:
        """Set the wrapped item's node ID.

        This modifies the internal _nodeid attribute of the pytest.Item.
        Used by the plugin to append size labels to test IDs.

        Args:
            nodeid: The new node ID to assign.

        """
        self._item._nodeid = nodeid  # noqa: SLF001


class TerminalReporterAdapter(OutputWriterPort):
    """Production adapter that wraps pytest.TerminalReporter.

    This adapter implements the OutputWriterPort interface by delegating to a real
    pytest.TerminalReporter object. It's used in production (real pytest runs) to provide
    an abstraction layer over pytest's terminal reporter implementation.

    This follows the hexagonal architecture pattern where:
    - OutputWriterPort is the Port (abstract interface)
    - TerminalReporterAdapter is the Production Adapter (real implementation)
    - StringBufferWriter is the Test Adapter (test double)

    Example:
        >>> adapter = TerminalReporterAdapter(terminalreporter)
        >>> adapter.write_section('Test Report', sep='=')
        >>> adapter.write_line('Total: 10 tests')
        >>> adapter.write_separator()

    """

    def __init__(self, reporter: pytest.TerminalReporter) -> None:
        """Initialize adapter with a pytest.TerminalReporter.

        Args:
            reporter: The pytest.TerminalReporter to wrap.

        """
        self._reporter = reporter

    def write_section(self, title: str, sep: str = '=') -> None:
        """Write a section header with title and separator.

        Delegates to pytest.TerminalReporter.section() to write a section header
        with appropriate formatting.

        Args:
            title: The section title to display.
            sep: The separator character to use (default: '=').

        """
        self._reporter.section(title, sep=sep)

    def write_line(self, message: str, **kwargs: object) -> None:
        """Write a single line of text.

        Delegates to pytest.TerminalReporter.write_line() to write a line of text
        with optional styling arguments (e.g., red=True, bold=True).

        Args:
            message: The message to write.
            **kwargs: Additional styling arguments forwarded to write_line.

        """
        self._reporter.write_line(message, **kwargs)  # type: ignore[arg-type]

    def write_separator(self, sep: str = '-') -> None:
        """Write a separator line.

        Delegates to pytest.TerminalReporter.write_sep() to write a separator line
        using the specified character.

        Args:
            sep: The separator character to use (default: '-').

        """
        self._reporter.write_sep(sep=sep)


class PytestWarningAdapter(WarningSystemPort):
    """Production adapter that wraps Python's warnings module.

    This adapter implements the WarningSystemPort interface by delegating to
    warnings.warn(). It's used in production (real pytest runs) to emit actual
    warnings through Python's warnings system.

    This follows the hexagonal architecture pattern where:
    - WarningSystemPort is the Port (abstract interface)
    - PytestWarningAdapter is the Production Adapter (real implementation)
    - FakeWarningSystem is the Test Adapter (test double)

    The adapter uses stacklevel=3 to point warnings to the caller's caller,
    which provides better context in warning messages.

    Example:
        >>> adapter = PytestWarningAdapter()
        >>> adapter.warn('This feature is deprecated', category=DeprecationWarning)

    """

    def warn(self, message: str, category: type[Warning]) -> None:
        """Emit a warning through Python's warnings system.

        Delegates to warnings.warn() with stacklevel=3 to point to the
        caller's caller for better warning context.

        Args:
            message: The warning message to emit.
            category: The warning category (e.g., UserWarning, DeprecationWarning).

        """
        warnings.warn(message, category=category, stacklevel=3)


class PytestConfigAdapter(ConfigStatePort):
    """Production adapter that wraps pytest.Config.

    This adapter implements the ConfigStatePort interface by managing state
    on a pytest.Config object. It encapsulates access to private attributes
    to eliminate noqa: SLF001 comments throughout the codebase.

    This follows the hexagonal architecture pattern where:
    - ConfigStatePort is the Port (abstract interface)
    - PytestConfigAdapter is the Production Adapter (real implementation)
    - FakeConfig is the Test Adapter (test double)

    The adapter manages the plugin state and distribution stats as attributes
    on the config object, providing a clean interface for state access.

    Example:
        >>> adapter = PytestConfigAdapter(config)
        >>> state = adapter.get_plugin_state()
        >>> adapter.set_distribution_stats(stats)
        >>> report_type = adapter.get_option('--test-size-report')

    """

    def __init__(self, config: pytest.Config) -> None:
        """Initialize adapter with a pytest.Config.

        Args:
            config: The pytest.Config to wrap.

        """
        self._config = config

    def get_plugin_state(self) -> PluginState:
        """Get or create the plugin state for the current session.

        Returns:
            The PluginState object containing all plugin session data.

        """
        if not hasattr(self._config, '_test_categories_state'):
            self._config._test_categories_state = PluginState()  # type: ignore[attr-defined]  # noqa: SLF001
        return cast('PluginState', self._config._test_categories_state)  # type: ignore[attr-defined]  # noqa: SLF001

    def set_plugin_state(self, state: PluginState) -> None:
        """Set the plugin state for the current session.

        Args:
            state: The PluginState object to store.

        """
        self._config._test_categories_state = state  # type: ignore[attr-defined]  # noqa: SLF001

    def get_distribution_stats(self) -> DistributionStats:
        """Get the distribution statistics for the current session.

        Returns:
            The DistributionStats object, or creates a default one if not set.

        """
        if not hasattr(self._config, 'distribution_stats'):
            self._config.distribution_stats = DistributionStats()  # type: ignore[attr-defined]
        return cast('DistributionStats', self._config.distribution_stats)  # type: ignore[attr-defined]

    def set_distribution_stats(self, stats: DistributionStats) -> None:
        """Set the distribution statistics for the current session.

        Args:
            stats: The DistributionStats object to store.

        """
        self._config.distribution_stats = stats  # type: ignore[attr-defined]

    def add_marker(self, marker_definition: str) -> None:
        """Add a marker definition to the configuration.

        Args:
            marker_definition: The marker definition string (e.g., 'small: mark test as small size').

        """
        self._config.addinivalue_line('markers', marker_definition)

    def get_option(self, name: str) -> object:
        """Get a command-line option value.

        Args:
            name: The option name (e.g., '--test-size-report').

        Returns:
            The option value, or None if not set.

        """
        return self._config.getoption(name)
