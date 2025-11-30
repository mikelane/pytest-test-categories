"""JSON report models for CI/CD integration.

This module provides Pydantic models for generating JSON reports of test size
distribution and timing data. The JSON format is designed for consumption by
CI/CD systems, dashboards, and custom tooling.

Example usage:
    pytest --test-size-report=json --test-size-report-file=report.json

The JSON output includes:
- Plugin version
- Timestamp in ISO 8601 format
- Summary with distribution statistics and violations
- Per-test details (optional)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
)

from pytest_test_categories.distribution.stats import DISTRIBUTION_TARGETS
from pytest_test_categories.types import TestSize

if TYPE_CHECKING:
    from pytest_test_categories.distribution.stats import DistributionStats
    from pytest_test_categories.reporting import TestSizeReport
    from pytest_test_categories.violations import ViolationTracker


class DistributionSizeEntry(BaseModel):
    """Distribution statistics for a single test size category.

    Represents the count, percentage, and target for a test size category
    in the JSON report output.
    """

    model_config = ConfigDict(frozen=True)

    count: int = Field(ge=0)
    percentage: float = Field(ge=0.0, le=100.0)
    target: float = Field(ge=0.0, le=100.0)


class HermeticityViolationsSummary(BaseModel):
    """Summary of hermeticity violations by type.

    Tracks counts of each hermeticity violation type (network, filesystem,
    process, database, sleep) for inclusion in the JSON report.
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
        """Calculate the total number of hermeticity violations."""
        return self.network + self.filesystem + self.process + self.database + self.sleep


class ViolationsSummary(BaseModel):
    """Summary of test violations.

    Tracks counts of timing and hermeticity violations across
    all tests in the suite.
    """

    model_config = ConfigDict(frozen=True)

    timing: int = Field(default=0, ge=0)
    hermeticity: HermeticityViolationsSummary = Field(default_factory=HermeticityViolationsSummary)


class JsonReportSummary(BaseModel):
    """Summary section of the JSON report.

    Contains aggregate statistics about the test suite including
    total tests, distribution by size, and violation counts.
    """

    model_config = ConfigDict(frozen=True)

    total_tests: int = Field(ge=0)
    distribution: dict[str, DistributionSizeEntry]
    violations: ViolationsSummary


class JsonTestEntry(BaseModel):
    """Individual test entry in the JSON report.

    Contains details about a single test including its name, size,
    duration, status, and any violations.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    size: str
    duration: float | None
    status: str
    violations: list[str]


class JsonReport(BaseModel):
    """Complete JSON report for CI/CD integration.

    This is the root model for the JSON report output. It contains:
    - version: The plugin version
    - timestamp: When the report was generated (ISO 8601 format)
    - summary: Aggregate statistics
    - tests: Per-test details
    """

    model_config = ConfigDict(frozen=True)

    version: str
    timestamp: datetime
    summary: JsonReportSummary
    tests: list[JsonTestEntry]

    @classmethod
    def from_test_size_report(
        cls,
        test_report: TestSizeReport,
        distribution_stats: DistributionStats,
        version: str,
        violation_tracker: ViolationTracker | None = None,
    ) -> JsonReport:
        """Create a JsonReport from a TestSizeReport and DistributionStats.

        Args:
            test_report: The TestSizeReport containing test data.
            distribution_stats: The DistributionStats with count data.
            version: The plugin version string.
            violation_tracker: Optional ViolationTracker with hermeticity violations.

        Returns:
            A JsonReport instance ready for serialization.

        """
        timestamp = datetime.now(tz=UTC)
        counts = distribution_stats.counts
        percentages = distribution_stats.calculate_percentages()

        distribution = {
            'small': DistributionSizeEntry(
                count=counts.small,
                percentage=percentages.small,
                target=DISTRIBUTION_TARGETS['small'].target,
            ),
            'medium': DistributionSizeEntry(
                count=counts.medium,
                percentage=percentages.medium,
                target=DISTRIBUTION_TARGETS['medium'].target,
            ),
            'large': DistributionSizeEntry(
                count=counts.large,
                percentage=percentages.large,
                target=DISTRIBUTION_TARGETS['large_xlarge'].target * 0.8,
            ),
            'xlarge': DistributionSizeEntry(
                count=counts.xlarge,
                percentage=percentages.xlarge,
                target=DISTRIBUTION_TARGETS['large_xlarge'].target * 0.2,
            ),
        }

        timing_violations = 0
        tests: list[JsonTestEntry] = []

        for size in TestSize:
            for nodeid in test_report.sized_tests[size]:
                violations: list[str] = []
                duration = test_report.test_durations.get(nodeid)
                outcome = test_report.test_outcomes.get(nodeid, 'unknown')

                if test_report.exceeds_time_limit(nodeid, size):
                    violations.append('timing')
                    timing_violations += 1

                if violation_tracker is not None:
                    test_violations = violation_tracker.get_test_violations(nodeid)
                    violations.extend(f'hermeticity:{vtype.value}' for vtype in test_violations)

                tests.append(
                    JsonTestEntry(
                        name=nodeid,
                        size=size.value,
                        duration=duration,
                        status=outcome,
                        violations=violations,
                    )
                )

        for nodeid in test_report.unsized_tests:
            duration = test_report.test_durations.get(nodeid)
            outcome = test_report.test_outcomes.get(nodeid, 'unknown')
            violations = []

            if violation_tracker is not None:
                test_violations = violation_tracker.get_test_violations(nodeid)
                violations.extend(f'hermeticity:{vtype.value}' for vtype in test_violations)

            tests.append(
                JsonTestEntry(
                    name=nodeid,
                    size='unsized',
                    duration=duration,
                    status=outcome,
                    violations=violations,
                )
            )

        total_tests = test_report.get_total_tests()

        hermeticity_summary = HermeticityViolationsSummary()
        if violation_tracker is not None:
            summary_data = violation_tracker.get_summary()
            hermeticity_summary = HermeticityViolationsSummary(
                network=summary_data.network,
                filesystem=summary_data.filesystem,
                process=summary_data.process,
                database=summary_data.database,
                sleep=summary_data.sleep,
            )

        summary = JsonReportSummary(
            total_tests=total_tests,
            distribution=distribution,
            violations=ViolationsSummary(timing=timing_violations, hermeticity=hermeticity_summary),
        )

        return cls(
            version=version,
            timestamp=timestamp,
            summary=summary,
            tests=tests,
        )
