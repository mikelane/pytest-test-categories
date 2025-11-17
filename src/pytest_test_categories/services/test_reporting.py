"""Test reporting service for test size reports.

This module provides the TestReportingService that manages test size
reporting during test execution. It follows hexagonal architecture by
depending on abstract ports rather than concrete pytest implementations.

The service encapsulates the logic for:
- Initializing test size reports based on options
- Adding tests to reports during collection
- Updating test outcomes and durations during execution
- Writing distribution summaries to terminal output

This is pure domain logic that can be tested without pytest.

Example:
    >>> from pytest_test_categories.reporting import TestSizeReport
    >>> from pytest_test_categories.types import TestSize
    >>> service = TestReportingService()
    >>> report = TestSizeReport()
    >>> service.add_test_to_report(report, 'test.py::test_func', TestSize.SMALL)
    >>> service.update_test_result(report, 'test.py::test_func', 'passed', 0.5)

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytest_test_categories.formatting import (
    format_distribution_row,
    get_status_message,
)
from pytest_test_categories.reporting import TestSizeReport

if TYPE_CHECKING:
    from pytest_test_categories.distribution.stats import DistributionStats
    from pytest_test_categories.types import (
        OutputWriterPort,
        TestSize,
    )


class TestReportingService:
    """Service for managing test size reporting.

    This service encapsulates the logic for managing test size reports and
    distribution summaries. It works through abstract ports, making it testable
    without pytest dependencies.

    The service is stateless and thread-safe - all state is passed as parameters.

    Example:
        >>> from pytest_test_categories.reporting import TestSizeReport
        >>> from pytest_test_categories.types import TestSize
        >>> service = TestReportingService()
        >>> report = TestSizeReport()
        >>> service.add_test_to_report(report, 'test.py::test_func', TestSize.SMALL)
        >>> len(report.test_sizes)
        1

    """

    def create_report_if_requested(self, report_option: object) -> TestSizeReport | None:
        """Create a TestSizeReport if the report option is set.

        Args:
            report_option: The value of the --test-size-report option.

        Returns:
            A TestSizeReport instance if option is not None, otherwise None.

        Example:
            >>> service = TestReportingService()
            >>> service.create_report_if_requested('basic') is not None
            True
            >>> service.create_report_if_requested(None) is None
            True

        """
        if report_option is not None:
            return TestSizeReport()
        return None

    def add_test_to_report(
        self,
        report: TestSizeReport,
        nodeid: str,
        test_size: TestSize | None,
    ) -> None:
        """Add a test to the report during collection.

        Args:
            report: The report to add the test to.
            nodeid: The test's node ID.
            test_size: The test's size category (may be None).

        Example:
            >>> report = TestSizeReport()
            >>> service = TestReportingService()
            >>> service.add_test_to_report(report, 'test.py::test_func', TestSize.SMALL)
            >>> 'test.py::test_func' in report.test_sizes
            True

        """
        report.add_test(nodeid, test_size)

    def update_test_result(
        self,
        report: TestSizeReport,
        nodeid: str,
        outcome: str,
        duration: float | None,
    ) -> None:
        """Update test outcome and duration in the report.

        Args:
            report: The report to update.
            nodeid: The test's node ID.
            outcome: The test outcome ('passed', 'failed', 'skipped', etc.).
            duration: The test duration in seconds (may be None).

        Example:
            >>> report = TestSizeReport()
            >>> service = TestReportingService()
            >>> service.add_test_to_report(report, 'test.py::test_func', TestSize.SMALL)
            >>> service.update_test_result(report, 'test.py::test_func', 'passed', 0.5)
            >>> report.test_outcomes['test.py::test_func']
            'passed'
            >>> report.test_durations['test.py::test_func']
            0.5

        """
        report.test_outcomes[nodeid] = outcome
        if duration is not None:
            report.test_durations[nodeid] = duration

    def write_distribution_summary(
        self,
        stats: DistributionStats,
        writer: OutputWriterPort,
    ) -> None:
        """Write the distribution summary to the terminal.

        This outputs the distribution table and status message through the
        provided output writer port.

        Args:
            stats: The distribution statistics to display.
            writer: Port for writing terminal output.

        Example:
            >>> from tests._fixtures.output_writer import StringBufferWriter
            >>> from pytest_test_categories.distribution.stats import DistributionStats
            >>> stats = DistributionStats.update_counts({'small': 80, 'medium': 15, 'large': 5})
            >>> writer = StringBufferWriter()
            >>> service = TestReportingService()
            >>> service.write_distribution_summary(stats, writer)
            >>> 'Test Suite Distribution Summary' in writer.getvalue()
            True

        """
        counts = stats.counts
        percentages = stats.calculate_percentages()

        writer.write_section('Test Suite Distribution Summary', sep='=')
        writer.write_line('    Test Size Distribution:')

        # Write distribution rows
        for size, count, percentage in [
            ('Small', counts.small, percentages.small),
            ('Medium', counts.medium, percentages.medium),
            ('Large', counts.large, percentages.large),
            ('XLarge', counts.xlarge, percentages.xlarge),
        ]:
            writer.write_line(format_distribution_row(size, count, percentage))

        # Write status message
        writer.write_line('')
        for line in get_status_message(percentages):
            writer.write_line(line)

        writer.write_separator(sep='=')
