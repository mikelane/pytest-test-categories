"""Hermeticity summary service for terminal output.

This module provides the HermeticitySummaryService that formats and writes
violation summaries to the terminal output. It displays violations by type
with actionable guidance for remediation.

The service follows hexagonal architecture principles:
- Accepts OutputWriterPort for terminal output abstraction
- Uses ViolationTracker for violation data
- Supports both verbose and quiet output modes

Example:
    >>> service = HermeticitySummaryService()
    >>> tracker = ViolationTracker()
    >>> tracker.record_violation(ViolationType.NETWORK, 'test.py::test_fn', 'details')
    >>> service.write_hermeticity_summary(tracker, EnforcementMode.WARN, writer)

See Also:
    - violation_tracking.py: ViolationTracker and ViolationType definitions
    - ports/network.py: EnforcementMode enum

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytest_test_categories.ports.network import EnforcementMode
from pytest_test_categories.violation_tracking import (
    ViolationTracker,
    ViolationType,
)

if TYPE_CHECKING:
    from pytest_test_categories.types import OutputWriterPort

# Maximum number of test nodeids to display before truncating
MAX_DISPLAYED_TESTS = 3

# Documentation URL for resource isolation
DOCS_URL = 'https://pytest-test-categories.readthedocs.io/resource-isolation/'


class HermeticitySummaryService:
    """Service for writing hermeticity violation summaries to terminal output.

    This service formats and writes a summary of all hermeticity violations
    detected during test execution. It shows violations grouped by type
    with counts, test nodeids, and remediation guidance.

    The output adapts based on:
    - Enforcement mode (warn vs strict)
    - Output verbosity (quiet mode)
    - Number of violations per type

    Example:
        >>> service = HermeticitySummaryService()
        >>> service.write_hermeticity_summary(tracker, EnforcementMode.WARN, writer)

    """

    def write_hermeticity_summary(
        self,
        tracker: ViolationTracker,
        enforcement_mode: EnforcementMode,
        writer: OutputWriterPort,
        *,
        quiet: bool = False,
    ) -> None:
        """Write hermeticity violation summary to terminal output.

        Args:
            tracker: ViolationTracker with recorded violations.
            enforcement_mode: Current enforcement mode (warn/strict).
            writer: OutputWriterPort for writing terminal output.
            quiet: If True, show condensed output without individual test nodeids.

        """
        if not tracker.has_violations:
            return

        self._write_header(writer, enforcement_mode)
        self._write_violation_breakdown(tracker, writer, quiet=quiet)
        self._write_totals(tracker, writer, enforcement_mode)
        self._write_remediation(writer)
        self._write_footer(writer)

    def _write_header(
        self,
        writer: OutputWriterPort,
        enforcement_mode: EnforcementMode,
    ) -> None:
        """Write the section header with enforcement mode."""
        writer.write_section('Hermeticity Violation Summary', sep='=')
        mode_name = enforcement_mode.value.lower()
        writer.write_line(f'Violations detected (enforcement: {mode_name}):')

    def _write_violation_breakdown(
        self,
        tracker: ViolationTracker,
        writer: OutputWriterPort,
        *,
        quiet: bool = False,
    ) -> None:
        """Write breakdown of violations by type."""
        for violation_type in ViolationType:
            count = tracker.count_by_type(violation_type)

            # In quiet mode, skip types with zero violations
            if quiet and count == 0:
                continue

            test_word = 'test' if count == 1 else 'tests'
            line = f'  {violation_type.display_name}:{" " * (12 - len(violation_type.display_name))}{count} {test_word}'

            # Add test nodeids in verbose mode
            if not quiet and count > 0:
                nodeids = tracker.get_test_nodeids_by_type(violation_type)
                if len(nodeids) <= MAX_DISPLAYED_TESTS:
                    nodeids_str = ', '.join(nodeids)
                else:
                    displayed = nodeids[:MAX_DISPLAYED_TESTS]
                    remaining = len(nodeids) - MAX_DISPLAYED_TESTS
                    nodeids_str = f'{", ".join(displayed)}, ...+{remaining} more'
                line += f' ({nodeids_str})'

            writer.write_line(line)

    def _write_totals(
        self,
        tracker: ViolationTracker,
        writer: OutputWriterPort,
        enforcement_mode: EnforcementMode,
    ) -> None:
        """Write total violations and unique test count."""
        writer.write_line('')  # Blank line before totals
        total = tracker.total_violations
        unique_tests = tracker.unique_test_count
        test_word = 'test' if unique_tests == 1 else 'tests'
        writer.write_line(f'Total: {total} violations in {unique_tests} {test_word}')

        # In strict mode, show failed test count
        if enforcement_mode == EnforcementMode.STRICT:
            failed = tracker.get_failed_tests()
            if failed:
                failed_word = 'test' if len(failed) == 1 else 'tests'
                writer.write_line(f'{len(failed)} {failed_word} failed due to violations')

    def _write_remediation(self, writer: OutputWriterPort) -> None:
        """Write remediation guidance."""
        writer.write_line('')  # Blank line before guidance
        writer.write_line('To fix: Mock external dependencies or change test category to @pytest.mark.medium')
        writer.write_line(f'Docs: {DOCS_URL}')

    def _write_footer(self, writer: OutputWriterPort) -> None:
        """Write closing separator."""
        writer.write_separator(sep='=')
