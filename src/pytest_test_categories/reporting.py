"""Test size reporting functionality.

This module provides classes and functions for generating reports about
test size distribution and execution statistics. It supports both summary
and detailed reports, with information about test sizes, execution times,
and status.

Example usage:
    pytest --test-size-report
    pytest --test-size-report=detailed
    pytest --test-size-report path/to/tests/
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from pydantic import (
    BaseModel,
    Field,
)

from pytest_test_categories.timing import get_limit
from pytest_test_categories.types import TestSize

if TYPE_CHECKING:
    import pytest


def _default_sized_tests() -> defaultdict[TestSize, list[str]]:
    """Create a defaultdict for sized_tests field."""
    return defaultdict(list)


class TestSizeReport(BaseModel):
    """Generator for test size reports."""

    sized_tests: defaultdict[TestSize, list[str]] = Field(default_factory=_default_sized_tests)
    unsized_tests: list[str] = Field(default_factory=list)
    test_durations: dict[str, float] = Field(default_factory=dict)
    test_outcomes: dict[str, str] = Field(default_factory=dict)

    def add_test(
        self, nodeid: str, size: TestSize | None, duration: float | None = None, outcome: str = 'passed'
    ) -> None:
        """Add a test to the report.

        Args:
            nodeid: The pytest node ID of the test
            size: The test size category, or None if unsized
            duration: The test execution time in seconds, if available
            outcome: The test outcome (passed, failed, etc.)

        """
        if size is None:
            self.unsized_tests.append(nodeid)
        else:
            self.sized_tests[size].append(nodeid)

        if duration is not None:
            self.test_durations[nodeid] = duration

        self.test_outcomes[nodeid] = outcome

    def get_total_tests(self) -> int:
        """Get the total number of tests in the report."""
        total = len(self.unsized_tests)
        for tests in self.sized_tests.values():
            total += len(tests)
        return total

    def get_size_counts(self) -> dict[str, int]:
        """Get the count of tests by size category."""
        counts = {size.name.lower(): len(self.sized_tests[size]) for size in TestSize}
        counts['unsized'] = len(self.unsized_tests)
        return counts

    def get_size_percentages(self) -> dict[str, float]:
        """Get the percentage of tests by size category."""
        total = self.get_total_tests()
        if total == 0:
            return {size.name.lower(): 0.0 for size in TestSize} | {'unsized': 0.0}

        percentages = {}
        for size in TestSize:
            percentages[size.name.lower()] = (len(self.sized_tests[size]) / total) * 100.0

        percentages['unsized'] = (len(self.unsized_tests) / total) * 100.0
        return percentages

    def exceeds_time_limit(self, nodeid: str, size: TestSize | None) -> bool:
        """Check if a test exceeds its time limit based on size."""
        if size is None or nodeid not in self.test_durations:
            return False

        duration = self.test_durations[nodeid]
        limit = get_limit(size).limit
        return duration > limit

    def write_basic_report(self, terminalreporter: pytest.TerminalReporter) -> None:
        """Write a basic summary report to the terminal."""
        counts = self.get_size_counts()
        percentages = self.get_size_percentages()
        total = self.get_total_tests()

        terminalreporter.section('Test Size Report Summary', sep='=')
        terminalreporter.write_line('Test Size Distribution:')

        for size in [*list(TestSize), 'unsized']:
            size_name = size if isinstance(size, str) else size.name
            count = counts[size_name.lower()]
            percentage = percentages[size_name.lower()]
            test_word = 'test' if count == 1 else 'tests'

            terminalreporter.write_line(f'    {size_name.title()}: {count} {test_word} ({percentage:.2f}%)')

        terminalreporter.write_line(f'    Total: {total} tests')
        terminalreporter.write_sep('=')

    def write_detailed_report(self, terminalreporter: pytest.TerminalReporter) -> None:
        """Write a detailed report to the terminal."""
        terminalreporter.section('Detailed Test Size Report', sep='=')
        terminalreporter.write_line('Test Name                                 Size     Duration    Status')
        terminalreporter.write_line('------------------------------------------------------------------------')

        self._write_sized_tests_to_report(terminalreporter)
        self._write_unsized_tests_to_report(terminalreporter)

        terminalreporter.write_sep('=')

    def _write_sized_tests_to_report(self, terminalreporter: pytest.TerminalReporter) -> None:
        """Write sized tests to the detailed report."""
        for size in TestSize:
            for nodeid in sorted(self.sized_tests[size]):
                duration = self.test_durations.get(nodeid, 0.0)
                outcome = self.test_outcomes.get(nodeid, 'unknown')

                exceeds_limit = self.exceeds_time_limit(nodeid, size)
                status = 'FAIL' if outcome != 'passed' else 'SLOW' if exceeds_limit else 'Pass'

                line = f'{nodeid:40} {size.name.lower():8} {duration:.1f}s      {status}'
                if exceeds_limit or outcome != 'passed':
                    terminalreporter.write_line(line, red=True)
                else:
                    terminalreporter.write_line(line)

    def _write_unsized_tests_to_report(self, terminalreporter: pytest.TerminalReporter) -> None:
        """Write unsized tests to the detailed report."""
        for nodeid in sorted(self.unsized_tests):
            duration = self.test_durations.get(nodeid, 0.0)
            outcome = self.test_outcomes.get(nodeid, 'unknown')
            status = 'FAIL' if outcome != 'passed' else 'Pass'

            line = f'{nodeid:40} unsized  {duration:.1f}s      {status}'
            if outcome != 'passed':
                terminalreporter.write_line(line, red=True)
            else:
                terminalreporter.write_line(line)
