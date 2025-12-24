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
    HermeticityViolationsSummary,
    JsonReport,
    JsonReportSummary,
    JsonTestEntry,
    ViolationsSummary,
)
from pytest_test_categories.reporting import TestSizeReport
from pytest_test_categories.types import TestSize
from pytest_test_categories.violation_tracking import ViolationTracker, ViolationType


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
class DescribeHermeticityViolationsSummary:
    """Test suite for HermeticityViolationsSummary model."""

    def it_creates_with_default_values(self) -> None:
        """Create hermeticity violations summary with default values of 0."""
        hermeticity = HermeticityViolationsSummary()

        assert hermeticity.network == 0
        assert hermeticity.filesystem == 0
        assert hermeticity.process == 0
        assert hermeticity.database == 0
        assert hermeticity.sleep == 0
        assert hermeticity.total == 0

    def it_creates_with_custom_values(self) -> None:
        """Create hermeticity violations summary with custom values."""
        hermeticity = HermeticityViolationsSummary(
            network=2,
            filesystem=1,
            process=3,
            database=0,
            sleep=1,
        )

        assert hermeticity.network == 2
        assert hermeticity.filesystem == 1
        assert hermeticity.process == 3
        assert hermeticity.database == 0
        assert hermeticity.sleep == 1

    def it_computes_total_from_all_types(self) -> None:
        """Compute total from all violation types."""
        hermeticity = HermeticityViolationsSummary(
            network=2,
            filesystem=1,
            process=3,
            database=4,
            sleep=5,
        )

        assert hermeticity.total == 15

    def it_serializes_to_dict_with_total(self) -> None:
        """Serialize hermeticity violations summary to dictionary format with computed total."""
        hermeticity = HermeticityViolationsSummary(network=1, filesystem=2)

        result = hermeticity.model_dump()

        assert result == {
            'network': 1,
            'filesystem': 2,
            'process': 0,
            'database': 0,
            'sleep': 0,
            'total': 3,
        }


