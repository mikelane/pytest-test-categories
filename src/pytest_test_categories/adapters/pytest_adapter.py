"""Production adapters for pytest following hexagonal architecture.

This module provides production adapters that wrap pytest objects and implement
the port interfaces. These adapters are used in real pytest runs.

The adapter pattern allows code to work with pytest objects through abstract interfaces
rather than directly depending on pytest's internal implementation.
"""

from __future__ import annotations

import warnings
from typing import cast

import pytest

from pytest_test_categories.distribution.stats import DistributionStats
from pytest_test_categories.types import (
    ConfigStatePort,
    OutputWriterPort,
    PluginState,
    TestItemPort,
    WarningSystemPort,
)


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

    def get_marker_kwargs(self, name: str) -> dict[str, object]:
        """Get keyword arguments from a marker.

        Retrieves the kwargs dict from a pytest marker. This is useful for
        extracting configuration options from markers like
        @pytest.mark.medium(allow_external_systems=True).

        Args:
            name: The marker name to retrieve kwargs from.

        Returns:
            A dictionary of keyword arguments, or empty dict if marker not found.

        """
        marker = self._item.get_closest_marker(name)
        if marker is None:
            return {}
        return dict(marker.kwargs)

    def get_class_hierarchy(self) -> list[tuple[str, dict[str, object]]]:
        """Get the class hierarchy with markers for conflict detection.

        Inspects the test item's class and its MRO (Method Resolution Order)
        to find all size markers defined at each level. This enables detection
        of marker inheritance conflicts.

        Returns:
            List of tuples containing (class_name, markers) for each class
            in the hierarchy. Returns empty list for function-level tests.

        """
        # Get the parent class of the test function (if any)
        parent = getattr(self._item, 'cls', None)
        if parent is None:
            return []

        hierarchy: list[tuple[str, dict[str, object]]] = []
        size_marker_names = {'small', 'medium', 'large', 'xlarge'}

        # Walk the MRO to find markers at each level
        for cls in parent.__mro__:
            if cls is object:
                continue

            # Check for pytestmark attribute on this specific class (not inherited)
            class_markers: dict[str, object] = {}
            if 'pytestmark' in cls.__dict__:
                pytestmark = cls.__dict__['pytestmark']
                # pytestmark can be a single Mark or a list of Marks
                marks = [pytestmark] if not isinstance(pytestmark, list) else pytestmark
                for mark in marks:
                    if hasattr(mark, 'name') and mark.name in size_marker_names:
                        class_markers[mark.name] = mark

            hierarchy.append((cls.__name__, class_markers))

        return hierarchy

    def get_method_markers(self) -> dict[str, object]:
        """Get markers applied directly to the test method.

        Retrieves markers defined directly on the test function itself,
        not inherited from the class or module. This enables detection
        of method-level marker conflicts with class-level markers.

        Returns:
            Dictionary of marker names to marker objects for method-level markers.

        """
        size_marker_names = {'small', 'medium', 'large', 'xlarge'}
        method_markers: dict[str, object] = {}

        # Get the actual test function
        func = getattr(self._item, 'obj', None)
        if func is None:
            return {}

        # Check for pytestmark on the function itself
        pytestmark = getattr(func, 'pytestmark', None)
        if pytestmark is not None:
            marks = [pytestmark] if not isinstance(pytestmark, list) else pytestmark
            for mark in marks:
                if hasattr(mark, 'name') and mark.name in size_marker_names:
                    method_markers[mark.name] = mark

        return method_markers


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

    def warn(self, message: str, category: type[Warning] | None = None) -> None:
        """Emit a warning through Python's warnings system.

        Delegates to warnings.warn() with stacklevel=2 to point to the
        caller for better warning context. Uses pytest.PytestWarning by default
        to match pytest's warning system.

        Args:
            message: The warning message to emit.
            category: The warning category (default: pytest.PytestWarning if None).

        """
        actual_category = category if category is not None else pytest.PytestWarning
        warnings.warn(message, category=actual_category, stacklevel=2)


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
