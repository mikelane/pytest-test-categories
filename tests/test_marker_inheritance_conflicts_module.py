"""Unit tests for marker inheritance conflict detection.

This test module validates the marker inheritance conflict detection logic
in TestDiscoveryService. These tests cover:

1. Multiple base class conflicts (e.g., class TestFoo(SmallTest, MediumTest))
2. Child class overriding parent marker
3. Method marker conflicting with class marker
4. Explicit override suppression via marker kwarg

Following TDD, these tests are written FIRST before implementation.
"""

from __future__ import annotations

import pytest

from pytest_test_categories.services.test_discovery import TestDiscoveryService
from pytest_test_categories.types import TestSize
from tests._fixtures.test_item import FakeTestItem
from tests._fixtures.warning_system import FakeWarningSystem


class FakeMarker:
    """Fake marker for testing with optional kwargs support."""

    def __init__(self, name: str, kwargs: dict[str, object] | None = None) -> None:
        """Initialize fake marker with name and optional kwargs.

        Args:
            name: The marker name.
            kwargs: Optional keyword arguments for the marker.

        """
        self.name = name
        self.kwargs = kwargs or {}


class FakeClassInfo:
    """Fake class hierarchy information for testing conflict detection.

    This provides the class hierarchy information that TestItemPort.get_class_hierarchy()
    returns. Each entry in the hierarchy is a tuple of (class_name, markers_dict).
    """

    def __init__(
        self,
        class_hierarchy: list[tuple[str, dict[str, object]]] | None = None,
        method_markers: dict[str, object] | None = None,
    ) -> None:
        """Initialize class info.

        Args:
            class_hierarchy: List of (class_name, markers) tuples, ordered from child to parent.
                            First element is the immediate class, last is furthest ancestor.
            method_markers: Markers applied directly to the test method.

        """
        self.class_hierarchy = class_hierarchy or []
        self.method_markers = method_markers or {}


class FakeTestItemWithHierarchy(FakeTestItem):
    """Extended FakeTestItem that supports class hierarchy inspection."""

    def __init__(
        self,
        nodeid: str,
        markers: dict[str, object] | None = None,
        class_info: FakeClassInfo | None = None,
    ) -> None:
        """Initialize fake test item with hierarchy info.

        Args:
            nodeid: The test node ID string.
            markers: Optional dictionary mapping marker names to marker objects.
            class_info: Optional class hierarchy information.

        """
        super().__init__(nodeid, markers)
        self._class_info = class_info or FakeClassInfo()

    def get_class_hierarchy(self) -> list[tuple[str, dict[str, object]]]:
        """Get the class hierarchy with markers.

        Returns:
            List of (class_name, markers) tuples from child to parent.

        """
        return self._class_info.class_hierarchy

    def get_method_markers(self) -> dict[str, object]:
        """Get markers applied directly to the test method.

        Returns:
            Dictionary of marker names to marker objects.

        """
        return self._class_info.method_markers


