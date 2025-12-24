"""Unit tests for TestDiscoveryService using fake adapters.

This test module validates the TestDiscoveryService in isolation using
FakeTestItem and FakeWarningSystem test doubles. These tests are fast and
deterministic because they don't depend on pytest infrastructure.
"""

from __future__ import annotations

import pytest

from pytest_test_categories.services.test_discovery import TestDiscoveryService
from pytest_test_categories.types import TestSize
from tests._fixtures.test_item import FakeTestItem
from tests._fixtures.warning_system import FakeWarningSystem


class FakeMarker:
    """Fake marker for testing."""

    def __init__(self, name: str, kwargs: dict[str, object] | None = None) -> None:
        """Initialize fake marker with name and optional kwargs.

        Args:
            name: The marker name.
            kwargs: Optional keyword arguments for the marker.

        """
        self.name = name
        self.kwargs = kwargs or {}


@pytest.mark.small
class DescribeTestDiscoveryService:
    """Tests for TestDiscoveryService class."""

    def it_finds_single_size_marker_on_test_item(self) -> None:
        """It finds and returns the TestSize when test has a single size marker."""
        # Arrange: Create a test item with a 'small' marker
        small_marker = FakeMarker('small')
        test_item = FakeTestItem(
            nodeid='test_module.py::test_function',
            markers={'small': small_marker},
        )
        warning_system = FakeWarningSystem()
        service = TestDiscoveryService(warning_system=warning_system)

        # Act: Find the test size
        result = service.find_test_size(test_item)

        # Assert: Returns SMALL size, no warnings
        assert result == TestSize.SMALL
        assert not warning_system.get_warnings()

    def it_returns_none_and_warns_for_missing_marker(self) -> None:
        """It returns None and emits warning when test has no size marker."""
        # Arrange: Create a test item with no markers
        test_item = FakeTestItem(nodeid='test_module.py::test_no_marker')
        warning_system = FakeWarningSystem()
        service = TestDiscoveryService(warning_system=warning_system)

        # Act: Find the test size
        result = service.find_test_size(test_item)

        # Assert: Returns None and warns about missing marker
        assert result is None
        assert warning_system.has_warning('Test has no size marker: test_module.py::test_no_marker')
        assert warning_system.has_warning_with_category(pytest.PytestWarning)

    def it_raises_usage_error_for_multiple_markers(self) -> None:
        """It raises UsageError when test has multiple size markers."""
        # Arrange: Create a test item with multiple size markers
        small_marker = FakeMarker('small')
        medium_marker = FakeMarker('medium')
        test_item = FakeTestItem(
            nodeid='test_module.py::test_multi',
            markers={'small': small_marker, 'medium': medium_marker},
        )
        warning_system = FakeWarningSystem()
        service = TestDiscoveryService(warning_system=warning_system)

        # Act & Assert: Raises UsageError with appropriate message
        with pytest.raises(pytest.UsageError) as exc_info:
            service.find_test_size(test_item)

        assert 'small' in str(exc_info.value)
        assert 'medium' in str(exc_info.value)

    def it_warns_only_once_per_test_for_missing_marker(self) -> None:
        """It warns only once for each test missing a marker (deduplication)."""
        # Arrange: Create same test item multiple times
        test_item = FakeTestItem(nodeid='test_module.py::test_repeat')
        warning_system = FakeWarningSystem()
        service = TestDiscoveryService(warning_system=warning_system)

        # Act: Find test size multiple times
        result1 = service.find_test_size(test_item)
        result2 = service.find_test_size(test_item)
        result3 = service.find_test_size(test_item)

        # Assert: Returns None each time but only one warning
        assert result1 is None
        assert result2 is None
        assert result3 is None
        warnings = warning_system.get_warnings()
        assert len(warnings) == 1
        assert warnings[0][0] == 'Test has no size marker: test_module.py::test_repeat'

    @pytest.mark.parametrize(
        ('marker_name', 'expected_size'),
        [
            ('small', TestSize.SMALL),
            ('medium', TestSize.MEDIUM),
            ('large', TestSize.LARGE),
            ('xlarge', TestSize.XLARGE),
        ],
    )
    def it_finds_all_four_test_sizes(self, marker_name: str, expected_size: TestSize) -> None:
        """It correctly identifies all four test size markers."""
        # Arrange: Create test item with specified marker
        marker = FakeMarker(marker_name)
        test_item = FakeTestItem(
            nodeid=f'test_module.py::test_{marker_name}',
            markers={marker_name: marker},
        )
        warning_system = FakeWarningSystem()
        service = TestDiscoveryService(warning_system=warning_system)

        # Act: Find the test size
        result = service.find_test_size(test_item)

        # Assert: Returns correct size
        assert result == expected_size

    def it_handles_case_where_marker_exists_but_is_not_size_marker(self) -> None:
        """It returns None and warns when marker exists but is not a size marker."""
        # Arrange: Create test item with non-size marker
        other_marker = FakeMarker('skip')
        test_item = FakeTestItem(
            nodeid='test_module.py::test_other',
            markers={'skip': other_marker},
        )
        warning_system = FakeWarningSystem()
        service = TestDiscoveryService(warning_system=warning_system)

        # Act: Find the test size
        result = service.find_test_size(test_item)

        # Assert: Returns None and warns (has marker but not a size marker)
        assert result is None
        assert warning_system.has_warning('Test has no size marker: test_module.py::test_other')

    def it_detects_multiple_markers_even_with_non_size_markers_present(self) -> None:
        """It raises UsageError for multiple size markers even if other markers exist."""
        # Arrange: Create test item with two size markers and other markers
        small_marker = FakeMarker('small')
        large_marker = FakeMarker('large')
        skip_marker = FakeMarker('skip')
        test_item = FakeTestItem(
            nodeid='test_module.py::test_mixed',
            markers={'small': small_marker, 'large': large_marker, 'skip': skip_marker},
        )
        warning_system = FakeWarningSystem()
        service = TestDiscoveryService(warning_system=warning_system)

        # Act & Assert: Raises UsageError mentioning both size markers
        with pytest.raises(pytest.UsageError) as exc_info:
            service.find_test_size(test_item)

        error_message = str(exc_info.value)
        assert 'small' in error_message
        assert 'large' in error_message
        # Should not mention 'skip' since it's not a size marker
        assert 'skip' not in error_message

    def it_tracks_warned_tests_independently_for_different_tests(self) -> None:
        """It warns once per unique test, not once globally."""
        # Arrange: Create two different test items without markers
        test_item1 = FakeTestItem(nodeid='test_module.py::test_one')
        test_item2 = FakeTestItem(nodeid='test_module.py::test_two')
        warning_system = FakeWarningSystem()
        service = TestDiscoveryService(warning_system=warning_system)

        # Act: Find test size for both items
        result1 = service.find_test_size(test_item1)
        result2 = service.find_test_size(test_item2)

        # Assert: Returns None for both and warns once per unique test
        assert result1 is None
        assert result2 is None
        warnings = warning_system.get_warnings()
        assert len(warnings) == 2
        assert warning_system.has_warning('Test has no size marker: test_module.py::test_one')
        assert warning_system.has_warning('Test has no size marker: test_module.py::test_two')

    def it_reuses_same_warning_system_across_multiple_finds(self) -> None:
        """It accumulates warnings in the provided warning system."""
        # Arrange: Create multiple test items without markers
        test_items = [
            FakeTestItem(nodeid='test_a.py::test_1'),
            FakeTestItem(nodeid='test_b.py::test_2'),
            FakeTestItem(nodeid='test_c.py::test_3'),
        ]
        warning_system = FakeWarningSystem()
        service = TestDiscoveryService(warning_system=warning_system)

        # Act: Find test size for all items
        for item in test_items:
            service.find_test_size(item)

        # Assert: All warnings accumulated in the same warning system
        warnings = warning_system.get_warnings()
        assert len(warnings) == 3
        assert all(cat == pytest.PytestWarning for _, cat in warnings)


