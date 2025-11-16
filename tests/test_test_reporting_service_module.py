"""Unit tests for TestReportingService module.

This module tests the TestReportingService in isolation without pytest dependencies.
Uses StringBufferWriter for deterministic output verification.
"""

from __future__ import annotations

import pytest

from pytest_test_categories.distribution.stats import DistributionStats
from pytest_test_categories.reporting import TestSizeReport
from pytest_test_categories.services.test_reporting import TestReportingService
from pytest_test_categories.types import TestSize
from tests._fixtures.output_writer import StringBufferWriter


@pytest.mark.small
class DescribeCreateReportIfRequested:
    """Test suite for create_report_if_requested method."""

    def it_creates_report_when_option_is_set(self) -> None:
        """Create TestSizeReport when report option is not None."""
        service = TestReportingService()

        report = service.create_report_if_requested('basic')

        assert report is not None
        assert isinstance(report, TestSizeReport)

    def it_creates_report_when_option_is_detailed(self) -> None:
        """Create TestSizeReport when report option is 'detailed'."""
        service = TestReportingService()

        report = service.create_report_if_requested('detailed')

        assert report is not None
        assert isinstance(report, TestSizeReport)

    def it_returns_none_when_option_is_none(self) -> None:
        """Return None when report option is None."""
        service = TestReportingService()

        report = service.create_report_if_requested(None)

        assert report is None

    def it_creates_report_when_option_is_empty_string(self) -> None:
        """Create TestSizeReport even when option is empty string."""
        service = TestReportingService()

        # Empty string is truthy, so it should create a report
        report = service.create_report_if_requested('')

        assert report is not None
        assert isinstance(report, TestSizeReport)


@pytest.mark.small
class DescribeAddTestToReport:
    """Test suite for add_test_to_report method."""

    def it_adds_test_to_report(self) -> None:
        """Add test to the report's sized_tests dictionary."""
        service = TestReportingService()
        report = TestSizeReport()

        service.add_test_to_report(report, 'test.py::test_func', TestSize.SMALL)

        assert 'test.py::test_func' in report.sized_tests[TestSize.SMALL]

    def it_adds_test_with_none_size(self) -> None:
        """Add test to report even when size is None."""
        service = TestReportingService()
        report = TestSizeReport()

        service.add_test_to_report(report, 'test.py::test_func', None)

        assert 'test.py::test_func' in report.unsized_tests

    def it_adds_multiple_tests_to_report(self) -> None:
        """Add multiple tests to the same report."""
        service = TestReportingService()
        report = TestSizeReport()

        service.add_test_to_report(report, 'test.py::test_one', TestSize.SMALL)
        service.add_test_to_report(report, 'test.py::test_two', TestSize.MEDIUM)
        service.add_test_to_report(report, 'test.py::test_three', TestSize.LARGE)

        assert 'test.py::test_one' in report.sized_tests[TestSize.SMALL]
        assert 'test.py::test_two' in report.sized_tests[TestSize.MEDIUM]
        assert 'test.py::test_three' in report.sized_tests[TestSize.LARGE]


@pytest.mark.small
class DescribeUpdateTestResult:
    """Test suite for update_test_result method."""

    def it_updates_test_outcome(self) -> None:
        """Update test outcome in the report."""
        service = TestReportingService()
        report = TestSizeReport()
        service.add_test_to_report(report, 'test.py::test_func', TestSize.SMALL)

        service.update_test_result(report, 'test.py::test_func', 'passed', 0.5)

        assert report.test_outcomes['test.py::test_func'] == 'passed'

    def it_updates_test_duration(self) -> None:
        """Update test duration in the report."""
        service = TestReportingService()
        report = TestSizeReport()
        service.add_test_to_report(report, 'test.py::test_func', TestSize.SMALL)

        service.update_test_result(report, 'test.py::test_func', 'passed', 0.5)

        assert report.test_durations['test.py::test_func'] == 0.5

    def it_updates_outcome_for_failed_test(self) -> None:
        """Update outcome to 'failed' for failing tests."""
        service = TestReportingService()
        report = TestSizeReport()
        service.add_test_to_report(report, 'test.py::test_func', TestSize.SMALL)

        service.update_test_result(report, 'test.py::test_func', 'failed', 1.2)

        assert report.test_outcomes['test.py::test_func'] == 'failed'
        assert report.test_durations['test.py::test_func'] == 1.2

    def it_updates_outcome_for_skipped_test(self) -> None:
        """Update outcome to 'skipped' for skipped tests."""
        service = TestReportingService()
        report = TestSizeReport()
        service.add_test_to_report(report, 'test.py::test_func', TestSize.SMALL)

        service.update_test_result(report, 'test.py::test_func', 'skipped', None)

        assert report.test_outcomes['test.py::test_func'] == 'skipped'
        assert 'test.py::test_func' not in report.test_durations

    def it_handles_none_duration_gracefully(self) -> None:
        """Handle None duration by not adding to test_durations."""
        service = TestReportingService()
        report = TestSizeReport()
        service.add_test_to_report(report, 'test.py::test_func', TestSize.SMALL)

        service.update_test_result(report, 'test.py::test_func', 'passed', None)

        assert report.test_outcomes['test.py::test_func'] == 'passed'
        assert 'test.py::test_func' not in report.test_durations

    def it_handles_zero_duration(self) -> None:
        """Handle zero duration correctly."""
        service = TestReportingService()
        report = TestSizeReport()
        service.add_test_to_report(report, 'test.py::test_func', TestSize.SMALL)

        service.update_test_result(report, 'test.py::test_func', 'passed', 0.0)

        assert report.test_durations['test.py::test_func'] == 0.0

    def it_updates_multiple_test_results(self) -> None:
        """Update results for multiple tests."""
        service = TestReportingService()
        report = TestSizeReport()
        service.add_test_to_report(report, 'test.py::test_one', TestSize.SMALL)
        service.add_test_to_report(report, 'test.py::test_two', TestSize.MEDIUM)

        service.update_test_result(report, 'test.py::test_one', 'passed', 0.5)
        service.update_test_result(report, 'test.py::test_two', 'failed', 1.5)

        assert report.test_outcomes['test.py::test_one'] == 'passed'
        assert report.test_outcomes['test.py::test_two'] == 'failed'
        assert report.test_durations['test.py::test_one'] == 0.5
        assert report.test_durations['test.py::test_two'] == 1.5


