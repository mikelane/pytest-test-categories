"""Unit tests for violation tracking module.

This module tests the ViolationTracker and related data structures for
tracking hermeticity violations during test execution.
"""

from __future__ import annotations

import pytest

from pytest_test_categories.violation_tracking import (
    ViolationRecord,
    ViolationTracker,
    ViolationType,
)


@pytest.mark.small
class DescribeViolationType:
    """Test suite for ViolationType enum."""

    def it_has_network_violation_type(self) -> None:
        """ViolationType has a NETWORK variant."""
        assert ViolationType.NETWORK.value == 'network'

    def it_has_filesystem_violation_type(self) -> None:
        """ViolationType has a FILESYSTEM variant."""
        assert ViolationType.FILESYSTEM.value == 'filesystem'

    def it_has_process_violation_type(self) -> None:
        """ViolationType has a PROCESS variant."""
        assert ViolationType.PROCESS.value == 'process'

    def it_has_database_violation_type(self) -> None:
        """ViolationType has a DATABASE variant."""
        assert ViolationType.DATABASE.value == 'database'

    def it_has_sleep_violation_type(self) -> None:
        """ViolationType has a SLEEP variant."""
        assert ViolationType.SLEEP.value == 'sleep'

    def it_has_display_name_property(self) -> None:
        """ViolationType has a display_name property for terminal output."""
        assert ViolationType.NETWORK.display_name == 'Network'
        assert ViolationType.FILESYSTEM.display_name == 'Filesystem'
        assert ViolationType.PROCESS.display_name == 'Process'
        assert ViolationType.DATABASE.display_name == 'Database'
        assert ViolationType.SLEEP.display_name == 'Sleep'


@pytest.mark.small
class DescribeViolationRecord:
    """Test suite for ViolationRecord data class."""

    def it_stores_violation_type(self) -> None:
        """ViolationRecord stores violation type."""
        record = ViolationRecord(
            violation_type=ViolationType.NETWORK,
            test_nodeid='test_api.py::test_fetch',
            details='Attempted connection to example.com:443',
        )

        assert record.violation_type == ViolationType.NETWORK

    def it_stores_test_nodeid(self) -> None:
        """ViolationRecord stores test nodeid."""
        record = ViolationRecord(
            violation_type=ViolationType.FILESYSTEM,
            test_nodeid='test_config.py::test_load',
            details='Attempted read on /etc/passwd',
        )

        assert record.test_nodeid == 'test_config.py::test_load'

    def it_stores_details(self) -> None:
        """ViolationRecord stores violation details."""
        record = ViolationRecord(
            violation_type=ViolationType.PROCESS,
            test_nodeid='test_cmd.py::test_run',
            details='Attempted subprocess.run: git status',
        )

        assert record.details == 'Attempted subprocess.run: git status'

    def it_is_immutable(self) -> None:
        """ViolationRecord is immutable (frozen)."""
        record = ViolationRecord(
            violation_type=ViolationType.DATABASE,
            test_nodeid='test_db.py::test_query',
            details='Attempted sqlite3 connection',
        )

        with pytest.raises(Exception):  # noqa: B017, PT011 - Pydantic ValidationError or frozen error
            record.test_nodeid = 'other_test'  # type: ignore[misc]


