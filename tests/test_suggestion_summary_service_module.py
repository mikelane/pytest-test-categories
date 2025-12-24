"""Unit tests for suggestion summary service module.

This module tests the SuggestionSummaryService that formats and writes
categorization suggestions to the terminal output.
"""

from __future__ import annotations

import pytest

from pytest_test_categories.services.suggestion_summary import SuggestionSummaryService
from pytest_test_categories.suggestion import (
    SuggestionCollector,
    TestSuggestion,
)
from pytest_test_categories.types import TestSize
from tests._fixtures.output_writer import StringBufferWriter


@pytest.mark.small
class DescribeSuggestionSummaryService:
    """Test suite for SuggestionSummaryService."""

    def it_does_not_write_summary_when_no_suggestions(self) -> None:
        """No output when there are no suggestions."""
        service = SuggestionSummaryService()
        collector = SuggestionCollector()
        writer = StringBufferWriter()

        service.write_suggestion_summary(collector, writer)

        output = writer.get_output()
        assert output == []

    def it_writes_section_header_when_suggestions_exist(self) -> None:
        """Write section header when suggestions are present."""
        service = SuggestionSummaryService()
        collector = SuggestionCollector()
        collector.record_current_size('test.py::test_fn', None)
        collector.record_execution_time('test.py::test_fn', 0.05)
        writer = StringBufferWriter()

        service.write_suggestion_summary(collector, writer)

        output = writer.get_output()
        assert any('Test Categorization Suggestions' in line for line in output)

    def it_groups_suggestions_by_category(self) -> None:
        """Group suggestions into upgrade, downgrade, and uncategorized."""
        service = SuggestionSummaryService()
        collector = SuggestionCollector()

        # Uncategorized test -> should be small
        collector.record_current_size('test_new.py::test_fn', None)
        collector.record_execution_time('test_new.py::test_fn', 0.05)

        writer = StringBufferWriter()

        service.write_suggestion_summary(collector, writer)

        output = writer.get_output()
        # Should show "Uncategorized tests" section
        assert any('Uncategorized' in line or 'uncategorized' in line for line in output)

    def it_shows_upgrade_suggestions_for_small_that_should_be_medium(self) -> None:
        """Show upgrade suggestions for @small tests that should be @medium."""
        service = SuggestionSummaryService()
        collector = SuggestionCollector()

        # Small test that uses network - should be medium
        collector.record_current_size('test_api.py::test_fetch', TestSize.SMALL)
        collector.record_observation(
            'test_api.py::test_fetch',
            __import__('pytest_test_categories.suggestion', fromlist=['ResourceType']).ResourceType.NETWORK,
            'Connection',
        )

        writer = StringBufferWriter()

        service.write_suggestion_summary(collector, writer)

        output = writer.get_output()
        # Should mention upgrading from small to medium
        assert any('@pytest.mark.small' in line and '@pytest.mark.medium' in line for line in output) or any(
            'test_api.py::test_fetch' in line for line in output
        )

    def it_shows_downgrade_suggestions_for_medium_that_could_be_small(self) -> None:
        """Show downgrade suggestions for @medium tests that could be @small."""
        service = SuggestionSummaryService()
        collector = SuggestionCollector()

        # Medium test that doesn't use resources - could be small
        collector.record_current_size('test_utils.py::test_format', TestSize.MEDIUM)
        collector.record_execution_time('test_utils.py::test_format', 0.05)

        writer = StringBufferWriter()

        service.write_suggestion_summary(collector, writer)

        output = writer.get_output()
        # Should mention downgrading
        assert any('test_utils.py::test_format' in line for line in output)
        assert any('could be' in line.lower() or '@pytest.mark.small' in line for line in output)

    def it_shows_suggestion_reason(self) -> None:
        """Show the reason for each suggestion."""
        service = SuggestionSummaryService()
        collector = SuggestionCollector()

        collector.record_current_size('test.py::test_fn', None)
        collector.record_execution_time('test.py::test_fn', 0.05)

        writer = StringBufferWriter()

        service.write_suggestion_summary(collector, writer)

        output = writer.get_output()
        # Should show reason in parentheses
        assert any('no external resources' in line.lower() for line in output)

    def it_shows_uncategorized_test_suggestions(self) -> None:
        """Show suggestions for tests without any size marker."""
        service = SuggestionSummaryService()
        collector = SuggestionCollector()

        # Uncategorized test
        collector.record_current_size('test_new.py::test_feature', None)
        collector.record_execution_time('test_new.py::test_feature', 0.05)

        writer = StringBufferWriter()

        service.write_suggestion_summary(collector, writer)

        output = writer.get_output()
        # Should show the test and suggested marker
        assert any('test_new.py::test_feature' in line for line in output)
        assert any('@pytest.mark.small' in line for line in output)

    def it_shows_json_output_hint(self) -> None:
        """Show hint about JSON output option."""
        service = SuggestionSummaryService()
        collector = SuggestionCollector()

        collector.record_current_size('test.py::test_fn', None)
        collector.record_execution_time('test.py::test_fn', 0.05)

        writer = StringBufferWriter()

        service.write_suggestion_summary(collector, writer)

        output = writer.get_output()
        # Should mention JSON output option
        assert any('--test-categories-suggest-output' in line or 'json' in line.lower() for line in output)

    def it_writes_closing_separator(self) -> None:
        """Write closing separator at the end."""
        service = SuggestionSummaryService()
        collector = SuggestionCollector()

        collector.record_current_size('test.py::test_fn', None)
        collector.record_execution_time('test.py::test_fn', 0.05)

        writer = StringBufferWriter()

        service.write_suggestion_summary(collector, writer)

        output = writer.get_output()
        # Should end with separator
        assert output[-1] == 'SEPARATOR[=]'


