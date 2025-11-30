"""Unit tests for hermeticity summary service module.

This module tests the HermeticitySummaryService that formats and writes
violation summaries to the terminal output.
"""

from __future__ import annotations

import pytest

from pytest_test_categories.ports.network import EnforcementMode
from pytest_test_categories.services.hermeticity_summary import HermeticitySummaryService
from pytest_test_categories.violation_tracking import (
    ViolationTracker,
    ViolationType,
)
from tests._fixtures.output_writer import StringBufferWriter


@pytest.mark.small
class DescribeHermeticitySummaryService:
    """Test suite for HermeticitySummaryService."""

    def it_does_not_write_summary_when_no_violations(self) -> None:
        """No output when violation tracker is empty."""
        service = HermeticitySummaryService()
        tracker = ViolationTracker()
        writer = StringBufferWriter()

        service.write_hermeticity_summary(tracker, EnforcementMode.WARN, writer)

        output = writer.get_output()
        assert output == []

    def it_writes_section_header_when_violations_exist(self) -> None:
        """Write section header when violations are present."""
        service = HermeticitySummaryService()
        tracker = ViolationTracker()
        tracker.record_violation(ViolationType.NETWORK, 'test_api.py::test_fetch', 'details')
        writer = StringBufferWriter()

        service.write_hermeticity_summary(tracker, EnforcementMode.WARN, writer)

        output = writer.get_output()
        assert any('Hermeticity Violation Summary' in line for line in output)

    def it_shows_enforcement_mode_in_header(self) -> None:
        """Show enforcement mode in the violations detected line."""
        service = HermeticitySummaryService()
        tracker = ViolationTracker()
        tracker.record_violation(ViolationType.NETWORK, 'test_api.py::test_fetch', 'details')
        writer = StringBufferWriter()

        service.write_hermeticity_summary(tracker, EnforcementMode.WARN, writer)

        output = writer.get_output()
        assert any('enforcement: warn' in line for line in output)

    def it_shows_strict_enforcement_mode(self) -> None:
        """Show strict enforcement mode when applicable."""
        service = HermeticitySummaryService()
        tracker = ViolationTracker()
        tracker.record_violation(ViolationType.NETWORK, 'test_api.py::test_fetch', 'details', failed=True)
        writer = StringBufferWriter()

        service.write_hermeticity_summary(tracker, EnforcementMode.STRICT, writer)

        output = writer.get_output()
        assert any('enforcement: strict' in line for line in output)

    def it_shows_violation_count_by_type(self) -> None:
        """Show count of violations for each type."""
        service = HermeticitySummaryService()
        tracker = ViolationTracker()
        tracker.record_violation(ViolationType.NETWORK, 'test_api.py::test_fetch', 'details')
        tracker.record_violation(ViolationType.NETWORK, 'test_client.py::test_connect', 'details')
        tracker.record_violation(ViolationType.FILESYSTEM, 'test_config.py::test_load', 'details')
        writer = StringBufferWriter()

        service.write_hermeticity_summary(tracker, EnforcementMode.WARN, writer)

        output = writer.get_output()
        # Should show Network: 2 tests
        assert any('Network:' in line and '2' in line for line in output)
        # Should show Filesystem: 1 test
        assert any('Filesystem:' in line and '1' in line for line in output)

    def it_shows_zero_for_unused_violation_types(self) -> None:
        """Show 0 for violation types with no violations."""
        service = HermeticitySummaryService()
        tracker = ViolationTracker()
        tracker.record_violation(ViolationType.NETWORK, 'test_api.py::test_fetch', 'details')
        writer = StringBufferWriter()

        service.write_hermeticity_summary(tracker, EnforcementMode.WARN, writer)

        output = writer.get_output()
        # Types with no violations should show 0
        assert any('Process:' in line and '0' in line for line in output)
        assert any('Database:' in line and '0' in line for line in output)
        assert any('Sleep:' in line and '0' in line for line in output)

    def it_shows_test_nodeids_for_violations(self) -> None:
        """Show test nodeids in the violation summary."""
        service = HermeticitySummaryService()
        tracker = ViolationTracker()
        tracker.record_violation(ViolationType.NETWORK, 'test_api.py::test_fetch', 'details')
        writer = StringBufferWriter()

        service.write_hermeticity_summary(tracker, EnforcementMode.WARN, writer)

        output = writer.get_output()
        # Should show the test nodeid
        assert any('test_api.py::test_fetch' in line for line in output)

    def it_truncates_long_test_lists_with_ellipsis(self) -> None:
        """Truncate test list when too many violations."""
        service = HermeticitySummaryService()
        tracker = ViolationTracker()
        # Add more than max_displayed tests
        for i in range(10):
            tracker.record_violation(ViolationType.NETWORK, f'test_api.py::test_{i}', 'details')
        writer = StringBufferWriter()

        service.write_hermeticity_summary(tracker, EnforcementMode.WARN, writer)

        output = writer.get_output()
        # Should contain ellipsis indicating more tests
        assert any('...' in line for line in output)

    def it_shows_total_violations(self) -> None:
        """Show total violations count."""
        service = HermeticitySummaryService()
        tracker = ViolationTracker()
        tracker.record_violation(ViolationType.NETWORK, 'test_api.py::test_fetch', 'details')
        tracker.record_violation(ViolationType.FILESYSTEM, 'test_config.py::test_load', 'details')
        tracker.record_violation(ViolationType.DATABASE, 'test_repo.py::test_query', 'details')
        writer = StringBufferWriter()

        service.write_hermeticity_summary(tracker, EnforcementMode.WARN, writer)

        output = writer.get_output()
        # Should show total count
        assert any('Total:' in line and '3' in line for line in output)

    def it_shows_unique_test_count(self) -> None:
        """Show count of unique tests with violations."""
        service = HermeticitySummaryService()
        tracker = ViolationTracker()
        # Same test with multiple violation types
        tracker.record_violation(ViolationType.NETWORK, 'test_api.py::test_fetch', 'details')
        tracker.record_violation(ViolationType.DATABASE, 'test_api.py::test_fetch', 'details')
        # Different test
        tracker.record_violation(ViolationType.FILESYSTEM, 'test_config.py::test_load', 'details')
        writer = StringBufferWriter()

        service.write_hermeticity_summary(tracker, EnforcementMode.WARN, writer)

        output = writer.get_output()
        # Should show unique test count (2 tests, not 3 violations)
        assert any('2 tests' in line for line in output) or any('in 2' in line for line in output)

    def it_shows_remediation_guidance(self) -> None:
        """Show remediation guidance at the end."""
        service = HermeticitySummaryService()
        tracker = ViolationTracker()
        tracker.record_violation(ViolationType.NETWORK, 'test_api.py::test_fetch', 'details')
        writer = StringBufferWriter()

        service.write_hermeticity_summary(tracker, EnforcementMode.WARN, writer)

        output = writer.get_output()
        # Should show guidance to fix
        assert any('To fix:' in line or 'Mock' in line for line in output)

    def it_shows_documentation_link(self) -> None:
        """Show link to documentation."""
        service = HermeticitySummaryService()
        tracker = ViolationTracker()
        tracker.record_violation(ViolationType.NETWORK, 'test_api.py::test_fetch', 'details')
        writer = StringBufferWriter()

        service.write_hermeticity_summary(tracker, EnforcementMode.WARN, writer)

        output = writer.get_output()
        # Should show documentation link
        assert any('Docs:' in line or 'readthedocs' in line for line in output)

    def it_writes_closing_separator(self) -> None:
        """Write closing separator at the end."""
        service = HermeticitySummaryService()
        tracker = ViolationTracker()
        tracker.record_violation(ViolationType.NETWORK, 'test_api.py::test_fetch', 'details')
        writer = StringBufferWriter()

        service.write_hermeticity_summary(tracker, EnforcementMode.WARN, writer)

        output = writer.get_output()
        # Should end with separator
        assert output[-1] == 'SEPARATOR[=]'


