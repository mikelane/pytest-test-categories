"""Suggestion summary service for terminal output.

This module provides the SuggestionSummaryService that formats and writes
categorization suggestions to the terminal output. It displays suggestions
grouped by category (upgrade, downgrade, uncategorized) with actionable guidance.

The service follows hexagonal architecture principles:
- Accepts OutputWriterPort for terminal output abstraction
- Uses SuggestionCollector for suggestion data
- Supports both collector-based and direct suggestion list input

Example:
    >>> service = SuggestionSummaryService()
    >>> collector = SuggestionCollector()
    >>> # ... collect observations during test run
    >>> service.write_suggestion_summary(collector, writer)

See Also:
    - suggestion.py: SuggestionCollector and TestSuggestion definitions
    - hermeticity_summary.py: Similar pattern for violation summaries

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytest_test_categories.types import TestSize

if TYPE_CHECKING:
    from pytest_test_categories.suggestion import (
        SuggestionCollector,
        TestSuggestion,
    )
    from pytest_test_categories.types import OutputWriterPort


class SuggestionSummaryService:
    """Service for writing test categorization suggestions to terminal output.

    This service formats and writes a summary of categorization suggestions
    detected during test execution. It groups suggestions by category:
    - Upgrades: Tests that should be larger (e.g., small -> medium)
    - Downgrades: Tests that could be smaller (e.g., medium -> small)
    - Uncategorized: Tests without any size marker

    Example:
        >>> service = SuggestionSummaryService()
        >>> service.write_suggestion_summary(collector, writer)

    """

    def write_suggestion_summary(
        self,
        collector: SuggestionCollector,
        writer: OutputWriterPort,
    ) -> None:
        """Write categorization suggestion summary to terminal output.

        Args:
            collector: SuggestionCollector with recorded observations.
            writer: OutputWriterPort for writing terminal output.

        """
        suggestions = collector.generate_suggestions()
        self.write_suggestions(suggestions, writer)

    def write_suggestions(
        self,
        suggestions: list[TestSuggestion],
        writer: OutputWriterPort,
    ) -> None:
        """Write suggestions from a pre-computed list to terminal output.

        Args:
            suggestions: List of TestSuggestion objects.
            writer: OutputWriterPort for writing terminal output.

        """
        if not suggestions:
            return

        self._write_header(writer)
        self._write_grouped_suggestions(suggestions, writer)
        self._write_json_hint(writer)
        self._write_footer(writer)

    def _write_header(self, writer: OutputWriterPort) -> None:
        """Write the section header."""
        writer.write_section('Test Categorization Suggestions', sep='=')
        writer.write_line('Based on observed behavior, here are suggested categories:')
        writer.write_line('')

    def _write_grouped_suggestions(
        self,
        suggestions: list[TestSuggestion],
        writer: OutputWriterPort,
    ) -> None:
        """Write suggestions grouped by category and transition type."""
        # Group suggestions by (current_size, suggested_size) for accurate headers
        upgrade_groups: dict[tuple[TestSize, TestSize], list[TestSuggestion]] = {}
        downgrade_groups: dict[tuple[TestSize, TestSize], list[TestSuggestion]] = {}
        uncategorized: list[TestSuggestion] = []

        for suggestion in suggestions:
            if suggestion.current_size is None:
                uncategorized.append(suggestion)
            elif self._is_upgrade(suggestion):
                key = (suggestion.current_size, suggestion.suggested_size)
                upgrade_groups.setdefault(key, []).append(suggestion)
            else:
                key = (suggestion.current_size, suggestion.suggested_size)
                downgrade_groups.setdefault(key, []).append(suggestion)

        # Write each group with its own header
        for (current, suggested), group_suggestions in sorted(upgrade_groups.items(), key=lambda x: x[0]):
            self._write_upgrade_section(group_suggestions, current, suggested, writer)

        for (current, suggested), group_suggestions in sorted(downgrade_groups.items(), key=lambda x: x[0]):
            self._write_downgrade_section(group_suggestions, current, suggested, writer)

        if uncategorized:
            self._write_uncategorized_section(uncategorized, writer)

    def _is_upgrade(self, suggestion: TestSuggestion) -> bool:
        """Determine if a suggestion is an upgrade (needs larger category).

        Args:
            suggestion: The suggestion to check.

        Returns:
            True if the suggestion recommends a larger category.

        """
        if suggestion.current_size is None:
            return False

        size_order = {
            TestSize.SMALL: 0,
            TestSize.MEDIUM: 1,
            TestSize.LARGE: 2,
            TestSize.XLARGE: 3,
        }

        current_order = size_order.get(suggestion.current_size, 0)
        suggested_order = size_order.get(suggestion.suggested_size, 0)
        return suggested_order > current_order

    def _write_upgrade_section(
        self,
        suggestions: list[TestSuggestion],
        current_size: TestSize,
        suggested_size: TestSize,
        writer: OutputWriterPort,
    ) -> None:
        """Write section for tests that should be upgraded."""
        writer.write_line(
            f'Currently @pytest.mark.{current_size.value} but should be @pytest.mark.{suggested_size.value}:'
        )
        for suggestion in suggestions:
            writer.write_line(f'  {suggestion.test_nodeid} ({suggestion.reason})')
        writer.write_line('')

    def _write_downgrade_section(
        self,
        suggestions: list[TestSuggestion],
        current_size: TestSize,
        suggested_size: TestSize,
        writer: OutputWriterPort,
    ) -> None:
        """Write section for tests that could be downgraded."""
        writer.write_line(
            f'Currently @pytest.mark.{current_size.value} but could be @pytest.mark.{suggested_size.value}:'
        )
        for suggestion in suggestions:
            writer.write_line(f'  {suggestion.test_nodeid} ({suggestion.reason})')
        writer.write_line('')

    def _write_uncategorized_section(
        self,
        suggestions: list[TestSuggestion],
        writer: OutputWriterPort,
    ) -> None:
        """Write section for uncategorized tests."""
        writer.write_line('Uncategorized tests - suggested categories:')
        for suggestion in suggestions:
            writer.write_line(
                f'  {suggestion.test_nodeid} -> @pytest.mark.{suggestion.suggested_size.value} ({suggestion.reason})'
            )
        writer.write_line('')

    def _write_json_hint(self, writer: OutputWriterPort) -> None:
        """Write hint about JSON output option."""
        writer.write_line('Run with --test-categories-suggest-output=suggestions.json for machine-readable output')

    def _write_footer(self, writer: OutputWriterPort) -> None:
        """Write closing separator."""
        writer.write_separator(sep='=')
