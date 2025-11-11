"""Tests for OutputWriterPort and its adapters.

This module tests the OutputWriterPort interface and its implementations:
- TerminalReporterAdapter: Production adapter wrapping pytest.TerminalReporter
- StringBufferWriter: Test adapter capturing output to a list

Following strict TDD principles, these tests are written FIRST to drive the interface design.
"""

from __future__ import annotations

from unittest.mock import (
    Mock,
)

import pytest

from pytest_test_categories.adapters.pytest_adapter import TerminalReporterAdapter
from tests._fixtures.output_writer import StringBufferWriter


@pytest.mark.small
class DescribeOutputWriterPort:
    """Tests for OutputWriterPort interface and contract."""

    def it_defines_abstract_interface(self) -> None:
        """It defines the abstract interface with required methods."""
        from pytest_test_categories.types import OutputWriterPort

        # Verify OutputWriterPort is abstract and has required methods
        assert hasattr(OutputWriterPort, 'write_section')
        assert hasattr(OutputWriterPort, 'write_line')
        assert hasattr(OutputWriterPort, 'write_separator')

    def it_cannot_be_instantiated_directly(self) -> None:
        """It cannot be instantiated directly as an abstract base class."""
        from pytest_test_categories.types import OutputWriterPort

        # Attempting to instantiate should raise TypeError
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            OutputWriterPort()  # type: ignore[abstract]


@pytest.mark.small
class DescribeTerminalReporterAdapter:
    """Tests for TerminalReporterAdapter production adapter."""

    def it_implements_output_writer_port(self) -> None:
        """It implements the OutputWriterPort interface."""
        from pytest_test_categories.types import OutputWriterPort

        mock_reporter = Mock()
        adapter = TerminalReporterAdapter(mock_reporter)

        # Verify adapter is an instance of OutputWriterPort
        assert isinstance(adapter, OutputWriterPort)

    def it_wraps_pytest_terminal_reporter(self) -> None:
        """It wraps a pytest.TerminalReporter instance."""
        mock_reporter = Mock()
        adapter = TerminalReporterAdapter(mock_reporter)

        # Adapter should store the wrapped reporter
        assert adapter._reporter is mock_reporter  # noqa: SLF001

    def it_delegates_write_section_to_reporter_section(self) -> None:
        """It delegates write_section to TerminalReporter.section()."""
        mock_reporter = Mock()
        adapter = TerminalReporterAdapter(mock_reporter)

        # Call write_section
        adapter.write_section('Test Section', sep='=')

        # Verify it called reporter.section with correct arguments
        mock_reporter.section.assert_called_once_with('Test Section', sep='=')

    def it_delegates_write_line_to_reporter_write_line(self) -> None:
        """It delegates write_line to TerminalReporter.write_line()."""
        mock_reporter = Mock()
        adapter = TerminalReporterAdapter(mock_reporter)

        # Call write_line
        adapter.write_line('Test message')

        # Verify it called reporter.write_line with correct arguments
        mock_reporter.write_line.assert_called_once_with('Test message')

    def it_forwards_kwargs_in_write_line(self) -> None:
        """It forwards keyword arguments in write_line to reporter."""
        mock_reporter = Mock()
        adapter = TerminalReporterAdapter(mock_reporter)

        # Call write_line with kwargs
        adapter.write_line('Error message', red=True, bold=True)

        # Verify kwargs were forwarded
        mock_reporter.write_line.assert_called_once_with('Error message', red=True, bold=True)

    def it_delegates_write_separator_to_reporter_write_sep(self) -> None:
        """It delegates write_separator to TerminalReporter.write_sep()."""
        mock_reporter = Mock()
        adapter = TerminalReporterAdapter(mock_reporter)

        # Call write_separator
        adapter.write_separator(sep='=')

        # Verify it called reporter.write_sep with correct arguments
        mock_reporter.write_sep.assert_called_once_with(sep='=')

    def it_uses_default_separator_when_not_specified(self) -> None:
        """It uses default separator when not specified in write_separator."""
        mock_reporter = Mock()
        adapter = TerminalReporterAdapter(mock_reporter)

        # Call write_separator without arguments
        adapter.write_separator()

        # Verify it called reporter.write_sep with default
        mock_reporter.write_sep.assert_called_once_with(sep='-')


