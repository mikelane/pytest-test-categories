"""Tests for the reporting module public APIs."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from pytest_test_categories.reporting import TestSizeReport
from pytest_test_categories.types import TestSize


@pytest.mark.small
class DescribeTestSizeReport:
    """Test the TestSizeReport class."""

    def it_initializes_with_empty_data(self) -> None:
        """Test that TestSizeReport initializes with empty data."""
        report = TestSizeReport()
        assert len(report.sized_tests) == 0
        assert len(report.unsized_tests) == 0
        assert len(report.test_durations) == 0
        assert len(report.test_outcomes) == 0

    def it_adds_sized_tests_correctly(self) -> None:
        """Test that add_test adds sized tests correctly."""
        report = TestSizeReport()

        report.add_test('test_small.py::test_small', TestSize.SMALL, 0.5, 'passed')
        report.add_test('test_medium.py::test_medium', TestSize.MEDIUM, 2.0, 'passed')

        assert 'test_small.py::test_small' in report.sized_tests[TestSize.SMALL]
        assert 'test_medium.py::test_medium' in report.sized_tests[TestSize.MEDIUM]
        assert report.test_durations['test_small.py::test_small'] == 0.5
        assert report.test_durations['test_medium.py::test_medium'] == 2.0
        assert report.test_outcomes['test_small.py::test_small'] == 'passed'
        assert report.test_outcomes['test_medium.py::test_medium'] == 'passed'

    def it_adds_unsized_tests_correctly(self) -> None:
        """Test that add_test adds unsized tests correctly."""
        report = TestSizeReport()

        report.add_test('test_unsized.py::test_unsized', None, 1.0, 'passed')

        assert 'test_unsized.py::test_unsized' in report.unsized_tests
        assert report.test_durations['test_unsized.py::test_unsized'] == 1.0
        assert report.test_outcomes['test_unsized.py::test_unsized'] == 'passed'

    def it_adds_tests_without_duration(self) -> None:
        """Test that add_test works without duration."""
        report = TestSizeReport()

        report.add_test('test_no_duration.py::test_no_duration', TestSize.SMALL, outcome='passed')

        assert 'test_no_duration.py::test_no_duration' in report.sized_tests[TestSize.SMALL]
        assert 'test_no_duration.py::test_no_duration' not in report.test_durations
        assert report.test_outcomes['test_no_duration.py::test_no_duration'] == 'passed'

    def it_uses_default_outcome(self) -> None:
        """Test that add_test uses default outcome."""
        report = TestSizeReport()

        report.add_test('test_default.py::test_default', TestSize.SMALL)

        assert report.test_outcomes['test_default.py::test_default'] == 'passed'

    def it_calculates_total_tests_correctly(self) -> None:
        """Test that get_total_tests returns correct count."""
        report = TestSizeReport()

        # Add some tests
        report.add_test('test1', TestSize.SMALL)
        report.add_test('test2', TestSize.MEDIUM)
        report.add_test('test3', TestSize.LARGE)
        report.add_test('test4', None)  # unsized

        assert report.get_total_tests() == 4

    def it_calculates_size_counts_correctly(self) -> None:
        """Test that get_size_counts returns correct counts."""
        report = TestSizeReport()

        # Add tests of different sizes
        report.add_test('test1', TestSize.SMALL)
        report.add_test('test2', TestSize.SMALL)
        report.add_test('test3', TestSize.MEDIUM)
        report.add_test('test4', None)  # unsized

        counts = report.get_size_counts()
        assert counts['small'] == 2
        assert counts['medium'] == 1
        assert counts['large'] == 0
        assert counts['xlarge'] == 0
        assert counts['unsized'] == 1

    def it_calculates_size_percentages_correctly(self) -> None:
        """Test that get_size_percentages returns correct percentages."""
        report = TestSizeReport()

        # Add 4 tests: 2 small (50%), 1 medium (25%), 1 unsized (25%)
        report.add_test('test1', TestSize.SMALL)
        report.add_test('test2', TestSize.SMALL)
        report.add_test('test3', TestSize.MEDIUM)
        report.add_test('test4', None)  # unsized

        percentages = report.get_size_percentages()
        assert percentages['small'] == 50.0
        assert percentages['medium'] == 25.0
        assert percentages['large'] == 0.0
        assert percentages['xlarge'] == 0.0
        assert percentages['unsized'] == 25.0

    def it_handles_zero_total_tests(self) -> None:
        """Test that get_size_percentages handles zero total tests."""
        report = TestSizeReport()

        percentages = report.get_size_percentages()
        assert percentages['small'] == 0.0
        assert percentages['medium'] == 0.0
        assert percentages['large'] == 0.0
        assert percentages['xlarge'] == 0.0
        assert percentages['unsized'] == 0.0

    def it_detects_time_limit_exceeded(self) -> None:
        """Test that exceeds_time_limit detects violations correctly."""
        report = TestSizeReport()

        # Add a small test that takes 2 seconds (exceeds 1 second limit)
        report.add_test('test_slow.py::test_slow', TestSize.SMALL, 2.0, 'passed')

        assert report.exceeds_time_limit('test_slow.py::test_slow', TestSize.SMALL) is True

    def it_detects_time_limit_not_exceeded(self) -> None:
        """Test that exceeds_time_limit detects no violations correctly."""
        report = TestSizeReport()

        # Add a small test that takes 0.5 seconds (within 1 second limit)
        report.add_test('test_fast.py::test_fast', TestSize.SMALL, 0.5, 'passed')

        assert report.exceeds_time_limit('test_fast.py::test_fast', TestSize.SMALL) is False

    def it_handles_missing_duration_for_time_check(self) -> None:
        """Test that exceeds_time_limit handles missing duration."""
        report = TestSizeReport()

        # Add a test without duration
        report.add_test('test_no_duration.py::test_no_duration', TestSize.SMALL, outcome='passed')

        assert report.exceeds_time_limit('test_no_duration.py::test_no_duration', TestSize.SMALL) is False

    def it_handles_unsized_test_for_time_check(self) -> None:
        """Test that exceeds_time_limit handles unsized tests."""
        report = TestSizeReport()

        # Add an unsized test
        report.add_test('test_unsized.py::test_unsized', None, 2.0, 'passed')

        assert report.exceeds_time_limit('test_unsized.py::test_unsized', None) is False

    def it_writes_basic_report(self) -> None:
        """Test that write_basic_report writes correct output."""
        report = TestSizeReport()

        # Add some tests
        report.add_test('test1', TestSize.SMALL)
        report.add_test('test2', TestSize.SMALL)
        report.add_test('test3', TestSize.MEDIUM)
        report.add_test('test4', None)  # unsized

        # Mock terminal reporter
        mock_reporter = Mock()

        report.write_basic_report(mock_reporter)

        # Check that section was called
        mock_reporter.section.assert_called_once_with('Test Size Report Summary', sep='=')

        # Check that write_line was called with expected content
        write_line_calls = [call[0][0] for call in mock_reporter.write_line.call_args_list]

        assert 'Test Size Distribution:' in write_line_calls
        assert '    Small: 2 tests (50.00%)' in write_line_calls
        assert '    Medium: 1 test (25.00%)' in write_line_calls
        assert '    Large: 0 tests (0.00%)' in write_line_calls
        assert '    Xlarge: 0 tests (0.00%)' in write_line_calls
        assert '    Unsized: 1 test (25.00%)' in write_line_calls
        assert '    Total: 4 tests' in write_line_calls

        # Check that write_sep was called
        mock_reporter.write_sep.assert_called_once_with('=')

    def it_writes_detailed_report(self) -> None:
        """Test that write_detailed_report writes correct output."""
        report = TestSizeReport()

        # Add some tests with different outcomes
        report.add_test('test_small.py::test_small', TestSize.SMALL, 0.5, 'passed')
        report.add_test('test_medium.py::test_medium', TestSize.MEDIUM, 2.0, 'failed')
        report.add_test('test_unsized.py::test_unsized', None, 1.0, 'passed')

        # Mock terminal reporter
        mock_reporter = Mock()

        report.write_detailed_report(mock_reporter)

        # Check that section was called
        mock_reporter.section.assert_called_once_with('Detailed Test Size Report', sep='=')

        # Check that header lines were written
        write_line_calls = [call[0][0] for call in mock_reporter.write_line.call_args_list]

        assert 'Test Name                                 Size     Duration    Status' in write_line_calls
        assert '------------------------------------------------------------------------' in write_line_calls

        # Check that write_sep was called
        mock_reporter.write_sep.assert_called_once_with('=')

    def it_handles_singular_vs_plural_in_basic_report(self) -> None:
        """Test that basic report uses correct singular/plural forms."""
        report = TestSizeReport()

        # Add exactly one test of each type
        report.add_test('test1', TestSize.SMALL)
        report.add_test('test2', TestSize.MEDIUM)
        report.add_test('test3', None)  # unsized

        mock_reporter = Mock()
        report.write_basic_report(mock_reporter)

        write_line_calls = [call[0][0] for call in mock_reporter.write_line.call_args_list]

        assert '    Small: 1 test (33.33%)' in write_line_calls
        assert '    Medium: 1 test (33.33%)' in write_line_calls
        assert '    Unsized: 1 test (33.33%)' in write_line_calls

    def it_handles_empty_report(self) -> None:
        """Test that reports handle empty data correctly."""
        report = TestSizeReport()

        mock_reporter = Mock()
        report.write_basic_report(mock_reporter)

        write_line_calls = [call[0][0] for call in mock_reporter.write_line.call_args_list]

        assert '    Small: 0 tests (0.00%)' in write_line_calls
        assert '    Medium: 0 tests (0.00%)' in write_line_calls
        assert '    Large: 0 tests (0.00%)' in write_line_calls
        assert '    Xlarge: 0 tests (0.00%)' in write_line_calls
        assert '    Unsized: 0 tests (0.00%)' in write_line_calls
        assert '    Total: 0 tests' in write_line_calls
