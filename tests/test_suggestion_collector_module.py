"""Unit tests for suggestion collector module.

This module tests the SuggestionCollector service and related data structures
for collecting resource usage observations and generating test category suggestions.
"""

from __future__ import annotations

import pytest

from pytest_test_categories.suggestion import (
    ResourceObservation,
    ResourceType,
    SuggestionCollector,
    TestSuggestion,
)
from pytest_test_categories.types import TestSize


@pytest.mark.small
class DescribeResourceType:
    """Test suite for ResourceType enum."""

    def it_has_network_resource_type(self) -> None:
        """ResourceType has a NETWORK variant."""
        assert ResourceType.NETWORK.value == 'network'

    def it_has_filesystem_resource_type(self) -> None:
        """ResourceType has a FILESYSTEM variant."""
        assert ResourceType.FILESYSTEM.value == 'filesystem'

    def it_has_subprocess_resource_type(self) -> None:
        """ResourceType has a SUBPROCESS variant."""
        assert ResourceType.SUBPROCESS.value == 'subprocess'

    def it_has_database_resource_type(self) -> None:
        """ResourceType has a DATABASE variant."""
        assert ResourceType.DATABASE.value == 'database'

    def it_has_sleep_resource_type(self) -> None:
        """ResourceType has a SLEEP variant."""
        assert ResourceType.SLEEP.value == 'sleep'


@pytest.mark.small
class DescribeResourceObservation:
    """Test suite for ResourceObservation data class."""

    def it_stores_resource_type(self) -> None:
        """ResourceObservation stores resource type."""
        observation = ResourceObservation(
            resource_type=ResourceType.NETWORK,
            details='Connection to example.com:443',
        )

        assert observation.resource_type == ResourceType.NETWORK

    def it_stores_details(self) -> None:
        """ResourceObservation stores observation details."""
        observation = ResourceObservation(
            resource_type=ResourceType.FILESYSTEM,
            details='Read /etc/passwd',
        )

        assert observation.details == 'Read /etc/passwd'

    def it_is_immutable(self) -> None:
        """ResourceObservation is immutable (frozen)."""
        observation = ResourceObservation(
            resource_type=ResourceType.DATABASE,
            details='SQLite connection',
        )

        with pytest.raises(Exception):  # noqa: B017, PT011
            observation.details = 'other'  # type: ignore[misc]


@pytest.mark.small
class DescribeTestSuggestion:
    """Test suite for TestSuggestion data class."""

    def it_stores_test_nodeid(self) -> None:
        """TestSuggestion stores test nodeid."""
        suggestion = TestSuggestion(
            test_nodeid='test_api.py::test_fetch',
            current_size=TestSize.SMALL,
            suggested_size=TestSize.MEDIUM,
            reason='network access detected',
        )

        assert suggestion.test_nodeid == 'test_api.py::test_fetch'

    def it_stores_current_size(self) -> None:
        """TestSuggestion stores current size (can be None for uncategorized)."""
        suggestion = TestSuggestion(
            test_nodeid='test_new.py::test_feature',
            current_size=None,
            suggested_size=TestSize.SMALL,
            reason='no external resources',
        )

        assert suggestion.current_size is None

    def it_stores_suggested_size(self) -> None:
        """TestSuggestion stores suggested size."""
        suggestion = TestSuggestion(
            test_nodeid='test_api.py::test_fetch',
            current_size=TestSize.SMALL,
            suggested_size=TestSize.MEDIUM,
            reason='network access detected',
        )

        assert suggestion.suggested_size == TestSize.MEDIUM

    def it_stores_reason(self) -> None:
        """TestSuggestion stores the reason for the suggestion."""
        suggestion = TestSuggestion(
            test_nodeid='test_utils.py::test_format',
            current_size=TestSize.MEDIUM,
            suggested_size=TestSize.SMALL,
            reason='no external resources, 50ms',
        )

        assert suggestion.reason == 'no external resources, 50ms'

    def it_is_immutable(self) -> None:
        """TestSuggestion is immutable (frozen)."""
        suggestion = TestSuggestion(
            test_nodeid='test_api.py::test_fetch',
            current_size=TestSize.SMALL,
            suggested_size=TestSize.MEDIUM,
            reason='network access detected',
        )

        with pytest.raises(Exception):  # noqa: B017, PT011
            suggestion.reason = 'other'  # type: ignore[misc]


