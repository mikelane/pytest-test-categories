"""Suggestion collector for auto-categorization analysis.

This module provides the SuggestionCollector service and related data structures
for collecting resource usage observations and generating test category suggestions.

The collector operates in "observation mode" during test execution:
- Records resource access patterns (network, filesystem, subprocess, etc.)
- Records execution times
- Tracks current test size markers

After test execution, the collector can generate suggestions for appropriate
test size categories based on observed behavior.

Example:
    >>> collector = SuggestionCollector()
    >>> collector.record_observation(
    ...     'test_api.py::test_fetch',
    ...     ResourceType.NETWORK,
    ...     'Connection to example.com:443'
    ... )
    >>> collector.record_execution_time('test_api.py::test_fetch', 0.5)
    >>> collector.record_current_size('test_api.py::test_fetch', TestSize.SMALL)
    >>> # Later: generate suggestions based on observations

See Also:
    - violation_tracking.py: Similar pattern for tracking violations
    - services/hermeticity_summary.py: Similar pattern for summary output

"""

from __future__ import annotations

from collections import defaultdict
from enum import StrEnum

from pydantic import BaseModel

from pytest_test_categories.types import TestSize

# Thresholds for categorization rules
SLOW_TEST_THRESHOLD_SECONDS = 1.0  # Tests slower than this -> MEDIUM
VERY_SLOW_TEST_THRESHOLD_SECONDS = 300  # Tests slower than 5 minutes -> LARGE
MULTIPLE_RESOURCE_TYPES_THRESHOLD = 2  # This many resource types -> LARGE


class ResourceType(StrEnum):
    """Types of external resources that tests may access.

    Each resource type corresponds to a category that affects
    the appropriate test size classification.

    Attributes:
        NETWORK: Network access (socket connections)
        FILESYSTEM: Filesystem access outside temp dirs
        SUBPROCESS: Subprocess spawning
        DATABASE: Database connections
        SLEEP: Sleep/timing function calls

    """

    NETWORK = 'network'
    FILESYSTEM = 'filesystem'
    SUBPROCESS = 'subprocess'
    DATABASE = 'database'
    SLEEP = 'sleep'


class ResourceObservation(BaseModel, frozen=True):
    """Immutable record of a resource access observation.

    Captures information about a resource access for analysis purposes.
    The record is immutable (frozen) to ensure it cannot be modified
    after creation.

    Attributes:
        resource_type: The type of resource accessed.
        details: Human-readable description of the access.

    Example:
        >>> observation = ResourceObservation(
        ...     resource_type=ResourceType.NETWORK,
        ...     details='Connection to example.com:443',
        ... )

    """

    resource_type: ResourceType
    details: str


class TestSuggestion(BaseModel, frozen=True):
    """Immutable record of a test size suggestion.

    Captures the suggestion for a test's appropriate size category
    based on observed behavior.

    Attributes:
        test_nodeid: The pytest node ID of the test.
        current_size: The current size marker, or None if uncategorized.
        suggested_size: The suggested size based on observations.
        reason: Human-readable explanation for the suggestion.

    Example:
        >>> suggestion = TestSuggestion(
        ...     test_nodeid='test_api.py::test_fetch',
        ...     current_size=TestSize.SMALL,
        ...     suggested_size=TestSize.MEDIUM,
        ...     reason='network access detected',
        ... )

    """

    test_nodeid: str
    current_size: TestSize | None
    suggested_size: TestSize
    reason: str