@pytest.mark.small
class DescribeGetTimeout:
    """Tests for get_timeout method to extract custom baselines from markers."""

    def it_returns_none_when_no_timeout_specified(self) -> None:
        """Return None when marker has no timeout kwarg."""
        small_marker = FakeMarker('small')
        test_item = FakeTestItem(
            nodeid='test_module.py::test_function',
            markers={'small': small_marker},
        )
        warning_system = FakeWarningSystem()
        service = TestDiscoveryService(warning_system=warning_system)

        result = service.get_timeout(test_item)

        assert result is None

    def it_returns_timeout_from_small_marker(self) -> None:
        """Extract timeout from @pytest.mark.small(timeout=0.1)."""
        small_marker = FakeMarker('small', kwargs={'timeout': 0.1})
        test_item = FakeTestItem(
            nodeid='test_module.py::test_function',
            markers={'small': small_marker},
        )
        warning_system = FakeWarningSystem()
        service = TestDiscoveryService(warning_system=warning_system)

        result = service.get_timeout(test_item)

        assert result == 0.1

    def it_returns_timeout_from_medium_marker(self) -> None:
        """Extract timeout from @pytest.mark.medium(timeout=5.0)."""
        medium_marker = FakeMarker('medium', kwargs={'timeout': 5.0})
        test_item = FakeTestItem(
            nodeid='test_module.py::test_function',
            markers={'medium': medium_marker},
        )
        warning_system = FakeWarningSystem()
        service = TestDiscoveryService(warning_system=warning_system)

        result = service.get_timeout(test_item)

        assert result == 5.0

    def it_returns_timeout_from_large_marker(self) -> None:
        """Extract timeout from @pytest.mark.large(timeout=60.0)."""
        large_marker = FakeMarker('large', kwargs={'timeout': 60.0})
        test_item = FakeTestItem(
            nodeid='test_module.py::test_function',
            markers={'large': large_marker},
        )
        warning_system = FakeWarningSystem()
        service = TestDiscoveryService(warning_system=warning_system)

        result = service.get_timeout(test_item)

        assert result == 60.0

    def it_returns_timeout_from_xlarge_marker(self) -> None:
        """Extract timeout from @pytest.mark.xlarge(timeout=120.0)."""
        xlarge_marker = FakeMarker('xlarge', kwargs={'timeout': 120.0})
        test_item = FakeTestItem(
            nodeid='test_module.py::test_function',
            markers={'xlarge': xlarge_marker},
        )
        warning_system = FakeWarningSystem()
        service = TestDiscoveryService(warning_system=warning_system)

        result = service.get_timeout(test_item)

        assert result == 120.0

    def it_returns_none_when_no_size_marker(self) -> None:
        """Return None when test has no size marker."""
        test_item = FakeTestItem(nodeid='test_module.py::test_function')
        warning_system = FakeWarningSystem()
        service = TestDiscoveryService(warning_system=warning_system)

        result = service.get_timeout(test_item)

        assert result is None

    def it_ignores_other_kwargs_in_marker(self) -> None:
        """Extract only timeout, ignoring other kwargs."""
        small_marker = FakeMarker('small', kwargs={'timeout': 0.1, 'allow_external_systems': True})
        test_item = FakeTestItem(
            nodeid='test_module.py::test_function',
            markers={'small': small_marker},
        )
        warning_system = FakeWarningSystem()
        service = TestDiscoveryService(warning_system=warning_system)

        result = service.get_timeout(test_item)

        assert result == 0.1

    def it_handles_integer_timeout_value(self) -> None:
        """Accept integer timeout values (converted to float)."""
        small_marker = FakeMarker('small', kwargs={'timeout': 1})
        test_item = FakeTestItem(
            nodeid='test_module.py::test_function',
            markers={'small': small_marker},
        )
        warning_system = FakeWarningSystem()
        service = TestDiscoveryService(warning_system=warning_system)

        result = service.get_timeout(test_item)

        assert result == 1.0
        assert isinstance(result, float)
