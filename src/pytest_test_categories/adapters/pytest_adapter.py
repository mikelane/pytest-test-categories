"""Production adapter for pytest.Item following hexagonal architecture.

This module provides the PytestItemAdapter which wraps pytest.Item and implements
the TestItemPort interface. This is the production adapter used in real pytest runs.

The adapter pattern allows code to work with test items through an abstract interface
rather than directly depending on pytest's internal implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytest_test_categories.types import TestItemPort

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
