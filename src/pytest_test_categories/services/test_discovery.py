"""Test discovery service for finding test size markers.

This module provides the TestDiscoveryService class that encapsulates the logic
for discovering test size markers on test items. It follows hexagonal architecture
by depending on abstract ports (TestItemPort, WarningSystemPort) rather than
concrete pytest implementation.

This service is the core of Phase 1 refactoring - extracting business logic from
plugin.py into a testable service that depends on ports (interfaces) rather than
concrete pytest implementations.

Design:
- Accepts WarningSystemPort via dependency injection
- Works with TestItemPort abstraction (not pytest.Item directly)
- Tracks warned tests to avoid duplicate warnings
- Returns TestSize enum or None
- Raises UsageError for invalid configuration (multiple markers)

Example:
    >>> from pytest_test_categories.adapters.pytest_adapter import (
    ...     PytestItemAdapter,
    ...     PytestWarningAdapter,
    ... )
    >>> warning_system = PytestWarningAdapter()
    >>> service = TestDiscoveryService(warning_system=warning_system)
    >>> test_item = PytestItemAdapter(pytest_item)
    >>> size = service.find_test_size(test_item)
    >>> if size:
    ...     print(f'Test is {size.name} size')

"""

from __future__ import annotations

import pytest

from pytest_test_categories.types import (
    TestItemPort,
    TestSize,
    WarningSystemPort,
)

# Error message for multiple size markers
MULTIPLE_MARKERS_ERROR = 'Test cannot have multiple size markers: {}'


class TestDiscoveryService:
    """Service for discovering test size markers on test items.

    This service encapsulates the logic for finding test size markers,
    validating that tests have exactly one size marker, and warning about
    missing markers. It follows hexagonal architecture by depending on
    abstract ports rather than concrete pytest implementations.

    The service tracks warned tests to avoid duplicate warnings when the
    same test is processed multiple times (e.g., during collection).

    Attributes:
        _warning_system: Port for emitting warnings.
        _warned_tests: Set of test node IDs that have already been warned about.

    Example:
        >>> from tests._fixtures.test_item import FakeTestItem
        >>> from tests._fixtures.warning_system import FakeWarningSystem
        >>> warning_system = FakeWarningSystem()
        >>> service = TestDiscoveryService(warning_system=warning_system)
        >>> item = FakeTestItem(nodeid='test.py::test_func', markers={'small': object()})
        >>> size = service.find_test_size(item)
        >>> assert size == TestSize.SMALL

    """

    def __init__(self, warning_system: WarningSystemPort) -> None:
        """Initialize the test discovery service.

        Args:
            warning_system: Port for emitting warnings about missing or invalid markers.

        """
        self._warning_system = warning_system
        self._warned_tests: set[str] = set()

    def find_test_size(self, item: TestItemPort) -> TestSize | None:
        """Find the test size marker on a test item.

        Searches for size markers (small, medium, large, xlarge) on the test item.
        Returns the size if exactly one is found, warns and returns None if none are
        found, and raises UsageError if multiple size markers are found.

        The service tracks warned tests by their node ID to avoid duplicate warnings
        when the same test is processed multiple times.

        Args:
            item: The test item to inspect for size markers.

        Returns:
            The TestSize enum value if exactly one size marker is found, None otherwise.

        Raises:
            pytest.UsageError: If the test has multiple size markers.

        Example:
            >>> # Test with one marker
            >>> item = FakeTestItem(nodeid='test.py::test_one', markers={'small': object()})
            >>> size = service.find_test_size(item)
            >>> assert size == TestSize.SMALL

            >>> # Test with no markers (warns once)
            >>> item = FakeTestItem(nodeid='test.py::test_none')
            >>> size = service.find_test_size(item)
            >>> assert size is None

            >>> # Test with multiple markers (raises)
            >>> item = FakeTestItem(
            ...     nodeid='test.py::test_multi',
            ...     markers={'small': object(), 'medium': object()}
            ... )
            >>> service.find_test_size(item)  # Raises UsageError

        """
        # Find all size markers on the test item
        found_sizes = [size for size in TestSize if item.get_marker(size.marker_name)]

        # No size markers found - warn and return None
        if not found_sizes:
            if item.nodeid not in self._warned_tests:
                self._warning_system.warn(
                    f'Test has no size marker: {item.nodeid}',
                    category=pytest.PytestWarning,
                )
                self._warned_tests.add(item.nodeid)
            return None

        # Multiple size markers found - raise error
        if len(found_sizes) > 1:
            marker_names = ', '.join(size.marker_name for size in found_sizes)
            raise pytest.UsageError(MULTIPLE_MARKERS_ERROR.format(marker_names))

        # Exactly one size marker found - return it
        return found_sizes[0]