@pytest.mark.small
class DescribeMarkerInheritanceConflicts:
    """Tests for marker inheritance conflict detection."""

    class DescribeMultipleBaseClassConflicts:
        """Tests for detecting conflicts from multiple inheritance."""

        def it_warns_when_class_inherits_from_multiple_sized_base_classes(self) -> None:
            """Warn when a class inherits from multiple base classes with different size markers.

            Example:
                class TestFoo(SmallTest, MediumTest):  # Warning!
                    pass

            """
            # Arrange: Create a test item from a class inheriting from SmallTest and MediumTest
            class_info = FakeClassInfo(
                class_hierarchy=[
                    ('TestFoo', {}),  # The child class itself (no direct markers)
                    ('SmallTest', {'small': FakeMarker('small')}),  # First base with @small
                    ('MediumTest', {'medium': FakeMarker('medium')}),  # Second base with @medium
                ]
            )
            # The effective marker comes from the first base class in MRO (SmallTest)
            test_item = FakeTestItemWithHierarchy(
                nodeid='test_module.py::TestFoo::test_method',
                markers={'small': FakeMarker('small')},  # Effective marker
                class_info=class_info,
            )
            warning_system = FakeWarningSystem()
            service = TestDiscoveryService(warning_system=warning_system)

            # Act: Find the test size (this should trigger conflict detection)
            result = service.find_test_size(test_item)

            # Assert: Returns the effective size but warns about conflict
            assert result == TestSize.SMALL
            warnings = warning_system.get_warnings()
            assert len(warnings) >= 1
            conflict_warning = next(
                (w for w in warnings if 'conflicting' in w[0].lower() or 'multiple' in w[0].lower()),
                None,
            )
            assert conflict_warning is not None, f'Expected conflict warning, got: {warnings}'
            assert 'SmallTest' in conflict_warning[0] or 'small' in conflict_warning[0]
            assert 'MediumTest' in conflict_warning[0] or 'medium' in conflict_warning[0]

        def it_does_not_warn_when_inheriting_from_single_sized_base(self) -> None:
            """No warning when class inherits from only one sized base class."""
            # Arrange: Create a test item from a class inheriting from only SmallTest
            class_info = FakeClassInfo(
                class_hierarchy=[
                    ('TestFoo', {}),
                    ('SmallTest', {'small': FakeMarker('small')}),
                ]
            )
            test_item = FakeTestItemWithHierarchy(
                nodeid='test_module.py::TestFoo::test_method',
                markers={'small': FakeMarker('small')},
                class_info=class_info,
            )
            warning_system = FakeWarningSystem()
            service = TestDiscoveryService(warning_system=warning_system)

            # Act: Find the test size
            result = service.find_test_size(test_item)

            # Assert: Returns size without any conflict warnings
            assert result == TestSize.SMALL
            warnings = warning_system.get_warnings()
            conflict_warnings = [w for w in warnings if 'conflict' in w[0].lower()]
            assert len(conflict_warnings) == 0

    class DescribeChildClassOverridesParent:
        """Tests for detecting when child class overrides parent's marker."""

        def it_warns_when_child_class_overrides_parent_size_marker(self) -> None:
            """Warn when a child class has a different size marker than parent.

            Example:
                @pytest.mark.small
                class TestBase:
                    pass

                @pytest.mark.medium  # Warning: overrides parent's @small
                class TestChild(TestBase):
                    pass

            """
            # Arrange: Create a test item where child overrides parent marker
            class_info = FakeClassInfo(
                class_hierarchy=[
                    ('TestChild', {'medium': FakeMarker('medium')}),  # Child has @medium
                    ('TestBase', {'small': FakeMarker('small')}),  # Parent has @small
                ]
            )
            test_item = FakeTestItemWithHierarchy(
                nodeid='test_module.py::TestChild::test_method',
                markers={'medium': FakeMarker('medium')},  # Effective marker is from child
                class_info=class_info,
            )
            warning_system = FakeWarningSystem()
            service = TestDiscoveryService(warning_system=warning_system)

            # Act: Find the test size
            result = service.find_test_size(test_item)

            # Assert: Returns the child's size but warns about override
            assert result == TestSize.MEDIUM
            warnings = warning_system.get_warnings()
            assert len(warnings) >= 1
            override_warning = next(
                (w for w in warnings if 'override' in w[0].lower()),
                None,
            )
            assert override_warning is not None, f'Expected override warning, got: {warnings}'

        def it_does_not_warn_when_child_and_parent_have_same_marker(self) -> None:
            """No warning when child has same marker as parent (reinforcing, not overriding)."""
            # Arrange: Create a test item where child has same marker as parent
            class_info = FakeClassInfo(
                class_hierarchy=[
                    ('TestChild', {'small': FakeMarker('small')}),
                    ('TestBase', {'small': FakeMarker('small')}),
                ]
            )
            test_item = FakeTestItemWithHierarchy(
                nodeid='test_module.py::TestChild::test_method',
                markers={'small': FakeMarker('small')},
                class_info=class_info,
            )
            warning_system = FakeWarningSystem()
            service = TestDiscoveryService(warning_system=warning_system)

            # Act: Find the test size
            result = service.find_test_size(test_item)

            # Assert: Returns size without override warning
            assert result == TestSize.SMALL
            warnings = warning_system.get_warnings()
            override_warnings = [w for w in warnings if 'override' in w[0].lower()]
            assert len(override_warnings) == 0

    class DescribeMethodOverridesClass:
        """Tests for detecting when method marker conflicts with class marker."""

        def it_warns_when_method_marker_conflicts_with_class_marker(self) -> None:
            """Warn when a method has a different size marker than its class.

            Example:
                @pytest.mark.small
                class TestFoo:
                    @pytest.mark.medium  # Warning: method overrides class marker
                    def test_something(self):
                        pass

            """
            # Arrange: Create a test item with method marker overriding class marker
            class_info = FakeClassInfo(
                class_hierarchy=[
                    ('TestFoo', {'small': FakeMarker('small')}),  # Class has @small
                ],
                method_markers={'medium': FakeMarker('medium')},  # Method has @medium
            )
            test_item = FakeTestItemWithHierarchy(
                nodeid='test_module.py::TestFoo::test_something',
                markers={'medium': FakeMarker('medium')},  # Effective marker is from method
                class_info=class_info,
            )
            warning_system = FakeWarningSystem()
            service = TestDiscoveryService(warning_system=warning_system)

            # Act: Find the test size
            result = service.find_test_size(test_item)

            # Assert: Returns method's size but warns about conflict
            assert result == TestSize.MEDIUM
            warnings = warning_system.get_warnings()
            assert len(warnings) >= 1
            conflict_warning = next(
                (w for w in warnings if 'method' in w[0].lower() or 'override' in w[0].lower()),
                None,
            )
            assert conflict_warning is not None, f'Expected method conflict warning, got: {warnings}'

        def it_does_not_warn_when_method_and_class_have_same_marker(self) -> None:
            """No warning when method has same marker as class."""
            # Arrange: Method marker matches class marker
            class_info = FakeClassInfo(
                class_hierarchy=[
                    ('TestFoo', {'small': FakeMarker('small')}),
                ],
                method_markers={'small': FakeMarker('small')},
            )
            test_item = FakeTestItemWithHierarchy(
                nodeid='test_module.py::TestFoo::test_something',
                markers={'small': FakeMarker('small')},
                class_info=class_info,
            )
            warning_system = FakeWarningSystem()
            service = TestDiscoveryService(warning_system=warning_system)

            # Act: Find the test size
            result = service.find_test_size(test_item)

            # Assert: Returns size without method conflict warning
            assert result == TestSize.SMALL
            warnings = warning_system.get_warnings()
            method_warnings = [w for w in warnings if 'method' in w[0].lower()]
            assert len(method_warnings) == 0

    class DescribeExplicitOverrideSuppression:
        """Tests for suppressing warnings with explicit override marker."""

        def it_does_not_warn_when_override_is_explicit(self) -> None:
            """No warning when marker includes override=True kwarg.

            Example:
                @pytest.mark.small
                class TestBase:
                    pass

                @pytest.mark.medium(override=True)  # Explicit override - no warning
                class TestChild(TestBase):
                    pass

            """
            # Arrange: Create a test item with explicit override
            marker_with_override = FakeMarker('medium', kwargs={'override': True})
            class_info = FakeClassInfo(
                class_hierarchy=[
                    ('TestChild', {'medium': marker_with_override}),  # Child with override=True
                    ('TestBase', {'small': FakeMarker('small')}),  # Parent has @small
                ]
            )
            test_item = FakeTestItemWithHierarchy(
                nodeid='test_module.py::TestChild::test_method',
                markers={'medium': marker_with_override},
                class_info=class_info,
            )
            warning_system = FakeWarningSystem()
            service = TestDiscoveryService(warning_system=warning_system)

            # Act: Find the test size
            result = service.find_test_size(test_item)

            # Assert: Returns size without any conflict/override warnings
            assert result == TestSize.MEDIUM
            warnings = warning_system.get_warnings()
            conflict_warnings = [w for w in warnings if 'override' in w[0].lower() or 'conflict' in w[0].lower()]
            assert len(conflict_warnings) == 0

        def it_still_warns_when_override_is_false(self) -> None:
            """Still warns when override=False (same as no kwarg)."""
            # Arrange: Create a test item with explicit override=False
            marker_without_override = FakeMarker('medium', kwargs={'override': False})
            class_info = FakeClassInfo(
                class_hierarchy=[
                    ('TestChild', {'medium': marker_without_override}),
                    ('TestBase', {'small': FakeMarker('small')}),
                ]
            )
            test_item = FakeTestItemWithHierarchy(
                nodeid='test_module.py::TestChild::test_method',
                markers={'medium': marker_without_override},
                class_info=class_info,
            )
            warning_system = FakeWarningSystem()
            service = TestDiscoveryService(warning_system=warning_system)

            # Act: Find the test size
            result = service.find_test_size(test_item)

            # Assert: Returns size but still warns about override
            assert result == TestSize.MEDIUM
            warnings = warning_system.get_warnings()
            override_warnings = [w for w in warnings if 'override' in w[0].lower()]
            assert len(override_warnings) >= 1

    class DescribeWarningContent:
        """Tests for warning message content and guidance."""

        def it_includes_guidance_on_resolving_multiple_inheritance_conflicts(self) -> None:
            """Warning includes guidance on how to resolve the conflict."""
            # Arrange
            class_info = FakeClassInfo(
                class_hierarchy=[
                    ('TestFoo', {}),
                    ('SmallTest', {'small': FakeMarker('small')}),
                    ('MediumTest', {'medium': FakeMarker('medium')}),
                ]
            )
            test_item = FakeTestItemWithHierarchy(
                nodeid='test_module.py::TestFoo::test_method',
                markers={'small': FakeMarker('small')},
                class_info=class_info,
            )
            warning_system = FakeWarningSystem()
            service = TestDiscoveryService(warning_system=warning_system)

            # Act
            service.find_test_size(test_item)

            # Assert: Warning should include resolution guidance
            warnings = warning_system.get_warnings()
            conflict_warning = next(
                (w for w in warnings if 'conflict' in w[0].lower() or 'multiple' in w[0].lower()),
                None,
            )
            assert conflict_warning is not None
            # Should mention using explicit marker or override
            assert 'explicit' in conflict_warning[0].lower() or 'override' in conflict_warning[0].lower()

        def it_includes_test_nodeid_in_warning_message(self) -> None:
            """Warning message includes the test node ID for identification."""
            # Arrange
            class_info = FakeClassInfo(
                class_hierarchy=[
                    ('TestChild', {'medium': FakeMarker('medium')}),
                    ('TestBase', {'small': FakeMarker('small')}),
                ]
            )
            test_item = FakeTestItemWithHierarchy(
                nodeid='test_module.py::TestChild::test_method',
                markers={'medium': FakeMarker('medium')},
                class_info=class_info,
            )
            warning_system = FakeWarningSystem()
            service = TestDiscoveryService(warning_system=warning_system)

            # Act
            service.find_test_size(test_item)

            # Assert: At least one warning should include the node ID
            warnings = warning_system.get_warnings()
            has_nodeid_in_warning = any('TestChild' in w[0] or 'test_module.py' in w[0] for w in warnings)
            assert has_nodeid_in_warning, f'Expected nodeid in warning, got: {warnings}'

    class DescribeEdgeCases:
        """Tests for edge cases in conflict detection."""

        def it_handles_test_item_without_class_hierarchy_support(self) -> None:
            """Works normally for test items that don't support hierarchy inspection.

            The FakeTestItem (without hierarchy) should still work normally.

            """
            # Arrange: Regular FakeTestItem without hierarchy support
            test_item = FakeTestItem(
                nodeid='test_module.py::test_function',
                markers={'small': FakeMarker('small')},
            )
            warning_system = FakeWarningSystem()
            service = TestDiscoveryService(warning_system=warning_system)

            # Act
            result = service.find_test_size(test_item)

            # Assert: Returns size without errors
            assert result == TestSize.SMALL
            # No conflict warnings (no hierarchy to analyze)
            conflict_warnings = [
                w for w in warning_system.get_warnings() if 'conflict' in w[0].lower() or 'override' in w[0].lower()
            ]
            assert len(conflict_warnings) == 0

        def it_handles_deeply_nested_inheritance(self) -> None:
            """Detects conflicts in deeply nested class hierarchies."""
            # Arrange: Deep hierarchy with conflict between top and bottom
            class_info = FakeClassInfo(
                class_hierarchy=[
                    ('TestLevel3', {'medium': FakeMarker('medium')}),  # Innermost - has @medium
                    ('TestLevel2', {}),  # No marker
                    ('TestLevel1', {}),  # No marker
                    ('SmallTest', {'small': FakeMarker('small')}),  # Base has @small
                ]
            )
            test_item = FakeTestItemWithHierarchy(
                nodeid='test_module.py::TestLevel3::test_method',
                markers={'medium': FakeMarker('medium')},
                class_info=class_info,
            )
            warning_system = FakeWarningSystem()
            service = TestDiscoveryService(warning_system=warning_system)

            # Act
            result = service.find_test_size(test_item)

            # Assert: Detects the override even with intermediate classes
            assert result == TestSize.MEDIUM
            warnings = warning_system.get_warnings()
            override_warning = next(
                (w for w in warnings if 'override' in w[0].lower()),
                None,
            )
            assert override_warning is not None, f'Expected override warning for deep hierarchy, got: {warnings}'

        def it_warns_only_once_for_same_test_conflict(self) -> None:
            """Conflict warnings are deduplicated for the same test processed multiple times."""
            # Arrange: Test with a conflict
            class_info = FakeClassInfo(
                class_hierarchy=[
                    ('TestChild', {'medium': FakeMarker('medium')}),
                    ('TestBase', {'small': FakeMarker('small')}),
                ]
            )
            test_item = FakeTestItemWithHierarchy(
                nodeid='test_module.py::TestChild::test_method',
                markers={'medium': FakeMarker('medium')},
                class_info=class_info,
            )
            warning_system = FakeWarningSystem()
            service = TestDiscoveryService(warning_system=warning_system)

            # Act: Process the same test multiple times
            service.find_test_size(test_item)
            service.find_test_size(test_item)
            service.find_test_size(test_item)

            # Assert: Only one conflict warning
            warnings = warning_system.get_warnings()
            override_warnings = [w for w in warnings if 'override' in w[0].lower()]
            assert len(override_warnings) == 1

        def it_handles_hierarchy_with_no_size_markers(self) -> None:
            """No crash when hierarchy exists but has no size markers."""
            # Arrange: Hierarchy exists but no size markers anywhere
            class_info = FakeClassInfo(
                class_hierarchy=[
                    ('TestFoo', {}),
                    ('SomeBase', {}),
                ]
            )
            test_item = FakeTestItemWithHierarchy(
                nodeid='test_module.py::TestFoo::test_method',
                markers={'small': FakeMarker('small')},  # Marker not from hierarchy
                class_info=class_info,
            )
            warning_system = FakeWarningSystem()
            service = TestDiscoveryService(warning_system=warning_system)

            # Act
            result = service.find_test_size(test_item)

            # Assert: Returns size without errors or conflict warnings
            assert result == TestSize.SMALL
            conflict_warnings = [
                w for w in warning_system.get_warnings() if 'override' in w[0].lower() or 'conflict' in w[0].lower()
            ]
            assert len(conflict_warnings) == 0

        def it_uses_get_marker_kwargs_for_override_detection(self) -> None:
            """Override detection works via get_marker_kwargs method."""

            # Arrange: Test where override=True is available via get_marker_kwargs
            # but not via the marker object's kwargs attribute
            class FakeItemWithKwargs(FakeTestItemWithHierarchy):
                def get_marker_kwargs(self, name: str) -> dict[str, object]:
                    if name == 'medium':
                        return {'override': True}
                    return {}

            class_info = FakeClassInfo(
                class_hierarchy=[
                    ('TestChild', {'medium': FakeMarker('medium')}),  # No kwargs on marker
                    ('TestBase', {'small': FakeMarker('small')}),
                ]
            )
            test_item = FakeItemWithKwargs(
                nodeid='test_module.py::TestChild::test_method',
                markers={'medium': FakeMarker('medium')},
                class_info=class_info,
            )
            warning_system = FakeWarningSystem()
            service = TestDiscoveryService(warning_system=warning_system)

            # Act
            result = service.find_test_size(test_item)

            # Assert: Returns size without override warning (suppressed)
            assert result == TestSize.MEDIUM
            override_warnings = [w for w in warning_system.get_warnings() if 'override' in w[0].lower()]
            assert len(override_warnings) == 0
