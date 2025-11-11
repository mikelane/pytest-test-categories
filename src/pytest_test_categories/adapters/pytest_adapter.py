"""Production adapters for pytest following hexagonal architecture.

This module provides production adapters that wrap pytest objects and implement
the port interfaces. These adapters are used in real pytest runs.

The adapter pattern allows code to work with pytest objects through abstract interfaces
rather than directly depending on pytest's internal implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytest_test_categories.types import (
    OutputWriterPort,
    TestItemPort,
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
        self._reporter.write_line(message, **kwargs)

    def write_separator(self, sep: str = '-') -> None:
        """Write a separator line.

        Delegates to pytest.TerminalReporter.write_sep() to write a separator line
        using the specified character.

        Args:
            sep: The separator character to use (default: '-').

        """
        self._reporter.write_sep(sep=sep)