@pytest.mark.small
class DescribeViolationsSummary:
    """Test suite for ViolationsSummary model."""

    def it_creates_with_default_values(self) -> None:
        """Create violations summary with default values of 0."""
        violations = ViolationsSummary()

        assert violations.timing == 0
        assert violations.hermeticity.total == 0

    def it_creates_with_custom_hermeticity_values(self) -> None:
        """Create violations summary with custom hermeticity values."""
        hermeticity = HermeticityViolationsSummary(network=2, filesystem=1)
        violations = ViolationsSummary(timing=3, hermeticity=hermeticity)

        assert violations.timing == 3
        assert violations.hermeticity.network == 2
        assert violations.hermeticity.filesystem == 1
        assert violations.hermeticity.total == 3

    def it_serializes_to_dict_with_nested_hermeticity(self) -> None:
        """Serialize violations summary to dictionary format with nested hermeticity."""
        hermeticity = HermeticityViolationsSummary(network=1)
        violations = ViolationsSummary(timing=2, hermeticity=hermeticity)

        result = violations.model_dump()

        assert result['timing'] == 2
        assert result['hermeticity']['network'] == 1
        assert result['hermeticity']['total'] == 1


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
            violations=ViolationsSummary(timing=2),
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
            violations=ViolationsSummary(),
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

    def it_includes_hermeticity_violations_in_summary(self) -> None:
        """Include hermeticity violations in JSON report summary."""
        test_report = TestSizeReport()
        test_report.add_test('test_api.py::test_network', TestSize.SMALL, duration=0.1, outcome='passed')
        test_report.add_test('test_file.py::test_filesystem', TestSize.SMALL, duration=0.1, outcome='passed')

        stats = DistributionStats.update_counts({TestSize.SMALL: 2})

        violation_tracker = ViolationTracker()
        violation_tracker.record_violation(
            ViolationType.NETWORK,
            'test_api.py::test_network',
            'Attempted connection to example.com:443',
        )
        violation_tracker.record_violation(
            ViolationType.FILESYSTEM,
            'test_file.py::test_filesystem',
            'Attempted write to /etc/passwd',
        )

        json_report = JsonReport.from_test_size_report(
            test_report=test_report,
            distribution_stats=stats,
            version='0.7.0',
            violation_tracker=violation_tracker,
        )

        assert json_report.summary.violations.hermeticity.network == 1
        assert json_report.summary.violations.hermeticity.filesystem == 1
        assert json_report.summary.violations.hermeticity.total == 2

    def it_includes_hermeticity_violations_in_per_test_entries(self) -> None:
        """Include hermeticity violation types in per-test entries."""
        test_report = TestSizeReport()
        test_report.add_test('test_api.py::test_network', TestSize.SMALL, duration=0.1, outcome='passed')

        stats = DistributionStats.update_counts({TestSize.SMALL: 1})

        violation_tracker = ViolationTracker()
        violation_tracker.record_violation(
            ViolationType.NETWORK,
            'test_api.py::test_network',
            'Attempted connection to example.com:443',
        )

        json_report = JsonReport.from_test_size_report(
            test_report=test_report,
            distribution_stats=stats,
            version='0.7.0',
            violation_tracker=violation_tracker,
        )

        test_entry = json_report.tests[0]
        assert 'hermeticity:network' in test_entry.violations

    def it_handles_multiple_violation_types_for_same_test(self) -> None:
        """Handle multiple hermeticity violation types for the same test."""
        test_report = TestSizeReport()
        test_report.add_test('test_all.py::test_violations', TestSize.SMALL, duration=0.1, outcome='failed')

        stats = DistributionStats.update_counts({TestSize.SMALL: 1})

        violation_tracker = ViolationTracker()
        violation_tracker.record_violation(
            ViolationType.NETWORK,
            'test_all.py::test_violations',
            'Network violation',
        )
        violation_tracker.record_violation(
            ViolationType.FILESYSTEM,
            'test_all.py::test_violations',
            'Filesystem violation',
        )
        violation_tracker.record_violation(
            ViolationType.PROCESS,
            'test_all.py::test_violations',
            'Process violation',
        )

        json_report = JsonReport.from_test_size_report(
            test_report=test_report,
            distribution_stats=stats,
            version='0.7.0',
            violation_tracker=violation_tracker,
        )

        test_entry = json_report.tests[0]
        assert 'hermeticity:network' in test_entry.violations
        assert 'hermeticity:filesystem' in test_entry.violations
        assert 'hermeticity:process' in test_entry.violations

    def it_includes_all_violation_type_counts_in_summary(self) -> None:
        """Include all violation type counts in summary hermeticity breakdown."""
        test_report = TestSizeReport()
        test_report.add_test('test_one.py::test_a', TestSize.SMALL, duration=0.1, outcome='passed')
        test_report.add_test('test_two.py::test_b', TestSize.SMALL, duration=0.1, outcome='passed')
        test_report.add_test('test_three.py::test_c', TestSize.SMALL, duration=0.1, outcome='passed')
        test_report.add_test('test_four.py::test_d', TestSize.SMALL, duration=0.1, outcome='passed')
        test_report.add_test('test_five.py::test_e', TestSize.SMALL, duration=0.1, outcome='passed')

        stats = DistributionStats.update_counts({TestSize.SMALL: 5})

        violation_tracker = ViolationTracker()
        violation_tracker.record_violation(ViolationType.NETWORK, 'test_one.py::test_a', 'network')
        violation_tracker.record_violation(ViolationType.FILESYSTEM, 'test_two.py::test_b', 'filesystem')
        violation_tracker.record_violation(ViolationType.PROCESS, 'test_three.py::test_c', 'process')
        violation_tracker.record_violation(ViolationType.DATABASE, 'test_four.py::test_d', 'database')
        violation_tracker.record_violation(ViolationType.SLEEP, 'test_five.py::test_e', 'sleep')

        json_report = JsonReport.from_test_size_report(
            test_report=test_report,
            distribution_stats=stats,
            version='0.7.0',
            violation_tracker=violation_tracker,
        )

        hermeticity = json_report.summary.violations.hermeticity
        assert hermeticity.network == 1
        assert hermeticity.filesystem == 1
        assert hermeticity.process == 1
        assert hermeticity.database == 1
        assert hermeticity.sleep == 1
        assert hermeticity.total == 5

    def it_handles_no_violation_tracker(self) -> None:
        """Handle case when no violation tracker is provided (backward compatibility)."""
        test_report = TestSizeReport()
        test_report.add_test('test_one.py::test_a', TestSize.SMALL, duration=0.1, outcome='passed')

        stats = DistributionStats.update_counts({TestSize.SMALL: 1})

        json_report = JsonReport.from_test_size_report(
            test_report=test_report,
            distribution_stats=stats,
            version='0.7.0',
            violation_tracker=None,
        )

        hermeticity = json_report.summary.violations.hermeticity
        assert hermeticity.network == 0
        assert hermeticity.filesystem == 0
        assert hermeticity.process == 0
        assert hermeticity.database == 0
        assert hermeticity.sleep == 0
        assert hermeticity.total == 0
        assert json_report.tests[0].violations == []

    def it_includes_hermeticity_violations_for_unsized_tests(self) -> None:
        """Include hermeticity violations for unsized tests."""
        test_report = TestSizeReport()
        test_report.add_test('test_one.py::test_unsized', None, duration=0.1, outcome='passed')

        stats = DistributionStats.update_counts({})

        violation_tracker = ViolationTracker()
        violation_tracker.record_violation(
            ViolationType.NETWORK,
            'test_one.py::test_unsized',
            'Network access from unsized test',
        )

        json_report = JsonReport.from_test_size_report(
            test_report=test_report,
            distribution_stats=stats,
            version='0.7.0',
            violation_tracker=violation_tracker,
        )

        assert json_report.tests[0].size == 'unsized'
        assert 'hermeticity:network' in json_report.tests[0].violations