@pytest.mark.small
class DescribeStringBufferWriter:
    """Tests for StringBufferWriter test adapter."""

    def it_implements_output_writer_port(self) -> None:
        """It implements the OutputWriterPort interface."""
        from pytest_test_categories.types import OutputWriterPort

        writer = StringBufferWriter()

        # Verify writer is an instance of OutputWriterPort
        assert isinstance(writer, OutputWriterPort)

    def it_starts_with_empty_buffer(self) -> None:
        """It starts with an empty output buffer."""
        writer = StringBufferWriter()

        # Verify initial state is empty
        assert writer.get_output() == []

    def it_captures_write_section_calls(self) -> None:
        """It captures write_section calls with title and separator."""
        writer = StringBufferWriter()

        # Write a section
        writer.write_section('Test Section', sep='=')

        # Verify output was captured
        output = writer.get_output()
        assert len(output) == 1
        assert output[0] == 'SECTION[=]: Test Section'

    def it_captures_write_line_calls(self) -> None:
        """It captures write_line calls with message."""
        writer = StringBufferWriter()

        # Write a line
        writer.write_line('Test message')

        # Verify output was captured
        output = writer.get_output()
        assert len(output) == 1
        assert output[0] == 'Test message'

    def it_captures_write_separator_calls(self) -> None:
        """It captures write_separator calls with separator character."""
        writer = StringBufferWriter()

        # Write a separator
        writer.write_separator(sep='=')

        # Verify output was captured
        output = writer.get_output()
        assert len(output) == 1
        assert output[0] == 'SEPARATOR[=]'

    def it_captures_multiple_calls_in_sequence(self) -> None:
        """It captures multiple calls in the order they were made."""
        writer = StringBufferWriter()

        # Write multiple things
        writer.write_section('Test Report', sep='=')
        writer.write_line('First line')
        writer.write_line('Second line')
        writer.write_separator(sep='-')

        # Verify all output was captured in order
        output = writer.get_output()
        assert output == [
            'SECTION[=]: Test Report',
            'First line',
            'Second line',
            'SEPARATOR[-]',
        ]

    def it_ignores_kwargs_in_write_line(self) -> None:
        """It ignores styling kwargs in write_line since it's just capturing text."""
        writer = StringBufferWriter()

        # Write with kwargs (should be ignored)
        writer.write_line('Error message', red=True, bold=True)

        # Verify output captured without kwargs
        output = writer.get_output()
        assert output == ['Error message']

    def it_provides_clear_output(self) -> None:
        """It provides clear, readable output format for assertions."""
        writer = StringBufferWriter()

        # Create a simple report
        writer.write_section('Summary', sep='=')
        writer.write_line('Test results here')
        writer.write_separator()

        # Output should be easy to assert on
        output = writer.get_output()
        assert 'SECTION[=]: Summary' in output
        assert 'Test results here' in output
        assert 'SEPARATOR[-]' in output


@pytest.mark.small
class DescribeReportingWithoutPytest:
    """Example tests showing report formatting without pytest dependencies.

    These tests demonstrate the key benefit of OutputWriterPort: we can test
    report formatting logic without needing pytest.TerminalReporter or pytester.
    """

    def it_formats_basic_size_report(self) -> None:
        """It formats a basic test size distribution report."""
        writer = StringBufferWriter()

        # Simulate report formatting (this would be in reporting.py)
        writer.write_section('Test Size Report Summary', sep='=')
        writer.write_line('Test Size Distribution:')
        writer.write_line('    Small: 8 tests (80.00%)')
        writer.write_line('    Medium: 1 test (10.00%)')
        writer.write_line('    Large: 1 test (10.00%)')
        writer.write_line('    Total: 10 tests')
        writer.write_separator(sep='=')

        # Verify the formatted output
        output = writer.get_output()
        assert output[0] == 'SECTION[=]: Test Size Report Summary'
        assert 'Test Size Distribution:' in output
        assert '    Small: 8 tests (80.00%)' in output
        assert '    Total: 10 tests' in output
        assert output[-1] == 'SEPARATOR[=]'

    def it_formats_detailed_test_report(self) -> None:
        """It formats a detailed test report with individual tests."""
        writer = StringBufferWriter()

        # Simulate detailed report formatting
        writer.write_section('Detailed Test Size Report', sep='=')
        writer.write_line('Test Name                                 Size     Duration    Status')
        writer.write_line('------------------------------------------------------------------------')
        writer.write_line('test_module.py::test_fast                small    0.1s      Pass')
        writer.write_line('test_module.py::test_slow                medium   2.5s      Pass')
        writer.write_line('test_module.py::test_failed              large    5.0s      FAIL', red=True)
        writer.write_separator(sep='=')

        # Verify the formatted output
        output = writer.get_output()
        assert 'SECTION[=]: Detailed Test Size Report' in output
        assert 'Test Name' in output[1]
        assert 'test_module.py::test_fast' in output[3]
        assert 'test_module.py::test_slow' in output[4]
        assert 'test_module.py::test_failed' in output[5]  # red=True ignored
        assert output[-1] == 'SEPARATOR[=]'