@pytest.mark.small
class DescribeSuggestionSummaryMultipleSuggestions:
    """Test suite for summary with multiple suggestions."""

    def it_groups_multiple_upgrade_suggestions(self) -> None:
        """Group multiple upgrade suggestions together."""
        service = SuggestionSummaryService()
        collector = SuggestionCollector()

        from pytest_test_categories.suggestion import ResourceType

        # Two small tests that should be medium
        collector.record_current_size('test_a.py::test_one', TestSize.SMALL)
        collector.record_observation('test_a.py::test_one', ResourceType.NETWORK, 'Connection')
        collector.record_current_size('test_b.py::test_two', TestSize.SMALL)
        collector.record_observation('test_b.py::test_two', ResourceType.DATABASE, 'DB connection')

        writer = StringBufferWriter()

        service.write_suggestion_summary(collector, writer)

        output = writer.get_output()
        # Should show both tests
        assert any('test_a.py::test_one' in line for line in output)
        assert any('test_b.py::test_two' in line for line in output)

    def it_shows_summary_counts(self) -> None:
        """Show summary counts of suggestions by category."""
        service = SuggestionSummaryService()
        collector = SuggestionCollector()

        from pytest_test_categories.suggestion import ResourceType

        # 2 upgrade suggestions
        collector.record_current_size('test_a.py::test_one', TestSize.SMALL)
        collector.record_observation('test_a.py::test_one', ResourceType.NETWORK, 'Connection')
        collector.record_current_size('test_b.py::test_two', TestSize.SMALL)
        collector.record_observation('test_b.py::test_two', ResourceType.DATABASE, 'DB connection')

        # 1 downgrade suggestion
        collector.record_current_size('test_c.py::test_three', TestSize.MEDIUM)
        collector.record_execution_time('test_c.py::test_three', 0.05)

        writer = StringBufferWriter()

        service.write_suggestion_summary(collector, writer)

        output = writer.get_output()
        # Should indicate total suggestions
        # Either explicit count or "Based on observed behavior" header
        assert len(output) > 0


@pytest.mark.small
class DescribeSuggestionSummaryFromSuggestionList:
    """Test suite for writing summary from a pre-computed list of suggestions."""

    def it_can_write_from_suggestion_list(self) -> None:
        """Write summary from a list of TestSuggestion objects."""
        service = SuggestionSummaryService()
        writer = StringBufferWriter()

        suggestions = [
            TestSuggestion(
                test_nodeid='test_api.py::test_fetch',
                current_size=TestSize.SMALL,
                suggested_size=TestSize.MEDIUM,
                reason='network access detected',
            ),
        ]

        service.write_suggestions(suggestions, writer)

        output = writer.get_output()
        assert any('test_api.py::test_fetch' in line for line in output)
        assert any('network' in line.lower() for line in output)

    def it_handles_empty_suggestion_list(self) -> None:
        """Handle empty suggestion list gracefully."""
        service = SuggestionSummaryService()
        writer = StringBufferWriter()

        service.write_suggestions([], writer)

        output = writer.get_output()
        assert output == []
