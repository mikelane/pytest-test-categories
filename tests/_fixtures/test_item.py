"""Fake test item implementation for testing.

This module provides FakeTestItem, a controllable test double that implements
the TestItemPort interface. It's used in tests as a substitute for pytest.Item
to enable deterministic testing without pytest's internal complexity.

The FakeTestItem follows hexagonal architecture principles:
- Implements the TestItemPort interface
- Provides controllable nodeid and markers
- Used in tests as a substitute for PytestItemAdapter
- Enables testing behavior without implementation details
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytest_test_categories.types import TestItemPort

if TYPE_CHECKING:
    from typing import Any


class FakeTestItem(TestItemPort):
    """Controllable test item adapter for testing.

    This is a test double that allows tests to control test item properties
    explicitly rather than depending on pytest's internal Item implementation.
    This eliminates test complexity and makes tests deterministic.

    The FakeTestItem follows hexagonal architecture principles:
    - Implements the TestItemPort interface
    - Provides controllable nodeid and markers configuration
    - Used in tests as a substitute for PytestItemAdapter
    - Enables testing behavior without pytest dependencies

    Example:
        >>> item = FakeTestItem(nodeid='test_module.py::test_function')
        >>> print(item.nodeid)
        'test_module.py::test_function'
        >>> marker = item.get_marker('small')
        >>> # marker is None unless configured

        >>> class FakeMarker:
        ...     name = 'small'
        >>> item = FakeTestItem(
        ...     nodeid='test.py::func',
        ...     markers={'small': FakeMarker()}
        ... )
        >>> marker = item.get_marker('small')
        >>> print(marker.name)
        'small'

    """

    def __init__(self, nodeid: str, markers: dict[str, Any] | None = None) -> None:
        """Initialize fake test item with configurable properties.

        Args:
            nodeid: The test node ID string.
            markers: Optional dictionary mapping marker names to marker objects.

        """
        self._nodeid = nodeid
        self._markers = markers or {}

    @property
    def nodeid(self) -> str:
        """Get the test item's node ID.

        Returns:
            The configured node ID string.

        """
        return self._nodeid

    def get_marker(self, name: str) -> object | None:
        """Get a marker by name from the configured markers.

        Args:
            name: The marker name to retrieve.

        Returns:
            The marker object if configured, None otherwise.

        """
        return self._markers.get(name)

    def set_nodeid(self, nodeid: str) -> None:
        """Set the test item's node ID.

        Args:
            nodeid: The new node ID to assign.

        """
        self._nodeid = nodeid