@pytest.mark.small
class DescribeWriteDistributionSummary:
    """Test suite for write_distribution_summary method."""

    def it_writes_section_header(self) -> None:
        """Write section header with correct title."""
        service = TestReportingService()
        writer = StringBufferWriter()
        stats = DistributionStats.update_counts(
            {
                'small': 80,
                'medium': 15,
                'large': 5,
                'xlarge': 0,
            }
        )

        service.write_distribution_summary(stats, writer)

        output = writer.get_output()
        assert 'SECTION[=]: Test Suite Distribution Summary' in output

    def it_writes_distribution_rows(self) -> None:
        """Write distribution rows for all test sizes."""
        service = TestReportingService()
        writer = StringBufferWriter()
        stats = DistributionStats.update_counts(
            {
                'small': 80,
                'medium': 15,
                'large': 5,
                'xlarge': 0,
            }
        )

        service.write_distribution_summary(stats, writer)

        output = writer.get_output()
        # Should contain rows for all sizes
        assert any('Small' in line and '80' in line for line in output)
        assert any('Medium' in line and '15' in line for line in output)
        assert any('Large' in line and '5' in line for line in output)
        assert any('XLarge' in line and '0' in line for line in output)

    def it_writes_status_message(self) -> None:
        """Write status message based on distribution."""
        service = TestReportingService()
        writer = StringBufferWriter()
        stats = DistributionStats.update_counts(
            {
                'small': 80,
                'medium': 15,
                'large': 5,
                'xlarge': 0,
            }
        )

        service.write_distribution_summary(stats, writer)

        output = writer.get_output()
        # Should contain success message
        assert any('Great job!' in line for line in output)

    def it_writes_closing_separator(self) -> None:
        """Write closing separator at the end."""
        service = TestReportingService()
        writer = StringBufferWriter()
        stats = DistributionStats.update_counts(
            {
                'small': 80,
                'medium': 15,
                'large': 5,
                'xlarge': 0,
            }
        )

        service.write_distribution_summary(stats, writer)

        output = writer.get_output()
        assert 'SEPARATOR[=]' in output

    def it_formats_percentages_correctly(self) -> None:
        """Format percentages with two decimal places."""
        service = TestReportingService()
        writer = StringBufferWriter()
        stats = DistributionStats.update_counts(
            {
                'small': 80,
                'medium': 15,
                'large': 5,
                'xlarge': 0,
            }
        )

        service.write_distribution_summary(stats, writer)

        output = writer.get_output()
        # Check for percentage formatting
        assert any('80.00%' in line for line in output)
        assert any('15.00%' in line for line in output)
        assert any('5.00%' in line for line in output)
        assert any('0.00%' in line for line in output)

    def it_writes_warning_for_poor_distribution(self) -> None:
        """Write warning message for poor distribution."""
        service = TestReportingService()
        writer = StringBufferWriter()
        stats = DistributionStats.update_counts(
            {
                'small': 50,
                'medium': 30,
                'large': 20,
                'xlarge': 0,
            }
        )

        service.write_distribution_summary(stats, writer)

        output = writer.get_output()
        # Should contain warning instead of success message
        assert any('Warning!' in line or 'improvement' in line for line in output)

    def it_writes_all_components_in_order(self) -> None:
        """Write all components in the correct order."""
        service = TestReportingService()
        writer = StringBufferWriter()
        stats = DistributionStats.update_counts(
            {
                'small': 80,
                'medium': 15,
                'large': 5,
                'xlarge': 0,
            }
        )

        service.write_distribution_summary(stats, writer)

        output = writer.get_output()
        # Verify order: section header, title, rows, status, separator
        assert output[0] == 'SECTION[=]: Test Suite Distribution Summary'
        assert 'Test Size Distribution:' in output[1]
        # Distribution rows should come before status
        small_row_idx = next(i for i, line in enumerate(output) if 'Small' in line and '80' in line)
        status_idx = next(i for i, line in enumerate(output) if 'Great job!' in line)
        assert small_row_idx < status_idx
        # Separator should be last
        assert output[-1] == 'SEPARATOR[=]'

    def it_handles_zero_tests(self) -> None:
        """Handle distribution summary with zero tests."""
        service = TestReportingService()
        writer = StringBufferWriter()
        stats = DistributionStats.update_counts(
            {
                'small': 0,
                'medium': 0,
                'large': 0,
                'xlarge': 0,
            }
        )

        service.write_distribution_summary(stats, writer)

        output = writer.get_output()
        # Should still write the summary, even with zero tests
        assert 'SECTION[=]: Test Suite Distribution Summary' in output
        assert any('0 tests' in line for line in output)