@pytest.mark.small
class DescribeSuggestionCollector:
    """Test suite for SuggestionCollector service."""

    def it_starts_with_no_observations(self) -> None:
        """New SuggestionCollector has no observations."""
        collector = SuggestionCollector()

        assert collector.observation_count == 0

    def it_records_observation_for_test(self) -> None:
        """SuggestionCollector can record an observation for a test."""
        collector = SuggestionCollector()

        collector.record_observation(
            test_nodeid='test_api.py::test_fetch',
            resource_type=ResourceType.NETWORK,
            details='Connection to example.com:443',
        )

        assert collector.observation_count == 1

    def it_records_multiple_observations_for_same_test(self) -> None:
        """SuggestionCollector can record multiple observations for the same test."""
        collector = SuggestionCollector()

        collector.record_observation(
            test_nodeid='test_api.py::test_fetch',
            resource_type=ResourceType.NETWORK,
            details='Connection to api.example.com:443',
        )
        collector.record_observation(
            test_nodeid='test_api.py::test_fetch',
            resource_type=ResourceType.DATABASE,
            details='PostgreSQL connection',
        )

        assert collector.observation_count == 2
        assert collector.get_test_observation_count('test_api.py::test_fetch') == 2

    def it_records_execution_time_for_test(self) -> None:
        """SuggestionCollector can record execution time for a test."""
        collector = SuggestionCollector()

        collector.record_execution_time(
            test_nodeid='test_utils.py::test_format',
            duration_seconds=0.05,
        )

        assert collector.get_execution_time('test_utils.py::test_format') == 0.05

    def it_records_current_size_for_test(self) -> None:
        """SuggestionCollector can record the current size marker of a test."""
        collector = SuggestionCollector()

        collector.record_current_size(
            test_nodeid='test_api.py::test_fetch',
            size=TestSize.SMALL,
        )

        assert collector.get_current_size('test_api.py::test_fetch') == TestSize.SMALL

    def it_records_none_for_uncategorized_test(self) -> None:
        """SuggestionCollector can record None for uncategorized tests."""
        collector = SuggestionCollector()

        collector.record_current_size(
            test_nodeid='test_new.py::test_feature',
            size=None,
        )

        assert collector.get_current_size('test_new.py::test_feature') is None

    def it_returns_none_for_unknown_test_size(self) -> None:
        """get_current_size returns None for tests not recorded."""
        collector = SuggestionCollector()

        assert collector.get_current_size('unknown::test') is None

    def it_returns_none_for_unknown_test_time(self) -> None:
        """get_execution_time returns None for tests not recorded."""
        collector = SuggestionCollector()

        assert collector.get_execution_time('unknown::test') is None

    def it_gets_observations_for_test(self) -> None:
        """SuggestionCollector can retrieve observations for a specific test."""
        collector = SuggestionCollector()

        collector.record_observation(
            test_nodeid='test_api.py::test_fetch',
            resource_type=ResourceType.NETWORK,
            details='network details',
        )
        collector.record_observation(
            test_nodeid='test_api.py::test_fetch',
            resource_type=ResourceType.DATABASE,
            details='database details',
        )

        observations = collector.get_observations('test_api.py::test_fetch')

        assert len(observations) == 2
        assert observations[0].resource_type == ResourceType.NETWORK
        assert observations[1].resource_type == ResourceType.DATABASE

    def it_returns_empty_list_for_unknown_test_observations(self) -> None:
        """get_observations returns empty list for unknown tests."""
        collector = SuggestionCollector()

        assert collector.get_observations('unknown::test') == []

    def it_gets_all_test_nodeids(self) -> None:
        """SuggestionCollector can retrieve all recorded test nodeids."""
        collector = SuggestionCollector()

        collector.record_current_size('test_a.py::test_one', TestSize.SMALL)
        collector.record_observation('test_b.py::test_two', ResourceType.NETWORK, 'details')
        collector.record_execution_time('test_c.py::test_three', 0.1)

        nodeids = collector.get_all_test_nodeids()

        assert 'test_a.py::test_one' in nodeids
        assert 'test_b.py::test_two' in nodeids
        assert 'test_c.py::test_three' in nodeids

    def it_has_observations_property(self) -> None:
        """SuggestionCollector has has_observations property."""
        collector = SuggestionCollector()

        assert collector.has_observations is False

        collector.record_observation('test.py::test_fn', ResourceType.NETWORK, 'details')

        assert collector.has_observations is True


