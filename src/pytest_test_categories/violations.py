"""Hermeticity violation tracking for JSON reports.

This module provides models and tracking for hermeticity violations
(network, filesystem, process, database, sleep) that occur during test
execution. These violations are collected and included in JSON reports
for CI/CD integration.

Example usage:
    tracker = ViolationTracker()
    tracker.record_violation('test_foo', ViolationType.NETWORK)
    summary = tracker.get_summary()
    # summary.network == 1, summary.total == 1
"""

from __future__ import annotations

from collections import defaultdict
from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
)


class ViolationType(StrEnum):
    """Types of hermeticity violations that can occur during test execution.

    Each violation type corresponds to a resource that small tests are
    not permitted to access according to Google's test size definitions.
    """

    NETWORK = 'network'
    FILESYSTEM = 'filesystem'
    PROCESS = 'process'
    DATABASE = 'database'
    SLEEP = 'sleep'


class HermeticityViolations(BaseModel):
    """Summary of hermeticity violations by type.

    This is an immutable (frozen) model that holds the count of each
    violation type and computes the total automatically.

    Attributes:
        network: Count of network access violations.
        filesystem: Count of filesystem access violations.
        process: Count of subprocess/process spawning violations.
        database: Count of database connection violations.
        sleep: Count of sleep call violations.
        total: Computed total of all violation types.

    """

    model_config = ConfigDict(frozen=True)

    network: int = Field(default=0, ge=0)
    filesystem: int = Field(default=0, ge=0)
    process: int = Field(default=0, ge=0)
    database: int = Field(default=0, ge=0)
    sleep: int = Field(default=0, ge=0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total(self) -> int:
        """Calculate the total number of violations across all types."""
        return self.network + self.filesystem + self.process + self.database + self.sleep


class ViolationTracker:
    """Tracks hermeticity violations during test execution.

    This class collects violations as they occur during test runs and
    provides methods to retrieve both aggregate summaries and per-test
    violation details for inclusion in JSON reports.

    The tracker is designed to be used as a singleton per test session,
    stored in PluginState.

    Example:
        >>> tracker = ViolationTracker()
        >>> tracker.record_violation('test_foo', ViolationType.NETWORK)
        >>> tracker.record_violation('test_foo', ViolationType.DATABASE)
        >>> tracker.get_summary().total
        2
        >>> tracker.get_test_violations('test_foo')
        [<ViolationType.NETWORK: 'network'>, <ViolationType.DATABASE: 'database'>]

    """

    def __init__(self) -> None:
        """Initialize an empty violation tracker."""
        self._violations_by_test: dict[str, list[ViolationType]] = defaultdict(list)
        self._counts: dict[ViolationType, int] = dict.fromkeys(ViolationType, 0)

    def record_violation(self, test_nodeid: str, violation_type: ViolationType) -> None:
        """Record a hermeticity violation for a test.

        Args:
            test_nodeid: The pytest node ID of the test that caused the violation.
            violation_type: The type of violation that occurred.

        """
        self._violations_by_test[test_nodeid].append(violation_type)
        self._counts[violation_type] += 1

    def get_summary(self) -> HermeticityViolations:
        """Get a summary of all violations by type.

        Returns:
            An immutable HermeticityViolations model with counts for each
            violation type and a computed total.

        """
        return HermeticityViolations(
            network=self._counts[ViolationType.NETWORK],
            filesystem=self._counts[ViolationType.FILESYSTEM],
            process=self._counts[ViolationType.PROCESS],
            database=self._counts[ViolationType.DATABASE],
            sleep=self._counts[ViolationType.SLEEP],
        )

    def get_test_violations(self, test_nodeid: str) -> list[ViolationType]:
        """Get the list of violations for a specific test.

        Args:
            test_nodeid: The pytest node ID of the test.

        Returns:
            A list of ViolationType values for the test. Returns an empty
            list if the test has no recorded violations.

        """
        return list(self._violations_by_test.get(test_nodeid, []))

    def reset(self) -> None:
        """Reset the tracker to its initial empty state.

        This clears all recorded violations and resets counts to zero.

        """
        self._violations_by_test.clear()
        self._counts = dict.fromkeys(ViolationType, 0)
