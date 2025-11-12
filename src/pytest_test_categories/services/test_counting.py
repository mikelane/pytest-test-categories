"""Test counting service for pytest-test-categories.

This module provides a service for counting tests by size category following
hexagonal architecture principles. It operates on test items through a minimal
protocol interface, making it independent of pytest infrastructure.
"""

from __future__ import annotations

from collections import defaultdict
from typing import (
    TYPE_CHECKING,
    Protocol,
)

from pytest_test_categories.distribution.stats import (
    DistributionStats,
    TestCounts,
)
from pytest_test_categories.types import TestSize

if TYPE_CHECKING:
    from collections.abc import Iterable


class TestItemProtocol(Protocol):
    """Minimal protocol for test items.

    This protocol defines the minimal interface needed for test counting,
    allowing the service to work with any object that has these methods
    without depending on pytest.Item.
    """

    nodeid: str

    def get_closest_marker(self, marker_name: str) -> object | None:
        """Get the closest marker with the given name.

        Args:
            marker_name: The marker name to search for

        Returns:
            Marker object if found, None otherwise

        """
        ...


class WarningSystemProtocol(Protocol):
    """Protocol for warning systems.

    This allows the service to emit warnings without depending on
    pytest's warning system.
    """

    def warn(self, message: str) -> None:
        """Emit a warning message.

        Args:
            message: The warning message to emit

        """
        ...


class TestCountingService:
    """Service for counting tests by size category.

    This service follows hexagonal architecture principles:
    - Works through protocols, not concrete pytest types
    - Contains no pytest-specific logic
    - Fully testable with fake implementations
    - Single responsibility: counting tests
    """

    def __init__(self) -> None:
        """Initialize the test counting service."""
        self._warned_tests: set[str] = set()

    def count_tests(
        self,
        items: Iterable[TestItemProtocol],
        warning_system: WarningSystemProtocol,
    ) -> DistributionStats:
        """Count tests by size category.

        Args:
            items: Iterable of test items to count
            warning_system: System for emitting warnings

        Returns:
            DistributionStats containing counts by size

        Raises:
            ValueError: If a test has multiple size markers

        """
        counts: dict[str, int] = defaultdict(int)

        for item in items:
            size = self._get_test_size(item, warning_system)
            if size is not None:
                counts[size.marker_name] += 1

        return DistributionStats.update_counts(
            TestCounts(
                small=counts.get('small', 0),
                medium=counts.get('medium', 0),
                large=counts.get('large', 0),
                xlarge=counts.get('xlarge', 0),
            )
        )

    def _get_test_size(
        self,
        item: TestItemProtocol,
        warning_system: WarningSystemProtocol,
    ) -> TestSize | None:
        """Get the size of a test item.

        Args:
            item: Test item to check
            warning_system: System for emitting warnings

        Returns:
            TestSize if item has a size marker, None otherwise

        Raises:
            ValueError: If item has multiple size markers

        """
        found_sizes = [size for size in TestSize if item.get_closest_marker(size.marker_name)]

        if not found_sizes:
            if item.nodeid not in self._warned_tests:
                warning_system.warn(f'Test has no size marker: {item.nodeid}')
                self._warned_tests.add(item.nodeid)
            return None

        if len(found_sizes) > 1:
            marker_names = ', '.join(size.marker_name for size in found_sizes)
            msg = f'Test cannot have multiple size markers: {marker_names}'
            raise ValueError(msg)

        return found_sizes[0]
