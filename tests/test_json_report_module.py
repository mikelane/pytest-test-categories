"""Unit tests for JSON report models.

This module tests the JSON report Pydantic models in isolation.
These models define the structure for JSON export of test size
distribution and timing data.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from pytest_test_categories.distribution.stats import DistributionStats
from pytest_test_categories.json_report import (
    DistributionSizeEntry,
    JsonReport,
    JsonReportSummary,
    JsonTestEntry,
    ViolationsSummary,
)
from pytest_test_categories.reporting import TestSizeReport
from pytest_test_categories.types import TestSize


@pytest.mark.small
class DescribeDistributionSizeEntry:
    """Test suite for DistributionSizeEntry model."""

    def it_creates_entry_with_all_fields(self) -> None:
        """Create a distribution size entry with count, percentage, and target."""
        entry = DistributionSizeEntry(count=80, percentage=80.0, target=80.0)

        assert entry.count == 80
        assert entry.percentage == 80.0
        assert entry.target == 80.0

    def it_validates_count_is_non_negative(self) -> None:
        """Validate that count cannot be negative."""
        with pytest.raises(ValueError, match='greater than or equal to 0'):
            DistributionSizeEntry(count=-1, percentage=80.0, target=80.0)

    def it_validates_percentage_range(self) -> None:
        """Validate that percentage is between 0 and 100."""
        with pytest.raises(ValueError, match='less than or equal to 100'):
            DistributionSizeEntry(count=80, percentage=101.0, target=80.0)

        with pytest.raises(ValueError, match='greater than or equal to 0'):
            DistributionSizeEntry(count=80, percentage=-1.0, target=80.0)

    def it_serializes_to_dict(self) -> None:
        """Serialize entry to dictionary format."""
        entry = DistributionSizeEntry(count=80, percentage=80.0, target=80.0)

        result = entry.model_dump()

        assert result == {'count': 80, 'percentage': 80.0, 'target': 80.0}


@pytest.mark.small
class DescribeViolationsSummary:
    """Test suite for ViolationsSummary model."""

    def it_creates_with_default_values(self) -> None:
        """Create violations summary with default values of 0."""
        violations = ViolationsSummary()

        assert violations.timing == 0
        assert violations.hermeticity == 0

    def it_creates_with_custom_values(self) -> None:
        """Create violations summary with custom values."""
        violations = ViolationsSummary(timing=3, hermeticity=1)

        assert violations.timing == 3
        assert violations.hermeticity == 1

    def it_serializes_to_dict(self) -> None:
        """Serialize violations summary to dictionary format."""
        violations = ViolationsSummary(timing=2, hermeticity=1)

        result = violations.model_dump()

        assert result == {'timing': 2, 'hermeticity': 1}


@pytest.mark.small
class DescribeJsonReportSummary:
    """Test suite for JsonReportSummary model."""

    def it_creates_summary_with_all_fields(self) -> None:
        """Create summary with total tests, distribution, and violations."""
        summary = JsonReportSummary(
            total_tests=100,
            distribution={
                'small': DistributionSizeEntry(count=80, percentage=80.0, target=80.0),
                'medium': DistributionSizeEntry(count=15, percentage=15.0, target=15.0),
                'large': DistributionSizeEntry(count=4, percentage=4.0, target=4.0),
                'xlarge': DistributionSizeEntry(count=1, percentage=1.0, target=1.0),
            },
            violations=ViolationsSummary(timing=2, hermeticity=0),
        )

        assert summary.total_tests == 100
        assert summary.distribution['small'].count == 80
        assert summary.violations.timing == 2

    def it_serializes_to_dict(self) -> None:
        """Serialize summary to dictionary format."""
        summary = JsonReportSummary(
            total_tests=100,
            distribution={
                'small': DistributionSizeEntry(count=80, percentage=80.0, target=80.0),
                'medium': DistributionSizeEntry(count=15, percentage=15.0, target=15.0),
                'large': DistributionSizeEntry(count=4, percentage=4.0, target=4.0),
                'xlarge': DistributionSizeEntry(count=1, percentage=1.0, target=1.0),
            },
            violations=ViolationsSummary(timing=0, hermeticity=0),
        )

        result = summary.model_dump()

        assert result['total_tests'] == 100
        assert result['distribution']['small']['count'] == 80


@pytest.mark.small
class DescribeJsonTestEntry:
    """Test suite for JsonTestEntry model."""

    def it_creates_test_entry_with_all_fields(self) -> None:
        """Create test entry with name, size, duration, status, and violations."""
        entry = JsonTestEntry(
            name='test_example.py::test_one',
            size='small',
            duration=0.032,
            status='passed',
            violations=[],
        )

        assert entry.name == 'test_example.py::test_one'
        assert entry.size == 'small'
        assert entry.duration == 0.032
        assert entry.status == 'passed'
        assert entry.violations == []

    def it_creates_test_entry_with_violations(self) -> None:
        """Create test entry with timing violation."""
        entry = JsonTestEntry(
            name='test_example.py::test_slow',
            size='small',
            duration=1.5,
            status='failed',
            violations=['timing'],
        )

        assert entry.violations == ['timing']

    def it_handles_none_duration(self) -> None:
        """Handle None duration for skipped tests."""
        entry = JsonTestEntry(
            name='test_example.py::test_skipped',
            size='small',
            duration=None,
            status='skipped',
            violations=[],
        )

        assert entry.duration is None

    def it_serializes_to_dict(self) -> None:
        """Serialize test entry to dictionary format."""
        entry = JsonTestEntry(
            name='test_example.py::test_one',
            size='small',
            duration=0.032,
            status='passed',
            violations=[],
        )

        result = entry.model_dump()

        assert result == {
            'name': 'test_example.py::test_one',
            'size': 'small',
            'duration': 0.032,
            'status': 'passed',
            'violations': [],
        }


@pytest.mark.small
class DescribeJsonReport:
    """Test suite for JsonReport model."""

    def it_creates_report_with_all_fields(self) -> None:
        """Create JSON report with version, timestamp, summary, and tests."""
        timestamp = datetime.now(tz=UTC)
        report = JsonReport(
            version='0.7.0',
            timestamp=timestamp,
            summary=JsonReportSummary(
                total_tests=1,
                distribution={
                    'small': DistributionSizeEntry(count=1, percentage=100.0, target=80.0),
                    'medium': DistributionSizeEntry(count=0, percentage=0.0, target=15.0),
                    'large': DistributionSizeEntry(count=0, percentage=0.0, target=4.0),
                    'xlarge': DistributionSizeEntry(count=0, percentage=0.0, target=1.0),
                },
                violations=ViolationsSummary(),
            ),
            tests=[
                JsonTestEntry(
                    name='test_example.py::test_one',
                    size='small',
                    duration=0.032,
                    status='passed',
                    violations=[],
                ),
            ],
        )

        assert report.version == '0.7.0'
        assert report.timestamp == timestamp
        assert report.summary.total_tests == 1
        assert len(report.tests) == 1

    def it_creates_report_without_tests(self) -> None:
        """Create JSON report with empty tests list."""
        timestamp = datetime.now(tz=UTC)
        report = JsonReport(
            version='0.7.0',
            timestamp=timestamp,
            summary=JsonReportSummary(
                total_tests=0,
                distribution={
                    'small': DistributionSizeEntry(count=0, percentage=0.0, target=80.0),
                    'medium': DistributionSizeEntry(count=0, percentage=0.0, target=15.0),
                    'large': DistributionSizeEntry(count=0, percentage=0.0, target=4.0),
                    'xlarge': DistributionSizeEntry(count=0, percentage=0.0, target=1.0),
                },
                violations=ViolationsSummary(),
            ),
            tests=[],
        )

        assert len(report.tests) == 0

    def it_serializes_to_json(self) -> None:
        """Serialize report to JSON string format."""
        timestamp = datetime(2025, 12, 15, 10, 30, 0, tzinfo=UTC)
        report = JsonReport(
            version='0.7.0',
            timestamp=timestamp,
            summary=JsonReportSummary(
                total_tests=1,
                distribution={
                    'small': DistributionSizeEntry(count=1, percentage=100.0, target=80.0),
                    'medium': DistributionSizeEntry(count=0, percentage=0.0, target=15.0),
                    'large': DistributionSizeEntry(count=0, percentage=0.0, target=4.0),
                    'xlarge': DistributionSizeEntry(count=0, percentage=0.0, target=1.0),
                },
                violations=ViolationsSummary(),
            ),
            tests=[],
        )

        result = report.model_dump_json(indent=2)

        assert '"version": "0.7.0"' in result
        assert '"2025-12-15T10:30:00Z"' in result

    def it_serializes_timestamp_in_iso_format(self) -> None:
        """Serialize timestamp in ISO 8601 format with Z suffix."""
        timestamp = datetime(2025, 12, 15, 10, 30, 0, tzinfo=UTC)
        report = JsonReport(
            version='0.7.0',
            timestamp=timestamp,
            summary=JsonReportSummary(
                total_tests=0,
                distribution={
                    'small': DistributionSizeEntry(count=0, percentage=0.0, target=80.0),
                    'medium': DistributionSizeEntry(count=0, percentage=0.0, target=15.0),
                    'large': DistributionSizeEntry(count=0, percentage=0.0, target=4.0),
                    'xlarge': DistributionSizeEntry(count=0, percentage=0.0, target=1.0),
                },
                violations=ViolationsSummary(),
            ),
            tests=[],
        )

        result = report.model_dump(mode='json')
        # Pydantic serializes datetime with Z suffix for UTC

        assert result['timestamp'] == '2025-12-15T10:30:00Z'


@pytest.mark.small
class DescribeJsonReportFromTestSizeReport:
    """Test suite for creating JsonReport from TestSizeReport."""

    def it_creates_json_report_from_test_size_report(self) -> None:
        """Create JSON report from TestSizeReport with distribution stats."""
        test_report = TestSizeReport()
        test_report.add_test('test_one.py::test_small', TestSize.SMALL, duration=0.032, outcome='passed')
        test_report.add_test('test_one.py::test_medium', TestSize.MEDIUM, duration=0.5, outcome='passed')

        stats = DistributionStats.update_counts({TestSize.SMALL: 1, TestSize.MEDIUM: 1})

        json_report = JsonReport.from_test_size_report(
            test_report=test_report,
            distribution_stats=stats,
            version='0.7.0',
        )

        assert json_report.version == '0.7.0'
        assert json_report.summary.total_tests == 2
        assert json_report.summary.distribution['small'].count == 1
        assert json_report.summary.distribution['medium'].count == 1
        assert len(json_report.tests) == 2

    def it_includes_timing_violations(self) -> None:
        """Include timing violations in JSON report."""
        test_report = TestSizeReport()
        test_report.add_test('test_slow.py::test_slow', TestSize.SMALL, duration=1.5, outcome='failed')

        stats = DistributionStats.update_counts({TestSize.SMALL: 1})

        json_report = JsonReport.from_test_size_report(
            test_report=test_report,
            distribution_stats=stats,
            version='0.7.0',
        )

        assert json_report.summary.violations.timing == 1
        assert 'timing' in json_report.tests[0].violations

    def it_handles_unsized_tests(self) -> None:
        """Handle unsized tests in JSON report."""
        test_report = TestSizeReport()
        test_report.add_test('test_one.py::test_unsized', None, duration=0.1, outcome='passed')

        stats = DistributionStats.update_counts({})

        json_report = JsonReport.from_test_size_report(
            test_report=test_report,
            distribution_stats=stats,
            version='0.7.0',
        )

        assert json_report.summary.total_tests == 1
        assert len(json_report.tests) == 1
        assert json_report.tests[0].size == 'unsized'
