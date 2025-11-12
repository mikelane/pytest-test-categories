"""String buffer writer implementation for testing.

This module provides StringBufferWriter, a controllable test double that implements
the OutputWriterPort interface. It's used in tests as a substitute for
pytest.TerminalReporter to enable deterministic testing without pytest's terminal
reporter complexity.

The StringBufferWriter follows hexagonal architecture principles:
- Implements the OutputWriterPort interface
- Provides controllable output capture to a list
- Used in tests as a substitute for TerminalReporterAdapter
- Enables testing report formatting without pytest dependencies
"""

from __future__ import annotations

from pytest_test_categories.types import OutputWriterPort


class StringBufferWriter(OutputWriterPort):
    """Controllable output writer adapter for testing.

    This is a test double that captures output to a list of strings, allowing tests
    to verify report formatting without depending on pytest.TerminalReporter. This
    eliminates test complexity and makes tests deterministic.

    The StringBufferWriter follows hexagonal architecture principles:
    - Implements the OutputWriterPort interface
    - Captures all output to an in-memory buffer
    - Provides get_output() method for assertions
    - Used in tests as a substitute for TerminalReporterAdapter

    Example:
        >>> writer = StringBufferWriter()
        >>> writer.write_section('Test Report', sep='=')
        >>> writer.write_line('Total: 10 tests')
        >>> writer.write_separator()
        >>> output = writer.get_output()
        >>> print(output)
        ['SECTION[=]: Test Report', 'Total: 10 tests', 'SEPARATOR[-]']

    """

    def __init__(self) -> None:
        """Initialize the string buffer writer with an empty buffer."""
        self._buffer: list[str] = []

    def write_section(self, title: str, sep: str = '=') -> None:
        """Write a section header to the buffer.

        Captures the section header in a format that's easy to assert on:
        "SECTION[sep]: title"

        Args:
            title: The section title to display.
            sep: The separator character to use (default: '=').

        """
        self._buffer.append(f'SECTION[{sep}]: {title}')

    def write_line(self, message: str, **kwargs: object) -> None:
        """Write a single line of text to the buffer.

        Captures the message text, ignoring any styling kwargs since this is
        just for testing and we only care about the content.

        Args:
            message: The message to write.
            **kwargs: Additional styling arguments (ignored).

        """
        self._buffer.append(message)

    def write_separator(self, sep: str = '-') -> None:
        """Write a separator line to the buffer.

        Captures the separator in a format that's easy to assert on:
        "SEPARATOR[sep]"

        Args:
            sep: The separator character to use (default: '-').

        """
        self._buffer.append(f'SEPARATOR[{sep}]')

    def get_output(self) -> list[str]:
        """Get the captured output as a list of strings.

        Returns:
            A list of all captured output lines in the order they were written.

        """
        return self._buffer
