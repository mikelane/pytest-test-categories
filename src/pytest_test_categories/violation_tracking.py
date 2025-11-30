"""Violation tracking for hermeticity enforcement.

This module provides data structures for tracking resource isolation violations
during test execution. It enables the plugin to collect violations in both
WARN and STRICT modes for terminal summary reporting.

The violation tracker follows hexagonal architecture principles:
- ViolationType: Enum defining the types of violations
- ViolationRecord: Immutable record of a single violation
- ViolationTracker: Service for collecting and querying violations

Example:
    >>> tracker = ViolationTracker()
    >>> tracker.record_violation(
    ...     ViolationType.NETWORK,
    ...     'test_api.py::test_fetch',
    ...     'Attempted connection to example.com:443'
    ... )
    >>> tracker.total_violations
    1
    >>> tracker.count_by_type(ViolationType.NETWORK)
    1

See Also:
    - exceptions.py: Exception classes for STRICT mode violations
    - ports/network.py: NetworkBlockerPort that uses this tracker

"""

from __future__ import annotations

from collections import defaultdict
from enum import StrEnum

from pydantic import BaseModel


class ViolationType(StrEnum):
    """Types of hermeticity violations that can be tracked.

    Each violation type corresponds to a resource category that tests
    may access inappropriately based on their size category.

    Attributes:
        NETWORK: Network access violation (socket connections)
        FILESYSTEM: Filesystem access violation (file I/O)
        PROCESS: Subprocess spawning violation
        DATABASE: Database connection violation
        SLEEP: Sleep/timing function violation

    """

    NETWORK = 'network'
    FILESYSTEM = 'filesystem'
    PROCESS = 'process'
    DATABASE = 'database'
    SLEEP = 'sleep'

    @property
    def display_name(self) -> str:
        """Get the human-readable display name for terminal output.

        Returns:
            Title-cased name suitable for terminal display.

        """
        return self.name.title()


class ViolationRecord(BaseModel, frozen=True):
    """Immutable record of a single hermeticity violation.

    Captures all information about a violation for reporting purposes.
    The record is immutable (frozen) to ensure it cannot be modified
    after creation.

    Attributes:
        violation_type: The type of resource violation.
        test_nodeid: The pytest node ID of the violating test.
        details: Human-readable description of the violation.
        failed: Whether this violation caused the test to fail (STRICT mode).

    Example:
        >>> record = ViolationRecord(
        ...     violation_type=ViolationType.NETWORK,
        ...     test_nodeid='test_api.py::test_fetch',
        ...     details='Attempted connection to example.com:443',
        ...     failed=False
        ... )

    """

    violation_type: ViolationType
    test_nodeid: str
    details: str
    failed: bool = False


class ViolationTracker:
    """Service for tracking hermeticity violations during test execution.

    This tracker collects violations from all resource blockers and provides
    query methods for terminal summary reporting. It is designed to work with
    both WARN and STRICT enforcement modes.

    The tracker maintains violations grouped by type for efficient querying
    and supports counting unique tests across all violation types.

    Example:
        >>> tracker = ViolationTracker()
        >>> tracker.record_violation(
        ...     ViolationType.NETWORK,
        ...     'test_api.py::test_fetch',
        ...     'Attempted connection to example.com:443'
        ... )
        >>> tracker.has_violations
        True
        >>> tracker.count_by_type(ViolationType.NETWORK)
        1

    """

    def __init__(self) -> None:
        """Initialize an empty violation tracker."""
        self._violations: dict[ViolationType, list[ViolationRecord]] = defaultdict(list)

    def record_violation(
        self,
        violation_type: ViolationType,
        test_nodeid: str,
        details: str,
        *,
        failed: bool = False,
    ) -> None:
        """Record a hermeticity violation.

        Args:
            violation_type: The type of resource violation.
            test_nodeid: The pytest node ID of the violating test.
            details: Human-readable description of the violation.
            failed: Whether this violation caused the test to fail (STRICT mode).

        """
        record = ViolationRecord(
            violation_type=violation_type,
            test_nodeid=test_nodeid,
            details=details,
            failed=failed,
        )
        self._violations[violation_type].append(record)

    @property
    def total_violations(self) -> int:
        """Get the total number of violations across all types.

        Returns:
            Total count of all recorded violations.

        """
        return sum(len(records) for records in self._violations.values())

    @property
    def has_violations(self) -> bool:
        """Check if any violations have been recorded.

        Returns:
            True if at least one violation has been recorded.

        """
        return self.total_violations > 0

    @property
    def unique_test_count(self) -> int:
        """Get the count of unique tests with violations.

        A test is counted once even if it has multiple violation types.

        Returns:
            Number of unique test nodeids with violations.

        """
        all_nodeids: set[str] = set()
        for records in self._violations.values():
            for record in records:
                all_nodeids.add(record.test_nodeid)
        return len(all_nodeids)

    def count_by_type(self, violation_type: ViolationType) -> int:
        """Get the count of violations for a specific type.

        Args:
            violation_type: The type to count violations for.

        Returns:
            Number of violations of the specified type.

        """
        return len(self._violations.get(violation_type, []))

    def get_violations_by_type(self, violation_type: ViolationType) -> list[ViolationRecord]:
        """Get all violations of a specific type.

        Args:
            violation_type: The type to retrieve violations for.

        Returns:
            List of ViolationRecord instances for the specified type.

        """
        return list(self._violations.get(violation_type, []))

    def get_test_nodeids_by_type(self, violation_type: ViolationType) -> list[str]:
        """Get the list of test nodeids for a specific violation type.

        Args:
            violation_type: The type to retrieve test nodeids for.

        Returns:
            List of test nodeids in the order they were recorded.

        """
        return [record.test_nodeid for record in self._violations.get(violation_type, [])]

    def get_failed_tests(self) -> set[str]:
        """Get the set of tests that failed due to violations (STRICT mode).

        Returns:
            Set of test nodeids that failed due to hermeticity violations.

        """
        failed: set[str] = set()
        for records in self._violations.values():
            for record in records:
                if record.failed:
                    failed.add(record.test_nodeid)
        return failed
