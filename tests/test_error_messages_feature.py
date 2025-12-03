"""Test error message formatting and remediation guidance.

This module tests that all error and warning messages follow the standard format:
1. What happened: Clear description of the violation
2. Why it matters: Brief explanation of the rule
3. How to fix: Specific remediation options

Error codes are used for grep-friendly CI log parsing (e.g., TC001, TC002).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pytest_test_categories.errors import (
    ERROR_CODES,
    format_error_message,
)
from pytest_test_categories.exceptions import (
    DatabaseViolationError,
    FilesystemAccessViolationError,
    NetworkAccessViolationError,
    SleepViolationError,
    SubprocessViolationError,
)
from pytest_test_categories.ports.filesystem import FilesystemOperation
from pytest_test_categories.timing import TimingViolationError
from pytest_test_categories.types import TestSize


@pytest.mark.small
class DescribeErrorCodes:
    """Tests for the centralized error code registry."""

    def it_has_unique_error_codes(self) -> None:
        """Verify all error codes are unique."""
        codes = [ec.code for ec in ERROR_CODES.values()]

        assert len(codes) == len(set(codes))

    def it_has_documentation_links(self) -> None:
        """Verify all error codes have documentation links."""
        for error_code in ERROR_CODES.values():
            assert error_code.doc_url.startswith('https://')
            assert 'pytest-test-categories' in error_code.doc_url

    def it_has_all_violation_types(self) -> None:
        """Verify all violation types have error codes."""
        expected_types = [
            'network_violation',
            'filesystem_violation',
            'subprocess_violation',
            'database_violation',
            'sleep_violation',
            'timing_violation',
            'distribution_warning',
        ]

        for violation_type in expected_types:
            assert violation_type in ERROR_CODES

    def it_has_meaningful_descriptions(self) -> None:
        """Verify error codes have non-empty descriptions."""
        for error_code in ERROR_CODES.values():
            assert len(error_code.title) > 10
            assert len(error_code.why_it_matters) > 20


@pytest.mark.small
class DescribeFormatErrorMessage:
    """Tests for the error message formatting function."""

    def it_includes_error_code(self) -> None:
        """Verify formatted messages include the error code."""
        error_code = ERROR_CODES['network_violation']

        message = format_error_message(
            error_code=error_code,
            what_happened='Test attempted network connection to api.example.com:443',
            remediation=['Mock the network call', 'Use dependency injection'],
        )

        assert 'TC001' in message

    def it_includes_what_happened_section(self) -> None:
        """Verify formatted messages include what happened."""
        error_code = ERROR_CODES['network_violation']

        message = format_error_message(
            error_code=error_code,
            what_happened='Test attempted network connection to api.example.com:443',
            remediation=['Mock the network call'],
        )

        assert 'api.example.com:443' in message

    def it_includes_why_it_matters_section(self) -> None:
        """Verify formatted messages include why it matters."""
        error_code = ERROR_CODES['network_violation']

        message = format_error_message(
            error_code=error_code,
            what_happened='Test attempted network connection',
            remediation=['Mock the network call'],
        )

        assert error_code.why_it_matters in message

    def it_includes_remediation_section(self) -> None:
        """Verify formatted messages include bullet-point remediation options."""
        error_code = ERROR_CODES['network_violation']

        message = format_error_message(
            error_code=error_code,
            what_happened='Test attempted network connection',
            remediation=['Mock the network call', 'Use dependency injection'],
        )

        assert 'To fix this (choose one):' in message
        assert '\u2022 Mock the network call' in message
        assert '\u2022 Use dependency injection' in message

    def it_includes_documentation_link(self) -> None:
        """Verify formatted messages include documentation link."""
        error_code = ERROR_CODES['network_violation']

        message = format_error_message(
            error_code=error_code,
            what_happened='Test attempted network connection',
            remediation=['Mock the network call'],
        )

        assert error_code.doc_url in message


@pytest.mark.small
class DescribeNetworkAccessViolationError:
    """Tests for NetworkAccessViolationError message format."""

    def it_includes_error_code(self) -> None:
        """Verify exception message includes error code."""
        exc = NetworkAccessViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_api.py::test_fetch',
            host='api.example.com',
            port=443,
        )

        assert 'TC001' in str(exc)

    def it_includes_host_and_port(self) -> None:
        """Verify exception message includes connection details."""
        exc = NetworkAccessViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_api.py::test_fetch',
            host='api.example.com',
            port=443,
        )

        assert 'api.example.com' in str(exc)
        assert '443' in str(exc)

    def it_includes_remediation_for_small_tests(self) -> None:
        """Verify small test errors include appropriate remediation."""
        exc = NetworkAccessViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_api.py::test_fetch',
            host='api.example.com',
            port=443,
        )

        message = str(exc)

        assert 'mock' in message.lower() or 'Mock' in message
        assert '@pytest.mark.medium' in message

    def it_includes_remediation_for_medium_tests(self) -> None:
        """Verify medium test errors include appropriate remediation."""
        exc = NetworkAccessViolationError(
            test_size=TestSize.MEDIUM,
            test_nodeid='tests/test_api.py::test_fetch',
            host='api.example.com',
            port=443,
        )

        message = str(exc)

        assert 'localhost' in message.lower()
        assert '@pytest.mark.large' in message

    def it_includes_documentation_link(self) -> None:
        """Verify exception message includes documentation link."""
        exc = NetworkAccessViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_api.py::test_fetch',
            host='api.example.com',
            port=443,
        )

        assert 'https://' in str(exc)


@pytest.mark.small
class DescribeFilesystemAccessViolationError:
    """Tests for FilesystemAccessViolationError message format."""

    def it_includes_error_code(self) -> None:
        """Verify exception message includes error code."""
        exc = FilesystemAccessViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_file.py::test_save',
            path=Path('/etc/passwd'),
            operation=FilesystemOperation.READ,
        )

        assert 'TC002' in str(exc)

    def it_includes_path_and_operation(self) -> None:
        """Verify exception message includes filesystem details."""
        exc = FilesystemAccessViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_file.py::test_save',
            path=Path('/etc/passwd'),
            operation=FilesystemOperation.READ,
        )

        # Use str(Path()) for cross-platform path representation (Unix: /etc/passwd, Windows: \etc\passwd)
        assert str(Path('/etc/passwd')) in str(exc)
        assert 'read' in str(exc).lower()

    def it_includes_remediation(self) -> None:
        """Verify exception message includes remediation guidance."""
        exc = FilesystemAccessViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_file.py::test_save',
            path=Path('/var/data/testfile'),
            operation=FilesystemOperation.WRITE,
        )

        message = str(exc)

        assert 'tmp_path' in message
        assert '@pytest.mark.medium' in message

    def it_includes_documentation_link(self) -> None:
        """Verify exception message includes documentation link."""
        exc = FilesystemAccessViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_file.py::test_save',
            path=Path('/var/data/testfile'),
            operation=FilesystemOperation.WRITE,
        )

        assert 'https://' in str(exc)


@pytest.mark.small
class DescribeSubprocessViolationError:
    """Tests for SubprocessViolationError message format."""

    def it_includes_error_code(self) -> None:
        """Verify exception message includes error code."""
        exc = SubprocessViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_cli.py::test_run',
            command='python',
            command_args=('script.py', '--verbose'),
            method='subprocess.run',
        )

        assert 'TC003' in str(exc)

    def it_includes_command_details(self) -> None:
        """Verify exception message includes command information."""
        exc = SubprocessViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_cli.py::test_run',
            command='python',
            command_args=('script.py', '--verbose'),
            method='subprocess.run',
        )

        message = str(exc)

        assert 'python' in message
        assert 'script.py' in message
        assert 'subprocess.run' in message

    def it_includes_remediation(self) -> None:
        """Verify exception message includes remediation guidance."""
        exc = SubprocessViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_cli.py::test_run',
            command='python',
            command_args=('script.py',),
            method='subprocess.run',
        )

        message = str(exc)

        assert 'mock' in message.lower() or 'Mock' in message
        assert '@pytest.mark.medium' in message

    def it_includes_documentation_link(self) -> None:
        """Verify exception message includes documentation link."""
        exc = SubprocessViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_cli.py::test_run',
            command='python',
            command_args=(),
            method='subprocess.run',
        )

        assert 'https://' in str(exc)


@pytest.mark.small
class DescribeDatabaseViolationError:
    """Tests for DatabaseViolationError message format."""

    def it_includes_error_code(self) -> None:
        """Verify exception message includes error code."""
        exc = DatabaseViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_db.py::test_query',
            library='sqlite3',
            connection_string=':memory:',
        )

        assert 'TC004' in str(exc)

    def it_includes_database_details(self) -> None:
        """Verify exception message includes database information."""
        exc = DatabaseViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_db.py::test_query',
            library='sqlite3',
            connection_string=':memory:',
        )

        message = str(exc)

        assert 'sqlite3' in message
        assert ':memory:' in message

    def it_includes_remediation(self) -> None:
        """Verify exception message includes remediation guidance."""
        exc = DatabaseViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_db.py::test_query',
            library='sqlite3',
            connection_string=':memory:',
        )

        message = str(exc)

        assert 'mock' in message.lower() or 'Mock' in message
        assert '@pytest.mark.medium' in message

    def it_includes_documentation_link(self) -> None:
        """Verify exception message includes documentation link."""
        exc = DatabaseViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_db.py::test_query',
            library='sqlite3',
            connection_string=':memory:',
        )

        assert 'https://' in str(exc)


@pytest.mark.small
class DescribeSleepViolationError:
    """Tests for SleepViolationError message format."""

    def it_includes_error_code(self) -> None:
        """Verify exception message includes error code."""
        exc = SleepViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_timing.py::test_delay',
            function='time.sleep',
            duration=0.5,
        )

        assert 'TC005' in str(exc)

    def it_includes_sleep_details(self) -> None:
        """Verify exception message includes sleep information."""
        exc = SleepViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_timing.py::test_delay',
            function='time.sleep',
            duration=0.5,
        )

        message = str(exc)

        assert 'time.sleep' in message
        assert '0.5' in message

    def it_includes_remediation(self) -> None:
        """Verify exception message includes remediation guidance."""
        exc = SleepViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_timing.py::test_delay',
            function='time.sleep',
            duration=0.5,
        )

        message = str(exc)

        assert 'mock' in message.lower() or 'Mock' in message or 'synchronization' in message.lower()
        assert '@pytest.mark.medium' in message

    def it_includes_documentation_link(self) -> None:
        """Verify exception message includes documentation link."""
        exc = SleepViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_timing.py::test_delay',
            function='time.sleep',
            duration=0.5,
        )

        assert 'https://' in str(exc)


@pytest.mark.small
class DescribeTimingViolationError:
    """Tests for TimingViolationError message format."""

    def it_includes_error_code(self) -> None:
        """Verify exception message includes error code."""
        exc = TimingViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_slow.py::test_compute',
            limit=1.0,
            actual=2.5,
        )

        assert 'TC006' in str(exc)

    def it_includes_timing_details(self) -> None:
        """Verify exception message includes timing information."""
        exc = TimingViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_slow.py::test_compute',
            limit=1.0,
            actual=2.5,
        )

        message = str(exc)

        assert '1.0' in message or '1' in message
        assert '2.5' in message

    def it_includes_remediation(self) -> None:
        """Verify exception message includes remediation guidance."""
        exc = TimingViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_slow.py::test_compute',
            limit=1.0,
            actual=2.5,
        )

        message = str(exc)

        assert 'optimize' in message.lower() or '@pytest.mark.medium' in message

    def it_includes_documentation_link(self) -> None:
        """Verify exception message includes documentation link."""
        exc = TimingViolationError(
            test_size=TestSize.SMALL,
            test_nodeid='tests/test_slow.py::test_compute',
            limit=1.0,
            actual=2.5,
        )

        assert 'https://' in str(exc)


@pytest.mark.small
class DescribeRemediationEdgeCases:
    """Tests for remediation edge cases for larger test sizes."""

    def it_returns_empty_remediation_for_large_network_violations(self) -> None:
        """Verify large test size returns empty remediation for network violations."""
        exc = NetworkAccessViolationError(
            test_size=TestSize.LARGE,
            test_nodeid='tests/test_api.py::test_fetch',
            host='api.example.com',
            port=443,
        )

        # Large tests have full network access, so remediation is empty
        assert exc.remediation == []

    def it_returns_empty_remediation_for_large_filesystem_violations(self) -> None:
        """Verify large test size returns empty remediation for filesystem violations."""
        exc = FilesystemAccessViolationError(
            test_size=TestSize.LARGE,
            test_nodeid='tests/test_file.py::test_save',
            path=Path('/var/data/testfile'),
            operation=FilesystemOperation.WRITE,
        )

        # Large tests have full filesystem access, so remediation is empty
        assert exc.remediation == []

    def it_returns_empty_remediation_for_large_subprocess_violations(self) -> None:
        """Verify large test size returns empty remediation for subprocess violations."""
        exc = SubprocessViolationError(
            test_size=TestSize.LARGE,
            test_nodeid='tests/test_cli.py::test_run',
            command='python',
            command_args=('script.py',),
            method='subprocess.run',
        )

        # Large tests can spawn subprocesses, so remediation is empty
        assert exc.remediation == []

    def it_returns_empty_remediation_for_large_database_violations(self) -> None:
        """Verify large test size returns empty remediation for database violations."""
        exc = DatabaseViolationError(
            test_size=TestSize.LARGE,
            test_nodeid='tests/test_db.py::test_query',
            library='sqlite3',
            connection_string=':memory:',
        )

        # Large tests can access databases, so remediation is empty
        assert exc.remediation == []

    def it_returns_empty_remediation_for_large_sleep_violations(self) -> None:
        """Verify large test size returns empty remediation for sleep violations."""
        exc = SleepViolationError(
            test_size=TestSize.LARGE,
            test_nodeid='tests/test_timing.py::test_delay',
            function='time.sleep',
            duration=0.5,
        )

        # Large tests can sleep, so remediation is empty
        assert exc.remediation == []


@pytest.mark.small
class DescribeErrorCodeFormat:
    """Tests for error code format consistency."""

    def it_uses_tc_prefix(self) -> None:
        """Verify all error codes use TC prefix."""
        for error_code in ERROR_CODES.values():
            assert error_code.code.startswith('TC')

    def it_uses_three_digit_numbers(self) -> None:
        """Verify all error codes use three-digit numbers."""
        for error_code in ERROR_CODES.values():
            numeric_part = error_code.code[2:]

            assert len(numeric_part) == 3
            assert numeric_part.isdigit()

    def it_is_grep_friendly(self) -> None:
        """Verify error codes can be easily grep'd from logs."""
        error_code = ERROR_CODES['network_violation']

        message = format_error_message(
            error_code=error_code,
            what_happened='Test attempted network connection',
            remediation=['Mock the network call'],
        )

        # Error code should appear at start of message or on its own line
        lines = message.split('\n')
        code_found_prominently = any(
            line.strip().startswith(error_code.code) or f'[{error_code.code}]' in line for line in lines
        )

        assert code_found_prominently
