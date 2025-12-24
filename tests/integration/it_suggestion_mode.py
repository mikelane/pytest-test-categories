"""Integration tests for suggestion mode (--test-categories-suggest).

These tests verify the auto-categorization suggestion feature works end-to-end,
from collecting observations during test execution through generating suggestions.

All tests use @pytest.mark.medium since they involve real pytest infrastructure.
"""

from __future__ import annotations

import pytest


@pytest.mark.medium
class DescribeSuggestionMode:
    """Integration tests for --test-categories-suggest option."""

    def it_shows_suggestion_header_when_enabled(self, pytester: pytest.Pytester) -> None:
        """Verify suggestion mode shows header in output."""
        pytester.makepyfile(
            test_example="""
            def test_uncategorized():
                assert True
            """
        )

        result = pytester.runpytest('--test-categories-suggest', '-v')

        result.assert_outcomes(passed=1)
        stdout = result.stdout.str()
        assert 'Test Categorization Suggestions' in stdout

    def it_suggests_small_for_fast_test_without_resources(self, pytester: pytest.Pytester) -> None:
        """Verify uncategorized fast tests are suggested as small."""
        pytester.makepyfile(
            test_example="""
            def test_fast_uncategorized():
                assert 1 + 1 == 2
            """
        )

        result = pytester.runpytest('--test-categories-suggest', '-v')

        result.assert_outcomes(passed=1)
        stdout = result.stdout.str()
        # Should suggest @pytest.mark.small
        assert '@pytest.mark.small' in stdout
        assert 'test_fast_uncategorized' in stdout

    def it_does_not_suggest_for_correctly_categorized_test(self, pytester: pytest.Pytester) -> None:
        """Verify no suggestions for correctly categorized tests."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_correctly_small():
                assert 1 + 1 == 2
            """
        )

        result = pytester.runpytest('--test-categories-suggest', '-v')

        result.assert_outcomes(passed=1)
        stdout = result.stdout.str()
        # Should not show suggestion for correctly categorized test
        assert 'test_correctly_small' not in stdout or 'Suggestions' not in stdout

    def it_can_write_json_output_to_file(self, pytester: pytest.Pytester) -> None:
        """Verify JSON output can be written to a file."""
        pytester.makepyfile(
            test_example="""
            def test_uncategorized():
                assert True
            """
        )

        result = pytester.runpytest(
            '--test-categories-suggest',
            '--test-categories-suggest-output=suggestions.json',
            '-v',
        )

        result.assert_outcomes(passed=1)
        # Verify the JSON file was created
        json_path = pytester.path / 'suggestions.json'
        assert json_path.exists()
        content = json_path.read_text()
        assert 'test_uncategorized' in content

    def it_runs_tests_in_observation_mode_without_blocking(self, pytester: pytest.Pytester) -> None:
        """Verify suggestion mode does not block resources (observation only).

        Note: Resource observation hooks are infrastructure only at this stage.
        The socket usage is not yet detected - tests with resources are currently
        suggested as SMALL (no external resources detected). When resource detection
        is wired up, this test documents the expected non-blocking behavior.
        """
        pytester.makepyfile(
            test_example="""
            import socket

            def test_network_access():
                # This uses network resources but suggestion mode should not block
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.close()
                assert True
            """
        )

        result = pytester.runpytest('--test-categories-suggest', '-v')

        # Test should pass - suggestion mode is non-blocking
        result.assert_outcomes(passed=1)
        stdout = result.stdout.str()
        # Currently suggests SMALL because resource detection is not yet wired up.
        # This test verifies non-blocking behavior; resource detection is future work.
        assert 'test_network_access' in stdout
        assert 'Suggestions' in stdout


@pytest.mark.medium
class DescribeSuggestionModeMultipleTests:
    """Integration tests for suggestion mode with multiple tests."""

    def it_generates_suggestions_for_multiple_tests(self, pytester: pytest.Pytester) -> None:
        """Verify suggestions are generated for multiple uncategorized tests."""
        pytester.makepyfile(
            test_example="""
            def test_one():
                assert True

            def test_two():
                assert True

            def test_three():
                assert True
            """
        )

        result = pytester.runpytest('--test-categories-suggest', '-v')

        result.assert_outcomes(passed=3)
        stdout = result.stdout.str()
        assert 'Suggestions' in stdout

    def it_groups_suggestions_by_category(self, pytester: pytest.Pytester) -> None:
        """Verify suggestions are grouped appropriately."""
        pytester.makepyfile(
            test_example="""
            import pytest

            # Fast uncategorized test - should suggest small
            def test_uncategorized_fast():
                assert True

            # Categorized as small with no issues
            @pytest.mark.small
            def test_correctly_small():
                assert True
            """
        )

        result = pytester.runpytest('--test-categories-suggest', '-v')

        result.assert_outcomes(passed=2)
        stdout = result.stdout.str()
        # Should only suggest for uncategorized
        assert 'Uncategorized' in stdout


@pytest.mark.medium
class DescribeSuggestionModeDisabled:
    """Tests for behavior when suggestion mode is not enabled."""

    def it_does_not_show_suggestions_by_default(self, pytester: pytest.Pytester) -> None:
        """Verify suggestions are not shown without the flag."""
        pytester.makepyfile(
            test_example="""
            def test_uncategorized():
                assert True
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)
        stdout = result.stdout.str()
        assert 'Test Categorization Suggestions' not in stdout
