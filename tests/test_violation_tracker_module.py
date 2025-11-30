"""Unit tests for ViolationTracker and hermeticity violation tracking.

This module tests the violation tracking system that records hermeticity
violations (network, filesystem, process, database, sleep) during test
execution for inclusion in JSON reports.
"""

from __future__ import annotations

import pytest

from pytest_test_categories.violations import (
    HermeticityViolations,
    ViolationTracker,
    ViolationType,
)


@pytest.mark.small
class DescribeViolationType:
    """Test suite for ViolationType enum."""

    def it_has_all_violation_types(self) -> None:
        """Verify all expected violation types exist."""
        assert ViolationType.NETWORK.value == 'network'
        assert ViolationType.FILESYSTEM.value == 'filesystem'
        assert ViolationType.PROCESS.value == 'process'
        assert ViolationType.DATABASE.value == 'database'
        assert ViolationType.SLEEP.value == 'sleep'


@pytest.mark.small
class DescribeHermeticityViolations:
    """Test suite for HermeticityViolations model."""

    def it_initializes_with_zero_counts(self) -> None:
        """Initialize with all violation counts at zero."""
        violations = HermeticityViolations()

        assert violations.network == 0
        assert violations.filesystem == 0
        assert violations.process == 0
        assert violations.database == 0
        assert violations.sleep == 0

    def it_calculates_total_correctly(self) -> None:
        """Calculate total from all violation types."""
        violations = HermeticityViolations(
            network=3,
            filesystem=2,
            process=0,
            database=1,
            sleep=0,
        )

        assert violations.total == 6

    def it_is_frozen(self) -> None:
        """Verify the model is immutable."""
        from pydantic import ValidationError

        violations = HermeticityViolations()

        with pytest.raises(ValidationError, match='frozen'):
            violations.network = 5

    def it_converts_to_dict(self) -> None:
        """Convert to dictionary for JSON serialization."""
        violations = HermeticityViolations(
            network=3,
            filesystem=2,
            process=0,
            database=1,
            sleep=0,
        )

        result = violations.model_dump()

        assert result == {
            'network': 3,
            'filesystem': 2,
            'process': 0,
            'database': 1,
            'sleep': 0,
            'total': 6,
        }


@pytest.mark.small
class DescribeViolationTracker:
    """Test suite for ViolationTracker."""

    def it_initializes_empty(self) -> None:
        """Initialize with no violations recorded."""
        tracker = ViolationTracker()

        assert tracker.get_summary().total == 0
        assert tracker.get_test_violations('test_foo') == []

    def it_records_network_violation(self) -> None:
        """Record a network violation for a test."""
        tracker = ViolationTracker()

        tracker.record_violation('test_example::test_foo', ViolationType.NETWORK)

        assert tracker.get_summary().network == 1
        assert ViolationType.NETWORK in tracker.get_test_violations('test_example::test_foo')

    def it_records_filesystem_violation(self) -> None:
        """Record a filesystem violation for a test."""
        tracker = ViolationTracker()

        tracker.record_violation('test_example::test_bar', ViolationType.FILESYSTEM)

        assert tracker.get_summary().filesystem == 1
        assert ViolationType.FILESYSTEM in tracker.get_test_violations('test_example::test_bar')

    def it_records_process_violation(self) -> None:
        """Record a process violation for a test."""
        tracker = ViolationTracker()

        tracker.record_violation('test_example::test_baz', ViolationType.PROCESS)

        assert tracker.get_summary().process == 1
        assert ViolationType.PROCESS in tracker.get_test_violations('test_example::test_baz')

    def it_records_database_violation(self) -> None:
        """Record a database violation for a test."""
        tracker = ViolationTracker()

        tracker.record_violation('test_example::test_db', ViolationType.DATABASE)

        assert tracker.get_summary().database == 1
        assert ViolationType.DATABASE in tracker.get_test_violations('test_example::test_db')

    def it_records_sleep_violation(self) -> None:
        """Record a sleep violation for a test."""
        tracker = ViolationTracker()

        tracker.record_violation('test_example::test_sleep', ViolationType.SLEEP)

        assert tracker.get_summary().sleep == 1
        assert ViolationType.SLEEP in tracker.get_test_violations('test_example::test_sleep')

    def it_records_multiple_violations_for_same_test(self) -> None:
        """Record multiple violations for the same test."""
        tracker = ViolationTracker()

        tracker.record_violation('test_foo', ViolationType.NETWORK)
        tracker.record_violation('test_foo', ViolationType.FILESYSTEM)
        tracker.record_violation('test_foo', ViolationType.DATABASE)

        violations = tracker.get_test_violations('test_foo')
        assert len(violations) == 3
        assert ViolationType.NETWORK in violations
        assert ViolationType.FILESYSTEM in violations
        assert ViolationType.DATABASE in violations

    def it_records_violations_across_multiple_tests(self) -> None:
        """Record violations across multiple tests."""
        tracker = ViolationTracker()

        tracker.record_violation('test_one', ViolationType.NETWORK)
        tracker.record_violation('test_two', ViolationType.NETWORK)
        tracker.record_violation('test_three', ViolationType.FILESYSTEM)

        summary = tracker.get_summary()
        assert summary.network == 2
        assert summary.filesystem == 1
        assert summary.total == 3

    def it_returns_empty_list_for_unknown_test(self) -> None:
        """Return empty list for test with no recorded violations."""
        tracker = ViolationTracker()

        violations = tracker.get_test_violations('unknown_test')

        assert violations == []

    def it_records_same_violation_type_multiple_times(self) -> None:
        """Record the same violation type multiple times for a test."""
        tracker = ViolationTracker()

        tracker.record_violation('test_foo', ViolationType.NETWORK)
        tracker.record_violation('test_foo', ViolationType.NETWORK)

        violations = tracker.get_test_violations('test_foo')
        assert len(violations) == 2
        assert tracker.get_summary().network == 2

    def it_resets_to_initial_state(self) -> None:
        """Reset tracker to initial empty state."""
        tracker = ViolationTracker()
        tracker.record_violation('test_foo', ViolationType.NETWORK)
        tracker.record_violation('test_bar', ViolationType.DATABASE)

        tracker.reset()

        assert tracker.get_summary().total == 0
        assert tracker.get_test_violations('test_foo') == []
        assert tracker.get_test_violations('test_bar') == []
