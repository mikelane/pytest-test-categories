"""Test the TestItemPort interface and its adapters.

This module tests the TestItemPort abstraction which follows the hexagonal
architecture pattern (Ports and Adapters) to isolate pytest dependencies.

The TestItemPort pattern:
- TestItemPort is the Port (abstract interface)
- PytestItemAdapter is the Production Adapter (wraps pytest.Item)
- FakeTestItem is the Test Adapter (controllable test double)

This architecture allows testing code that interacts with test items
without depending on pytest's internal implementation details.
"""

from __future__ import annotations

import pytest

from pytest_test_categories.adapters.pytest_adapter import PytestItemAdapter
from pytest_test_categories.types import TestItemPort
from tests._fixtures.test_item import FakeTestItem


@pytest.mark.small
class DescribeTestItemPort:
    """Tests for the TestItemPort abstract interface."""

    def it_defines_nodeid_property(self) -> None:
        """Verify that TestItemPort requires nodeid property."""
        # This test will pass once we create the TestItemPort ABC
        # with an abstract nodeid property

        # Attempting to instantiate abstract class should fail
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            TestItemPort()  # type: ignore[abstract]

    def it_defines_get_marker_method(self) -> None:
        """Verify that TestItemPort requires get_marker() method."""
        # The abstract class should have get_marker as abstract method
        assert hasattr(TestItemPort, 'get_marker')
        assert getattr(TestItemPort.get_marker, '__isabstractmethod__', False)

    def it_defines_set_nodeid_method(self) -> None:
        """Verify that TestItemPort requires set_nodeid() method."""
        # The abstract class should have set_nodeid as abstract method
        assert hasattr(TestItemPort, 'set_nodeid')
        assert getattr(TestItemPort.set_nodeid, '__isabstractmethod__', False)


@pytest.mark.small
class DescribePytestItemAdapter:
    """Tests for the PytestItemAdapter production adapter."""

    def it_wraps_pytest_item_nodeid(self, request: pytest.FixtureRequest) -> None:
        """Verify that adapter exposes pytest.Item.nodeid."""
        # Use the current test's item as a real pytest.Item
        adapter = PytestItemAdapter(request.node)
        assert adapter.nodeid == request.node.nodeid

    def it_wraps_pytest_item_get_closest_marker(self, request: pytest.FixtureRequest) -> None:
        """Verify that adapter delegates get_marker to pytest.Item."""
        # Use the current test's item which has a 'small' marker
        adapter = PytestItemAdapter(request.node)
        marker = adapter.get_marker('small')

        assert marker is not None
        assert marker.name == 'small'

    def it_returns_none_for_missing_marker(self, request: pytest.FixtureRequest) -> None:
        """Verify that adapter returns None for non-existent markers."""
        adapter = PytestItemAdapter(request.node)
        marker = adapter.get_marker('nonexistent_marker')

        assert marker is None

    def it_wraps_pytest_item_nodeid_setter(self, request: pytest.FixtureRequest) -> None:
        """Verify that adapter can modify pytest.Item._nodeid."""
        adapter = PytestItemAdapter(request.node)
        original_nodeid = adapter.nodeid

        new_nodeid = f'{original_nodeid}_modified'
        adapter.set_nodeid(new_nodeid)

        assert adapter.nodeid == new_nodeid
        assert request.node.nodeid == new_nodeid

        # Restore original nodeid for clean test execution
        adapter.set_nodeid(original_nodeid)


@pytest.mark.small
class DescribeFakeTestItem:
    """Tests for the FakeTestItem test adapter."""

    def it_provides_controllable_nodeid(self) -> None:
        """Verify that FakeTestItem has configurable nodeid."""
        item = FakeTestItem(nodeid='test_module.py::test_function')
        assert item.nodeid == 'test_module.py::test_function'

    def it_provides_controllable_markers(self) -> None:
        """Verify that FakeTestItem returns configured markers."""

        # Create a fake marker
        class FakeMarker:
            def __init__(self, name: str) -> None:
                self.name = name

        small_marker = FakeMarker('small')
        item = FakeTestItem(nodeid='test_file.py::test_func', markers={'small': small_marker})

        marker = item.get_marker('small')
        assert marker is not None
        assert marker.name == 'small'

    def it_returns_none_for_undefined_markers(self) -> None:
        """Verify that FakeTestItem returns None for markers not configured."""
        item = FakeTestItem(nodeid='test_file.py::test_func', markers={})
        marker = item.get_marker('medium')

        assert marker is None

    def it_allows_nodeid_modification(self) -> None:
        """Verify that FakeTestItem nodeid can be changed."""
        item = FakeTestItem(nodeid='original.py::test')
        item.set_nodeid('modified.py::test [LARGE]')

        assert item.nodeid == 'modified.py::test [LARGE]'

    def it_accepts_empty_markers_dict(self) -> None:
        """Verify that FakeTestItem works with no markers."""
        item = FakeTestItem(nodeid='test.py::func')
        assert item.get_marker('any_marker') is None

    def it_supports_multiple_markers(self) -> None:
        """Verify that FakeTestItem can have multiple markers."""

        class FakeMarker:
            def __init__(self, name: str) -> None:
                self.name = name

        item = FakeTestItem(
            nodeid='test.py::func',
            markers={'small': FakeMarker('small'), 'integration': FakeMarker('integration')},
        )

        assert item.get_marker('small') is not None
        assert item.get_marker('integration') is not None
        assert item.get_marker('large') is None
