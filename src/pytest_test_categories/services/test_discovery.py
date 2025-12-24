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
- Detects marker inheritance conflicts and emits warnings

Conflict Detection:
- Multiple base class conflicts: class inherits from multiple sized base classes
- Child class overrides: child class marker differs from parent class marker
- Method overrides class: method marker differs from class marker
- Conflicts can be suppressed with explicit `override=True` marker kwarg

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

from dataclasses import dataclass

import pytest

from pytest_test_categories.types import (
    TestItemPort,
    TestSize,
    WarningSystemPort,
)


@dataclass(frozen=True)
class MarkerConflict:
    """Data class for holding marker conflict information."""

    child_class: str
    child_marker: str
    parent_class: str
    parent_marker: str


# Error message for multiple size markers
MULTIPLE_MARKERS_ERROR = 'Test cannot have multiple size markers: {}'

# Warning messages for marker inheritance conflicts
MULTIPLE_BASE_CONFLICT_WARNING = (
    'Marker inheritance conflict in {nodeid}: Class inherits from multiple base classes '
    'with different size markers ({markers}). Using {effective}. '
    'Add an explicit @pytest.mark.{effective} to the class or use override=True to suppress this warning.'
)

CHILD_OVERRIDES_PARENT_WARNING = (
    'Marker override in {nodeid}: {child_class} has @{child_marker} but inherits from '
    '{parent_class} with @{parent_marker}. Use @pytest.mark.{child_marker}(override=True) '
    'to indicate this is intentional.'
)