class SuggestionCollector:
    """Service for collecting resource observations and generating suggestions.

    This collector operates in "observation mode" during test execution,
    recording resource access patterns without blocking them. After execution,
    it can generate suggestions for appropriate test size categories.

    The collector tracks:
    - Resource observations (network, filesystem, subprocess, database, sleep)
    - Execution times for each test
    - Current size markers for each test

    Example:
        >>> collector = SuggestionCollector()
        >>> collector.record_observation('test.py::test_fn', ResourceType.NETWORK, 'details')
        >>> collector.record_execution_time('test.py::test_fn', 0.5)
        >>> collector.record_current_size('test.py::test_fn', TestSize.SMALL)
        >>> collector.has_observations
        True

    """

    def __init__(self) -> None:
        """Initialize an empty suggestion collector."""
        self._observations: dict[str, list[ResourceObservation]] = defaultdict(list)
        self._execution_times: dict[str, float] = {}
        self._current_sizes: dict[str, TestSize | None] = {}

    def record_observation(
        self,
        test_nodeid: str,
        resource_type: ResourceType,
        details: str,
    ) -> None:
        """Record a resource access observation for a test.

        Args:
            test_nodeid: The pytest node ID of the test.
            resource_type: The type of resource accessed.
            details: Human-readable description of the access.

        """
        observation = ResourceObservation(
            resource_type=resource_type,
            details=details,
        )
        self._observations[test_nodeid].append(observation)

    def record_execution_time(
        self,
        test_nodeid: str,
        duration_seconds: float,
    ) -> None:
        """Record execution time for a test.

        Args:
            test_nodeid: The pytest node ID of the test.
            duration_seconds: The test execution time in seconds.

        """
        self._execution_times[test_nodeid] = duration_seconds

    def record_current_size(
        self,
        test_nodeid: str,
        size: TestSize | None,
    ) -> None:
        """Record the current size marker of a test.

        Args:
            test_nodeid: The pytest node ID of the test.
            size: The current size marker, or None if uncategorized.

        """
        self._current_sizes[test_nodeid] = size

    @property
    def observation_count(self) -> int:
        """Get the total number of observations across all tests.

        Returns:
            Total count of all recorded observations.

        """
        return sum(len(obs) for obs in self._observations.values())

    @property
    def has_observations(self) -> bool:
        """Check if any observations have been recorded.

        Returns:
            True if at least one observation has been recorded.

        """
        return self.observation_count > 0

    def get_test_observation_count(self, test_nodeid: str) -> int:
        """Get the number of observations for a specific test.

        Args:
            test_nodeid: The pytest node ID of the test.

        Returns:
            Number of observations for the specified test.

        """
        return len(self._observations.get(test_nodeid, []))

    def get_observations(self, test_nodeid: str) -> list[ResourceObservation]:
        """Get all observations for a specific test.

        Args:
            test_nodeid: The pytest node ID of the test.

        Returns:
            List of ResourceObservation instances for the specified test.

        """
        return list(self._observations.get(test_nodeid, []))

    def get_execution_time(self, test_nodeid: str) -> float | None:
        """Get the execution time for a specific test.

        Args:
            test_nodeid: The pytest node ID of the test.

        Returns:
            The execution time in seconds, or None if not recorded.

        """
        return self._execution_times.get(test_nodeid)

    def get_current_size(self, test_nodeid: str) -> TestSize | None:
        """Get the current size marker for a specific test.

        Args:
            test_nodeid: The pytest node ID of the test.

        Returns:
            The current size marker, or None if not recorded or uncategorized.

        """
        return self._current_sizes.get(test_nodeid)

    def get_all_test_nodeids(self) -> set[str]:
        """Get all test nodeids that have been recorded.

        Returns:
            Set of all test nodeids with any recorded data.

        """
        all_nodeids: set[str] = set()
        all_nodeids.update(self._observations.keys())
        all_nodeids.update(self._execution_times.keys())
        all_nodeids.update(self._current_sizes.keys())
        return all_nodeids

    def generate_suggestions(self) -> list[TestSuggestion]:
        """Generate test size suggestions based on collected observations.

        Analyzes all recorded tests and generates suggestions for tests that:
        - Are uncategorized (no size marker)
        - Have a size marker that doesn't match their observed behavior

        Categorization rules:
        - No external resources + <100ms -> SMALL
        - No external resources + <1s -> SMALL
        - External resources OR >1s -> MEDIUM
        - Multiple resource types OR >5min -> LARGE

        Returns:
            List of TestSuggestion instances for tests needing categorization changes.

        """
        suggestions: list[TestSuggestion] = []

        for test_nodeid in self.get_all_test_nodeids():
            suggested = self._suggest_size_for_test(test_nodeid)
            if suggested is not None:
                suggestions.append(suggested)

        return suggestions

    def _suggest_size_for_test(self, test_nodeid: str) -> TestSuggestion | None:
        """Determine the suggested size for a single test.

        Args:
            test_nodeid: The pytest node ID of the test.

        Returns:
            A TestSuggestion if the test needs recategorization, None otherwise.

        """
        current_size = self.get_current_size(test_nodeid)
        observations = self.get_observations(test_nodeid)
        execution_time = self.get_execution_time(test_nodeid)

        suggested_size, reason = self._analyze_test_behavior(observations, execution_time)

        # Only generate suggestion if there's a mismatch
        if current_size == suggested_size:
            return None

        return TestSuggestion(
            test_nodeid=test_nodeid,
            current_size=current_size,
            suggested_size=suggested_size,
            reason=reason,
        )

    def _analyze_test_behavior(
        self,
        observations: list[ResourceObservation],
        execution_time: float | None,
    ) -> tuple[TestSize, str]:
        """Analyze test behavior and determine appropriate size category.

        Args:
            observations: List of resource observations for the test.
            execution_time: Execution time in seconds, or None if not recorded.

        Returns:
            Tuple of (suggested_size, reason_string).

        """
        # Count unique resource types accessed
        resource_types = {obs.resource_type for obs in observations}
        num_resource_types = len(resource_types)

        # Check for very slow tests (>5 minutes)
        if execution_time is not None and execution_time > VERY_SLOW_TEST_THRESHOLD_SECONDS:
            return TestSize.LARGE, f'duration >5min ({execution_time:.1f}s)'

        # Check for multiple resource types -> LARGE
        if num_resource_types >= MULTIPLE_RESOURCE_TYPES_THRESHOLD:
            type_names = ', '.join(sorted(rt.value for rt in resource_types))
            return TestSize.LARGE, f'multiple resource types ({type_names})'

        # Check for any external resource -> MEDIUM
        if num_resource_types == 1:
            resource_type = next(iter(resource_types))
            return TestSize.MEDIUM, f'{resource_type.value} access detected'

        # Check for slow tests (>1 second) -> MEDIUM
        if execution_time is not None and execution_time > SLOW_TEST_THRESHOLD_SECONDS:
            return TestSize.MEDIUM, f'slow duration ({execution_time:.2f}s)'

        # No resources and fast -> SMALL
        duration_info = f', {execution_time * 1000:.0f}ms' if execution_time is not None else ''
        return TestSize.SMALL, f'no external resources{duration_info}'