@pytest.mark.small
class DescribeHermeticitySummaryQuietMode:
    """Test suite for quiet mode behavior."""

    def it_shows_shorter_summary_in_quiet_mode(self) -> None:
        """Show condensed summary in quiet mode."""
        service = HermeticitySummaryService()
        tracker = ViolationTracker()
        tracker.record_violation(ViolationType.NETWORK, 'test_api.py::test_fetch', 'details')
        tracker.record_violation(ViolationType.FILESYSTEM, 'test_config.py::test_load', 'details')
        writer = StringBufferWriter()

        service.write_hermeticity_summary(tracker, EnforcementMode.WARN, writer, quiet=True)

        output = writer.get_output()
        # Quiet mode should have fewer lines than verbose mode
        # Just show total and types with violations
        assert len(output) < 15  # Reasonable limit for quiet output

    def it_omits_zero_count_types_in_quiet_mode(self) -> None:
        """Omit violation types with zero count in quiet mode."""
        service = HermeticitySummaryService()
        tracker = ViolationTracker()
        tracker.record_violation(ViolationType.NETWORK, 'test_api.py::test_fetch', 'details')
        writer = StringBufferWriter()

        service.write_hermeticity_summary(tracker, EnforcementMode.WARN, writer, quiet=True)

        output = writer.get_output()
        # Should not show types with 0 violations
        assert not any('Process:' in line and '0' in line for line in output)
        assert not any('Database:' in line and '0' in line for line in output)
        assert not any('Sleep:' in line and '0' in line for line in output)

    def it_omits_test_nodeids_in_quiet_mode(self) -> None:
        """Omit individual test nodeids in quiet mode."""
        service = HermeticitySummaryService()
        tracker = ViolationTracker()
        tracker.record_violation(ViolationType.NETWORK, 'test_api.py::test_fetch', 'details')
        writer = StringBufferWriter()

        service.write_hermeticity_summary(tracker, EnforcementMode.WARN, writer, quiet=True)

        output = writer.get_output()
        # Should not show individual test nodeids (just counts)
        # The test nodeid format test_api.py::test_fetch should not appear in parentheses
        assert not any('test_api.py::test_fetch' in line and '(' in line for line in output)