METHOD_OVERRIDES_CLASS_WARNING = (
    'Marker override in {nodeid}: Method has @{method_marker} but class has @{class_marker}. '
    'Use @pytest.mark.{method_marker}(override=True) to indicate this is intentional.'
)


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
        self._warned_conflicts: set[str] = set()  # Track conflict warnings to avoid duplicates

    def find_test_size(self, item: TestItemPort) -> TestSize | None:
        """Find the test size marker on a test item.

        Searches for size markers (small, medium, large, xlarge) on the test item.
        Returns the size if exactly one is found, warns and returns None if none are
        found, and raises UsageError if multiple size markers are found.

        The service tracks warned tests by their node ID to avoid duplicate warnings
        when the same test is processed multiple times.

        Also detects and warns about marker inheritance conflicts:
        - Multiple base classes with different size markers
        - Child class overriding parent class marker
        - Method marker conflicting with class marker

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

        # Exactly one size marker found
        effective_size = found_sizes[0]

        # Check for marker inheritance conflicts
        self._check_inheritance_conflicts(item, effective_size)

        return effective_size

    def get_timeout(self, item: TestItemPort) -> float | None:
        """Get the custom timeout from a test item's size marker.

        Extracts the optional `timeout` kwarg from the test's size marker.
        This allows tests to define stricter performance baselines than the
        category's default time limit.

        Args:
            item: The test item to inspect for timeout.

        Returns:
            The timeout value in seconds if specified, None otherwise.

        Example:
            >>> # Test with @pytest.mark.small(timeout=0.1)
            >>> item = FakeTestItem(
            ...     nodeid='test.py::test_fast',
            ...     markers={'small': FakeMarker('small', kwargs={'timeout': 0.1})}
            ... )
            >>> timeout = service.get_timeout(item)
            >>> assert timeout == 0.1

            >>> # Test without timeout
            >>> item = FakeTestItem(
            ...     nodeid='test.py::test_normal',
            ...     markers={'small': FakeMarker('small')}
            ... )
            >>> timeout = service.get_timeout(item)
            >>> assert timeout is None

        """
        # Find the size marker
        for size in TestSize:
            marker_kwargs = item.get_marker_kwargs(size.marker_name)
            if marker_kwargs:
                timeout = marker_kwargs.get('timeout')
                if timeout is not None:
                    # timeout can be float, int, or string from marker kwargs
                    return float(str(timeout))
                return None

        # No size marker found
        return None

    def _check_inheritance_conflicts(self, item: TestItemPort, effective_size: TestSize) -> None:
        """Check for marker inheritance conflicts and emit warnings.

        This method inspects the class hierarchy and method markers to detect
        potential conflicts that may cause confusion about which size applies.

        Conflicts are only warned about once per test to avoid duplicate warnings.

        Args:
            item: The test item to inspect.
            effective_size: The effective size marker that was determined.

        """
        # Skip if we've already warned about this test
        conflict_key = f'conflict:{item.nodeid}'
        if conflict_key in self._warned_conflicts:
            return

        # Get class hierarchy information
        hierarchy = item.get_class_hierarchy()
        method_markers = item.get_method_markers()

        # Check for multiple base class conflicts
        self._check_multiple_base_conflicts(item, hierarchy, effective_size)

        # Check for child overriding parent
        self._check_child_override_conflicts(item, hierarchy)

        # Check for method overriding class
        self._check_method_override_conflicts(item, hierarchy, method_markers)

    def _check_multiple_base_conflicts(
        self,
        item: TestItemPort,
        hierarchy: list[tuple[str, dict[str, object]]],
        effective_size: TestSize,
    ) -> None:
        """Check for conflicts from multiple inheritance.

        Warns when a class inherits from multiple base classes that have
        different size markers (e.g., class TestFoo(SmallTest, MediumTest)).

        Args:
            item: The test item being checked.
            hierarchy: The class hierarchy with markers.
            effective_size: The effective size marker determined.

        """
        if len(hierarchy) < 2:
            return

        # Find all unique size markers in the base classes (not the immediate class)
        # The first entry is the immediate class, the rest are ancestors
        base_sizes: dict[str, str] = {}  # marker_name -> class_name
        for class_name, markers in hierarchy[1:]:  # Skip the immediate class
            for marker_name in markers:
                if marker_name in {'small', 'medium', 'large', 'xlarge'} and marker_name not in base_sizes:
                    base_sizes[marker_name] = class_name

        # If multiple different sizes found in base classes, warn
        if len(base_sizes) > 1:
            # Check if immediate class has explicit marker (which would suppress warning)
            immediate_class_markers = hierarchy[0][1] if hierarchy else {}
            has_explicit_override = self._has_explicit_override(item, immediate_class_markers)

            if not has_explicit_override:
                conflict_key = f'conflict:{item.nodeid}'
                if conflict_key not in self._warned_conflicts:
                    marker_list = ', '.join(f'{cls} (@{marker})' for marker, cls in sorted(base_sizes.items()))
                    warning = MULTIPLE_BASE_CONFLICT_WARNING.format(
                        nodeid=item.nodeid,
                        markers=marker_list,
                        effective=effective_size.marker_name,
                    )
                    self._warning_system.warn(warning, category=pytest.PytestWarning)
                    self._warned_conflicts.add(conflict_key)

    def _check_child_override_conflicts(
        self,
        item: TestItemPort,
        hierarchy: list[tuple[str, dict[str, object]]],
    ) -> None:
        """Check for child class overriding parent marker.

        Warns when a child class has a different size marker than its parent class.

        Args:
            item: The test item being checked.
            hierarchy: The class hierarchy with markers.

        """
        if len(hierarchy) < 2:
            return

        # Find the first (immediate) class with a marker
        child_info = self._find_first_class_with_marker(hierarchy)
        if child_info is None:
            return

        child_class_name, child_marker = child_info

        # Find conflicting parent and emit warning if needed
        conflict = self._find_parent_conflict(hierarchy, child_class_name, child_marker)
        if conflict is not None:
            self._emit_child_override_warning(item, hierarchy, conflict)

    def _find_first_class_with_marker(
        self,
        hierarchy: list[tuple[str, dict[str, object]]],
    ) -> tuple[str, str] | None:
        """Find the first class in the hierarchy that has a size marker.

        Args:
            hierarchy: The class hierarchy with markers.

        Returns:
            Tuple of (class_name, marker_name) or None if no marker found.

        """
        for class_name, markers in hierarchy:
            size_markers = [m for m in markers if m in {'small', 'medium', 'large', 'xlarge'}]
            if size_markers:
                return (class_name, size_markers[0])
        return None

    def _find_parent_conflict(
        self,
        hierarchy: list[tuple[str, dict[str, object]]],
        child_class_name: str,
        child_marker: str,
    ) -> MarkerConflict | None:
        """Find a parent class with a different marker than the child.

        Args:
            hierarchy: The class hierarchy with markers.
            child_class_name: Name of the child class with the marker.
            child_marker: The child's marker name.

        Returns:
            MarkerConflict if a conflict is found, None otherwise.

        """
        found_child = False
        for class_name, markers in hierarchy:
            size_markers = [m for m in markers if m in {'small', 'medium', 'large', 'xlarge'}]
            if not found_child:
                if size_markers:
                    found_child = True
                continue

            # This is a parent class - check for different marker
            if size_markers and size_markers[0] != child_marker:
                return MarkerConflict(
                    child_class=child_class_name,
                    child_marker=child_marker,
                    parent_class=class_name,
                    parent_marker=size_markers[0],
                )
        return None

    def _emit_child_override_warning(
        self,
        item: TestItemPort,
        hierarchy: list[tuple[str, dict[str, object]]],
        conflict: MarkerConflict,
    ) -> None:
        """Emit a warning for child class overriding parent marker.

        Args:
            item: The test item being checked.
            hierarchy: The class hierarchy with markers.
            conflict: The conflict details.

        """
        has_explicit_override = self._has_explicit_override(item, hierarchy[0][1])

        if not has_explicit_override:
            conflict_key = f'conflict:{item.nodeid}'
            if conflict_key not in self._warned_conflicts:
                warning = CHILD_OVERRIDES_PARENT_WARNING.format(
                    nodeid=item.nodeid,
                    child_class=conflict.child_class,
                    child_marker=conflict.child_marker,
                    parent_class=conflict.parent_class,
                    parent_marker=conflict.parent_marker,
                )
                self._warning_system.warn(warning, category=pytest.PytestWarning)
                self._warned_conflicts.add(conflict_key)

    def _check_method_override_conflicts(
        self,
        item: TestItemPort,
        hierarchy: list[tuple[str, dict[str, object]]],
        method_markers: dict[str, object],
    ) -> None:
        """Check for method marker conflicting with class marker.

        Warns when a test method has a different size marker than its class.

        Args:
            item: The test item being checked.
            hierarchy: The class hierarchy with markers.
            method_markers: Markers applied to the test method.

        """
        # Find method size marker
        method_size_markers = [m for m in method_markers if m in {'small', 'medium', 'large', 'xlarge'}]
        if not method_size_markers:
            return

        method_marker = method_size_markers[0]

        # Find class size marker (from immediate class or inherited)
        class_marker: str | None = None
        for _class_name, markers in hierarchy:
            class_size_markers = [m for m in markers if m in {'small', 'medium', 'large', 'xlarge'}]
            if class_size_markers:
                class_marker = class_size_markers[0]
                break

        if class_marker is None or class_marker == method_marker:
            return

        # Check for explicit override on method marker
        method_marker_obj = method_markers.get(method_marker)
        has_explicit_override = False
        if method_marker_obj is not None and hasattr(method_marker_obj, 'kwargs'):
            has_explicit_override = getattr(method_marker_obj, 'kwargs', {}).get('override', False)

        if not has_explicit_override:
            conflict_key = f'conflict:{item.nodeid}'
            if conflict_key not in self._warned_conflicts:
                warning = METHOD_OVERRIDES_CLASS_WARNING.format(
                    nodeid=item.nodeid,
                    method_marker=method_marker,
                    class_marker=class_marker,
                )
                self._warning_system.warn(warning, category=pytest.PytestWarning)
                self._warned_conflicts.add(conflict_key)

    def _has_explicit_override(self, item: TestItemPort, class_markers: dict[str, object]) -> bool:
        """Check if the marker has an explicit override=True kwarg.

        Args:
            item: The test item to check.
            class_markers: The markers dict from the class.

        Returns:
            True if any size marker has override=True, False otherwise.

        """
        for marker_name in ['small', 'medium', 'large', 'xlarge']:
            marker = class_markers.get(marker_name)
            if (
                marker is not None
                and hasattr(marker, 'kwargs')
                and getattr(marker, 'kwargs', {}).get('override', False)
            ):
                return True

            # Also check via get_marker_kwargs for compatibility
            kwargs = item.get_marker_kwargs(marker_name)
            if kwargs.get('override', False):
                return True

        return False
