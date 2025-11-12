"""Unit tests for TestCountingService module.

This module tests the TestCountingService in isolation using fake test items.
No pytest infrastructure is required - these are pure unit tests.
"""

from __future__ import annotations

import pytest

from pytest_test_categories.services.test_counting import TestCountingService
from pytest_test_categories.types import TestSize


class FakeTestItem:
    """Fake test item for testing without pytest infrastructure."""

    def __init__(self, nodeid: str, size: TestSize | None = None) -> None:
        """Initialize fake test item.

        Args:
            nodeid: The test node ID
            size: The test size marker (None if no marker)

        """
        self.nodeid = nodeid
        self._size = size
        self._markers: dict[str, bool] = {}
        if size:
            self._markers[size.marker_name] = True

    def get_closest_marker(self, marker_name: str) -> bool:
        """Simulate pytest's get_closest_marker."""
        return self._markers.get(marker_name, False)


class FakeWarningSystem:
    """Fake warning system for testing."""

    def __init__(self) -> None:
        """Initialize fake warning system."""
        self.warnings: list[str] = []

    def warn(self, message: str) -> None:
        """Record a warning."""
        self.warnings.append(message)


@pytest.mark.small
class DescribeTestCountingService:
    """Test suite for TestCountingService."""

    def it_counts_no_tests_from_empty_list(self) -> None:
        """Return zero counts when given empty test list."""
        service = TestCountingService()
        warning_system = FakeWarningSystem()

        stats = service.count_tests([], warning_system)

        assert stats.counts.small == 0
        assert stats.counts.medium == 0
        assert stats.counts.large == 0
        assert stats.counts.xlarge == 0

    def it_counts_single_small_test(self) -> None:
        """Count a single small test correctly."""
        service = TestCountingService()
        warning_system = FakeWarningSystem()
        items = [FakeTestItem('test_one', TestSize.SMALL)]

        stats = service.count_tests(items, warning_system)

        assert stats.counts.small == 1
        assert stats.counts.medium == 0
        assert stats.counts.large == 0
        assert stats.counts.xlarge == 0

    def it_counts_single_medium_test(self) -> None:
        """Count a single medium test correctly."""
        service = TestCountingService()
        warning_system = FakeWarningSystem()
        items = [FakeTestItem('test_one', TestSize.MEDIUM)]

        stats = service.count_tests(items, warning_system)

        assert stats.counts.small == 0
        assert stats.counts.medium == 1
        assert stats.counts.large == 0
        assert stats.counts.xlarge == 0

    def it_counts_single_large_test(self) -> None:
        """Count a single large test correctly."""
        service = TestCountingService()
        warning_system = FakeWarningSystem()
        items = [FakeTestItem('test_one', TestSize.LARGE)]

        stats = service.count_tests(items, warning_system)

        assert stats.counts.small == 0
        assert stats.counts.medium == 0
        assert stats.counts.large == 1
        assert stats.counts.xlarge == 0

    def it_counts_single_xlarge_test(self) -> None:
        """Count a single xlarge test correctly."""
        service = TestCountingService()
        warning_system = FakeWarningSystem()
        items = [FakeTestItem('test_one', TestSize.XLARGE)]

        stats = service.count_tests(items, warning_system)

        assert stats.counts.small == 0
        assert stats.counts.medium == 0
        assert stats.counts.large == 0
        assert stats.counts.xlarge == 1

    def it_counts_mixed_test_sizes(self) -> None:
        """Count multiple tests of different sizes correctly."""
        service = TestCountingService()
        warning_system = FakeWarningSystem()
        items = [
            FakeTestItem('test_small_1', TestSize.SMALL),
            FakeTestItem('test_small_2', TestSize.SMALL),
            FakeTestItem('test_small_3', TestSize.SMALL),
            FakeTestItem('test_medium_1', TestSize.MEDIUM),
            FakeTestItem('test_medium_2', TestSize.MEDIUM),
            FakeTestItem('test_large_1', TestSize.LARGE),
            FakeTestItem('test_xlarge_1', TestSize.XLARGE),
        ]

        stats = service.count_tests(items, warning_system)

        assert stats.counts.small == 3
        assert stats.counts.medium == 2
        assert stats.counts.large == 1
        assert stats.counts.xlarge == 1

    def it_warns_about_tests_without_size_markers(self) -> None:
        """Warn when encountering tests without size markers."""
        service = TestCountingService()
        warning_system = FakeWarningSystem()
        items = [
            FakeTestItem('test_with_marker', TestSize.SMALL),
            FakeTestItem('test_without_marker', None),
        ]

        stats = service.count_tests(items, warning_system)

        assert stats.counts.small == 1
        assert len(warning_system.warnings) == 1
        assert 'test_without_marker' in warning_system.warnings[0]

    def it_does_not_warn_about_same_test_twice(self) -> None:
        """Warn only once per test without a size marker."""
        service = TestCountingService()
        warning_system = FakeWarningSystem()
        items = [FakeTestItem('test_no_marker', None)]

        # Count twice
        service.count_tests(items, warning_system)
        service.count_tests(items, warning_system)

        # Should only warn once
        assert len(warning_system.warnings) == 1

    def it_raises_error_for_multiple_size_markers(self) -> None:
        """Raise error when test has multiple size markers."""
        service = TestCountingService()
        warning_system = FakeWarningSystem()

        # Create item with multiple markers
        item = FakeTestItem('test_multiple', TestSize.SMALL)
        item._markers[TestSize.MEDIUM.marker_name] = True  # Add second marker

        with pytest.raises(ValueError, match='multiple size markers'):
            service.count_tests([item], warning_system)