@pytest.mark.small
class DescribeSuggestionCollectorGenerateSuggestions:
    """Test suite for SuggestionCollector.generate_suggestions() method."""

    def it_returns_empty_list_when_no_tests_recorded(self) -> None:
        """generate_suggestions returns empty list when no tests recorded."""
        collector = SuggestionCollector()

        suggestions = collector.generate_suggestions()

        assert suggestions == []

    def it_suggests_small_for_test_with_no_resources_and_fast_execution(self) -> None:
        """Suggests small for tests with no external resources and <100ms."""
        collector = SuggestionCollector()
        collector.record_current_size('test.py::test_fn', None)
        collector.record_execution_time('test.py::test_fn', 0.05)

        suggestions = collector.generate_suggestions()

        assert len(suggestions) == 1
        assert suggestions[0].test_nodeid == 'test.py::test_fn'
        assert suggestions[0].suggested_size == TestSize.SMALL
        assert 'no external resources' in suggestions[0].reason.lower()

    def it_suggests_medium_for_test_with_network_access(self) -> None:
        """Suggests medium for tests with network access."""
        collector = SuggestionCollector()
        collector.record_current_size('test.py::test_fn', None)
        collector.record_observation('test.py::test_fn', ResourceType.NETWORK, 'Connection to api.example.com')

        suggestions = collector.generate_suggestions()

        assert len(suggestions) == 1
        assert suggestions[0].suggested_size == TestSize.MEDIUM
        assert 'network' in suggestions[0].reason.lower()

    def it_suggests_medium_for_test_with_filesystem_access(self) -> None:
        """Suggests medium for tests with filesystem access."""
        collector = SuggestionCollector()
        collector.record_current_size('test.py::test_fn', None)
        collector.record_observation('test.py::test_fn', ResourceType.FILESYSTEM, 'Read /etc/passwd')

        suggestions = collector.generate_suggestions()

        assert len(suggestions) == 1
        assert suggestions[0].suggested_size == TestSize.MEDIUM
        assert 'filesystem' in suggestions[0].reason.lower()

    def it_suggests_medium_for_test_with_subprocess_access(self) -> None:
        """Suggests medium for tests with subprocess access."""
        collector = SuggestionCollector()
        collector.record_current_size('test.py::test_fn', None)
        collector.record_observation('test.py::test_fn', ResourceType.SUBPROCESS, 'subprocess.run: git status')

        suggestions = collector.generate_suggestions()

        assert len(suggestions) == 1
        assert suggestions[0].suggested_size == TestSize.MEDIUM
        assert 'subprocess' in suggestions[0].reason.lower()

    def it_suggests_medium_for_test_with_database_access(self) -> None:
        """Suggests medium for tests with database access."""
        collector = SuggestionCollector()
        collector.record_current_size('test.py::test_fn', None)
        collector.record_observation('test.py::test_fn', ResourceType.DATABASE, 'PostgreSQL connection')

        suggestions = collector.generate_suggestions()

        assert len(suggestions) == 1
        assert suggestions[0].suggested_size == TestSize.MEDIUM
        assert 'database' in suggestions[0].reason.lower()

    def it_suggests_medium_for_test_with_sleep_calls(self) -> None:
        """Suggests medium for tests with sleep calls."""
        collector = SuggestionCollector()
        collector.record_current_size('test.py::test_fn', None)
        collector.record_observation('test.py::test_fn', ResourceType.SLEEP, 'time.sleep(1.0)')

        suggestions = collector.generate_suggestions()

        assert len(suggestions) == 1
        assert suggestions[0].suggested_size == TestSize.MEDIUM
        assert 'sleep' in suggestions[0].reason.lower()

    def it_suggests_medium_for_slow_test_over_1_second(self) -> None:
        """Suggests medium for tests taking more than 1 second."""
        collector = SuggestionCollector()
        collector.record_current_size('test.py::test_fn', None)
        collector.record_execution_time('test.py::test_fn', 1.5)

        suggestions = collector.generate_suggestions()

        assert len(suggestions) == 1
        assert suggestions[0].suggested_size == TestSize.MEDIUM
        assert 'duration' in suggestions[0].reason.lower() or 'slow' in suggestions[0].reason.lower()

    def it_suggests_large_for_test_with_multiple_resource_types(self) -> None:
        """Suggests large for tests accessing multiple resource types."""
        collector = SuggestionCollector()
        collector.record_current_size('test.py::test_fn', None)
        collector.record_observation('test.py::test_fn', ResourceType.NETWORK, 'Connection')
        collector.record_observation('test.py::test_fn', ResourceType.DATABASE, 'DB connection')

        suggestions = collector.generate_suggestions()

        assert len(suggestions) == 1
        assert suggestions[0].suggested_size == TestSize.LARGE
        assert 'multiple' in suggestions[0].reason.lower() or 'network' in suggestions[0].reason.lower()

    def it_suggests_large_for_very_slow_test_over_5_minutes(self) -> None:
        """Suggests large for tests taking more than 5 minutes."""
        collector = SuggestionCollector()
        collector.record_current_size('test.py::test_fn', None)
        collector.record_execution_time('test.py::test_fn', 350)  # 5+ minutes

        suggestions = collector.generate_suggestions()

        assert len(suggestions) == 1
        assert suggestions[0].suggested_size == TestSize.LARGE

    def it_identifies_mismatched_small_that_should_be_medium(self) -> None:
        """Identifies @small tests that should be @medium due to resources."""
        collector = SuggestionCollector()
        collector.record_current_size('test.py::test_fn', TestSize.SMALL)
        collector.record_observation('test.py::test_fn', ResourceType.NETWORK, 'Connection')

        suggestions = collector.generate_suggestions()

        assert len(suggestions) == 1
        assert suggestions[0].current_size == TestSize.SMALL
        assert suggestions[0].suggested_size == TestSize.MEDIUM

    def it_identifies_medium_that_could_be_small(self) -> None:
        """Identifies @medium tests that could be @small if no resources used."""
        collector = SuggestionCollector()
        collector.record_current_size('test.py::test_fn', TestSize.MEDIUM)
        collector.record_execution_time('test.py::test_fn', 0.05)
        # No observations recorded - test didn't use any external resources

        suggestions = collector.generate_suggestions()

        assert len(suggestions) == 1
        assert suggestions[0].current_size == TestSize.MEDIUM
        assert suggestions[0].suggested_size == TestSize.SMALL

    def it_does_not_suggest_when_current_matches_suggested(self) -> None:
        """Does not generate suggestion when current category matches behavior."""
        collector = SuggestionCollector()
        collector.record_current_size('test.py::test_fn', TestSize.SMALL)
        collector.record_execution_time('test.py::test_fn', 0.05)
        # No observations - test is correctly categorized as small

        suggestions = collector.generate_suggestions()

        assert len(suggestions) == 0

    def it_generates_suggestions_for_multiple_tests(self) -> None:
        """Generates suggestions for multiple tests in the collector."""
        collector = SuggestionCollector()

        # Test 1: uncategorized, should be small
        collector.record_current_size('test1.py::test_a', None)
        collector.record_execution_time('test1.py::test_a', 0.05)

        # Test 2: small but uses network, should be medium
        collector.record_current_size('test2.py::test_b', TestSize.SMALL)
        collector.record_observation('test2.py::test_b', ResourceType.NETWORK, 'Connection')

        # Test 3: correctly categorized as medium
        collector.record_current_size('test3.py::test_c', TestSize.MEDIUM)
        collector.record_observation('test3.py::test_c', ResourceType.FILESYSTEM, 'Read file')

        suggestions = collector.generate_suggestions()

        # Should have 2 suggestions (test1 and test2, not test3)
        assert len(suggestions) == 2
        nodeids = {s.test_nodeid for s in suggestions}
        assert 'test1.py::test_a' in nodeids
        assert 'test2.py::test_b' in nodeids
        assert 'test3.py::test_c' not in nodeids