@pytest.mark.small
class DescribeViolationsSummaryWithBaseline:
    """Test suite for ViolationsSummary with baseline violations."""

    def it_creates_with_baseline_field(self) -> None:
        """Create violations summary with baseline field."""
        violations = ViolationsSummary(baseline=1)

        assert violations.baseline == 1

    def it_defaults_baseline_to_zero(self) -> None:
        """Default baseline violations to 0."""
        violations = ViolationsSummary()

        assert violations.baseline == 0

    def it_serializes_baseline_to_dict(self) -> None:
        """Serialize baseline violations to dictionary format."""
        violations = ViolationsSummary(timing=1, baseline=2)

        result = violations.model_dump()

        assert result['baseline'] == 2
        assert result['timing'] == 1


@pytest.mark.small
class DescribeJsonReportWithBaselineViolations:
    """Test suite for JSON report baseline violation handling."""

    def it_includes_baseline_violations_in_summary(self) -> None:
        """Include baseline violations count in JSON report summary."""
        test_report = TestSizeReport()
        test_report.add_test(
            'test_slow.py::test_exceeded_baseline',
            TestSize.SMALL,
            duration=0.15,
            outcome='failed',
        )
        test_report.add_baseline_violation(
            'test_slow.py::test_exceeded_baseline',
            baseline=0.1,
            category_limit=1.0,
            actual=0.15,
        )

        stats = DistributionStats.update_counts({TestSize.SMALL: 1})

        json_report = JsonReport.from_test_size_report(
            test_report=test_report,
            distribution_stats=stats,
            version='0.7.0',
        )

        assert json_report.summary.violations.baseline == 1

    def it_includes_baseline_violation_in_per_test_entry(self) -> None:
        """Include baseline violation marker in per-test violations list."""
        test_report = TestSizeReport()
        test_report.add_test(
            'test_slow.py::test_exceeded_baseline',
            TestSize.SMALL,
            duration=0.15,
            outcome='failed',
        )
        test_report.add_baseline_violation(
            'test_slow.py::test_exceeded_baseline',
            baseline=0.1,
            category_limit=1.0,
            actual=0.15,
        )

        stats = DistributionStats.update_counts({TestSize.SMALL: 1})

        json_report = JsonReport.from_test_size_report(
            test_report=test_report,
            distribution_stats=stats,
            version='0.7.0',
        )

        test_entry = json_report.tests[0]
        assert 'baseline' in test_entry.violations

    def it_distinguishes_baseline_from_timing_violations(self) -> None:
        """Distinguish baseline violations from regular timing violations."""
        test_report = TestSizeReport()
        # Test that exceeds baseline (0.15s > 0.1s baseline)
        test_report.add_test(
            'test_baseline.py::test_exceeded_baseline',
            TestSize.SMALL,
            duration=0.15,
            outcome='failed',
        )
        test_report.add_baseline_violation(
            'test_baseline.py::test_exceeded_baseline',
            baseline=0.1,
            category_limit=1.0,
            actual=0.15,
        )
        # Test that exceeds category limit (1.5s > 1.0s limit)
        test_report.add_test(
            'test_timing.py::test_exceeded_limit',
            TestSize.SMALL,
            duration=1.5,
            outcome='failed',
        )

        stats = DistributionStats.update_counts({TestSize.SMALL: 2})

        json_report = JsonReport.from_test_size_report(
            test_report=test_report,
            distribution_stats=stats,
            version='0.7.0',
        )

        assert json_report.summary.violations.baseline == 1
        assert json_report.summary.violations.timing == 1

        # Check per-test entries
        baseline_test = next(t for t in json_report.tests if t.name == 'test_baseline.py::test_exceeded_baseline')
        timing_test = next(t for t in json_report.tests if t.name == 'test_timing.py::test_exceeded_limit')
        assert 'baseline' in baseline_test.violations
        assert 'timing' not in baseline_test.violations
        assert 'timing' in timing_test.violations
        assert 'baseline' not in timing_test.violations

    def it_handles_no_baseline_violations(self) -> None:
        """Handle case when there are no baseline violations."""
        test_report = TestSizeReport()
        test_report.add_test('test_fast.py::test_quick', TestSize.SMALL, duration=0.05, outcome='passed')

        stats = DistributionStats.update_counts({TestSize.SMALL: 1})

        json_report = JsonReport.from_test_size_report(
            test_report=test_report,
            distribution_stats=stats,
            version='0.7.0',
        )

        assert json_report.summary.violations.baseline == 0
        assert json_report.tests[0].violations == []