@pytest.mark.small
class DescribeHermeticitySummaryStrictMode:
    """Test suite for strict mode behavior."""

    def it_indicates_failed_tests_in_strict_mode(self) -> None:
        """Indicate which tests failed due to violations in strict mode."""
        service = HermeticitySummaryService()
        tracker = ViolationTracker()
        tracker.record_violation(ViolationType.NETWORK, 'test_api.py::test_fetch', 'details', failed=True)
        tracker.record_violation(ViolationType.NETWORK, 'test_client.py::test_connect', 'details', failed=True)
        writer = StringBufferWriter()

        service.write_hermeticity_summary(tracker, EnforcementMode.STRICT, writer)

        output = writer.get_output()
        # Should indicate tests failed
        assert any('failed' in line.lower() for line in output)

    def it_shows_failed_test_count(self) -> None:
        """Show count of tests that failed due to violations."""
        service = HermeticitySummaryService()
        tracker = ViolationTracker()
        tracker.record_violation(ViolationType.NETWORK, 'test_api.py::test_fetch', 'details', failed=True)
        tracker.record_violation(ViolationType.NETWORK, 'test_client.py::test_connect', 'details', failed=True)
        writer = StringBufferWriter()

        service.write_hermeticity_summary(tracker, EnforcementMode.STRICT, writer)

        output = writer.get_output()
        # Should show how many tests failed
        assert any('2' in line and 'failed' in line.lower() for line in output)