@pytest.mark.small
class DescribeViolationTracker:
    """Test suite for ViolationTracker."""

    def it_starts_with_empty_violations(self) -> None:
        """New ViolationTracker has no violations."""
        tracker = ViolationTracker()

        assert tracker.total_violations == 0

    def it_records_violation(self) -> None:
        """ViolationTracker can record a violation."""
        tracker = ViolationTracker()

        tracker.record_violation(
            violation_type=ViolationType.NETWORK,
            test_nodeid='test_api.py::test_fetch',
            details='Attempted connection to example.com:443',
        )

        assert tracker.total_violations == 1

    def it_records_multiple_violations_of_same_type(self) -> None:
        """ViolationTracker can record multiple violations of the same type."""
        tracker = ViolationTracker()

        tracker.record_violation(
            ViolationType.NETWORK,
            'test_api.py::test_fetch',
            'Attempted connection to example.com:443',
        )
        tracker.record_violation(
            ViolationType.NETWORK,
            'test_client.py::test_connect',
            'Attempted connection to api.github.com:443',
        )

        assert tracker.total_violations == 2
        assert tracker.count_by_type(ViolationType.NETWORK) == 2

    def it_records_violations_of_different_types(self) -> None:
        """ViolationTracker can record violations of different types."""
        tracker = ViolationTracker()

        tracker.record_violation(ViolationType.NETWORK, 'test_api.py::test_fetch', 'network details')
        tracker.record_violation(ViolationType.FILESYSTEM, 'test_config.py::test_load', 'filesystem details')
        tracker.record_violation(ViolationType.DATABASE, 'test_repo.py::test_query', 'database details')

        assert tracker.total_violations == 3
        assert tracker.count_by_type(ViolationType.NETWORK) == 1
        assert tracker.count_by_type(ViolationType.FILESYSTEM) == 1
        assert tracker.count_by_type(ViolationType.DATABASE) == 1

    def it_returns_zero_for_empty_type(self) -> None:
        """count_by_type returns 0 for types with no violations."""
        tracker = ViolationTracker()

        tracker.record_violation(ViolationType.NETWORK, 'test_api.py::test_fetch', 'details')

        assert tracker.count_by_type(ViolationType.PROCESS) == 0
        assert tracker.count_by_type(ViolationType.SLEEP) == 0

    def it_gets_violations_by_type(self) -> None:
        """ViolationTracker can retrieve violations by type."""
        tracker = ViolationTracker()

        tracker.record_violation(ViolationType.NETWORK, 'test_api.py::test_fetch', 'network1')
        tracker.record_violation(ViolationType.FILESYSTEM, 'test_config.py::test_load', 'filesystem1')
        tracker.record_violation(ViolationType.NETWORK, 'test_client.py::test_connect', 'network2')

        network_violations = tracker.get_violations_by_type(ViolationType.NETWORK)

        assert len(network_violations) == 2
        assert all(v.violation_type == ViolationType.NETWORK for v in network_violations)

    def it_gets_test_nodeids_by_type(self) -> None:
        """ViolationTracker can get list of test nodeids for a violation type."""
        tracker = ViolationTracker()

        tracker.record_violation(ViolationType.NETWORK, 'test_api.py::test_fetch', 'details')
        tracker.record_violation(ViolationType.NETWORK, 'test_client.py::test_connect', 'details')

        nodeids = tracker.get_test_nodeids_by_type(ViolationType.NETWORK)

        assert nodeids == ['test_api.py::test_fetch', 'test_client.py::test_connect']

    def it_checks_if_has_violations(self) -> None:
        """ViolationTracker has has_violations property."""
        tracker = ViolationTracker()

        assert tracker.has_violations is False

        tracker.record_violation(ViolationType.SLEEP, 'test_timing.py::test_wait', 'details')

        assert tracker.has_violations is True

    def it_gets_unique_test_count(self) -> None:
        """ViolationTracker can count unique tests with violations."""
        tracker = ViolationTracker()

        # Same test with multiple violation types
        tracker.record_violation(ViolationType.NETWORK, 'test_api.py::test_fetch', 'details1')
        tracker.record_violation(ViolationType.DATABASE, 'test_api.py::test_fetch', 'details2')
        # Different test
        tracker.record_violation(ViolationType.NETWORK, 'test_client.py::test_connect', 'details3')

        assert tracker.unique_test_count == 2

    def it_tracks_failed_tests_for_strict_mode(self) -> None:
        """ViolationTracker can track which tests failed due to violations."""
        tracker = ViolationTracker()

        tracker.record_violation(ViolationType.NETWORK, 'test_api.py::test_fetch', 'details', failed=True)
        tracker.record_violation(ViolationType.NETWORK, 'test_client.py::test_connect', 'details', failed=False)

        failed_tests = tracker.get_failed_tests()

        assert 'test_api.py::test_fetch' in failed_tests
        assert 'test_client.py::test_connect' not in failed_tests
