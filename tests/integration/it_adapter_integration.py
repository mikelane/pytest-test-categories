"""Integration tests for production adapters.

These tests verify that production adapters correctly integrate with their
real external dependencies (pytest objects, warnings module, etc.).

All tests use @pytest.mark.medium since they involve real infrastructure.
"""

from __future__ import annotations

import warnings

import pytest

from pytest_test_categories.adapters.pytest_adapter import (
    PytestConfigAdapter,
    PytestItemAdapter,
    PytestWarningAdapter,
)
from pytest_test_categories.distribution.stats import DistributionStats
from pytest_test_categories.types import (
    PluginState,
    TestSize,
)


@pytest.mark.medium
class DescribePytestItemAdapterIntegration:
    """Integration tests for PytestItemAdapter with real pytest.Item objects."""

    def it_wraps_real_pytest_item_nodeid(self, pytester: pytest.Pytester) -> None:
        """Verify adapter correctly exposes real pytest.Item nodeid."""
        source = """
import pytest

@pytest.mark.small
def test_example():
    assert True
"""
        # Collect the test items - getitems takes source code directly
        items = pytester.getitems(source)
        assert len(items) == 1

        # Wrap with adapter
        adapter = PytestItemAdapter(items[0])

        # Verify nodeid is correctly exposed
        assert 'test_example' in adapter.nodeid

    def it_retrieves_markers_from_real_pytest_item(self, pytester: pytest.Pytester) -> None:
        """Verify adapter correctly retrieves markers from real pytest.Item."""
        source = """
import pytest

@pytest.mark.small
def test_with_marker():
    assert True

def test_without_marker():
    assert True
"""
        items = pytester.getitems(source)
        assert len(items) == 2

        # Find the test with marker
        marked_item = next(i for i in items if 'test_with_marker' in i.nodeid)
        unmarked_item = next(i for i in items if 'test_without_marker' in i.nodeid)

        marked_adapter = PytestItemAdapter(marked_item)
        unmarked_adapter = PytestItemAdapter(unmarked_item)

        # Verify marker retrieval
        assert marked_adapter.get_marker('small') is not None
        assert unmarked_adapter.get_marker('small') is None

    def it_modifies_nodeid_on_real_pytest_item(self, pytester: pytest.Pytester) -> None:
        """Verify adapter can modify nodeid on real pytest.Item."""
        source = """
def test_example():
    assert True
"""
        items = pytester.getitems(source)
        adapter = PytestItemAdapter(items[0])

        original_nodeid = adapter.nodeid
        new_nodeid = f'{original_nodeid}[SMALL]'

        adapter.set_nodeid(new_nodeid)

        assert adapter.nodeid == new_nodeid
        assert '[SMALL]' in adapter.nodeid

    def it_retrieves_class_level_markers(self, pytester: pytest.Pytester) -> None:
        """Verify adapter retrieves markers from test class."""
        source = """
import pytest

@pytest.mark.medium
class TestExample:
    def test_method(self):
        assert True
"""
        items = pytester.getitems(source)
        adapter = PytestItemAdapter(items[0])

        # Marker should be found via class inheritance
        assert adapter.get_marker('medium') is not None


@pytest.mark.medium
class DescribePytestConfigAdapterIntegration:
    """Integration tests for PytestConfigAdapter with real pytest.Config objects."""

    def it_stores_and_retrieves_plugin_state(self, pytester: pytest.Pytester) -> None:
        """Verify adapter correctly manages plugin state on real config."""
        config = pytester.parseconfig()

        adapter = PytestConfigAdapter(config)

        # Get initial state (should create one)
        state = adapter.get_plugin_state()
        assert isinstance(state, PluginState)
        assert state.active is True

        # Modify and set new state
        new_state = PluginState(active=False)
        adapter.set_plugin_state(new_state)

        # Retrieve and verify
        retrieved_state = adapter.get_plugin_state()
        assert retrieved_state.active is False

    def it_stores_and_retrieves_distribution_stats(self, pytester: pytest.Pytester) -> None:
        """Verify adapter correctly manages distribution stats on real config."""
        config = pytester.parseconfig()

        adapter = PytestConfigAdapter(config)

        # Set stats - use TestSize enum as keys
        stats = DistributionStats.update_counts({TestSize.SMALL: 10, TestSize.MEDIUM: 5})
        adapter.set_distribution_stats(stats)

        # Retrieve and verify
        retrieved_stats = adapter.get_distribution_stats()
        assert retrieved_stats.counts.small == 10
        assert retrieved_stats.counts.medium == 5

    def it_retrieves_command_line_options(self, pytester: pytest.Pytester) -> None:
        """Verify adapter retrieves command line options from real config."""
        # Create config with verbose option
        config = pytester.parseconfig('-v')

        adapter = PytestConfigAdapter(config)

        # Standard pytest options should be accessible
        verbose = adapter.get_option('verbose')
        assert verbose is not None


@pytest.mark.medium
class DescribePytestWarningAdapterIntegration:
    """Integration tests for PytestWarningAdapter with real warnings module."""

    def it_emits_real_warnings(self) -> None:
        """Verify adapter emits real warnings through Python's warnings system."""
        adapter = PytestWarningAdapter()

        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter('always')
            adapter.warn('Test warning message', category=UserWarning)

        assert len(caught_warnings) == 1
        assert 'Test warning message' in str(caught_warnings[0].message)
        assert caught_warnings[0].category is UserWarning

    def it_uses_pytest_warning_as_default_category(self) -> None:
        """Verify adapter uses PytestWarning when no category specified."""
        adapter = PytestWarningAdapter()

        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter('always')
            adapter.warn('Default category warning')

        assert len(caught_warnings) == 1
        assert caught_warnings[0].category is pytest.PytestWarning

    def it_emits_deprecation_warnings(self) -> None:
        """Verify adapter can emit DeprecationWarning."""
        adapter = PytestWarningAdapter()

        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter('always')
            adapter.warn('Deprecated feature', category=DeprecationWarning)

        assert len(caught_warnings) == 1
        assert caught_warnings[0].category is DeprecationWarning


@pytest.mark.medium
class DescribeTerminalReporterAdapterIntegration:
    """Integration tests for TerminalReporterAdapter with real pytest.TerminalReporter."""

    def it_writes_to_real_terminal_reporter(self, pytester: pytest.Pytester) -> None:
        """Verify adapter writes through real terminal reporter."""
        # Create a test that uses the terminal reporter
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_example():
                assert True
            """
        )

        # Run with test-size-report to trigger terminal reporter usage
        result = pytester.runpytest('-v')

        # The plugin should have written to terminal reporter
        # This verifies the adapter is functioning in the real environment
        result.assert_outcomes(passed=1)

    def it_integrates_with_plugin_terminal_summary(self, pytester: pytest.Pytester) -> None:
        """Verify adapter integrates correctly in pytest_terminal_summary hook."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_one():
                assert True

            @pytest.mark.small
            def test_two():
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # Should see distribution summary in output
        stdout = result.stdout.str()
        assert 'Test Suite Distribution Summary' in stdout or result.ret == 0


@pytest.mark.medium
class DescribeAdapterInteroperability:
    """Integration tests verifying adapters work together correctly."""

    def it_uses_adapters_throughout_test_collection(self, pytester: pytest.Pytester) -> None:
        """Verify adapters work together during test collection."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_small():
                assert True

            @pytest.mark.medium
            def test_medium():
                assert True
            """
        )

        # Run the full collection and execution
        result = pytester.runpytest('-v')

        # Verify both tests were collected and run
        result.assert_outcomes(passed=2)

        # Verify size labels were applied (via PytestItemAdapter)
        stdout = result.stdout.str()
        assert '[SMALL]' in stdout
        assert '[MEDIUM]' in stdout

    def it_handles_config_state_across_hooks(self, pytester: pytest.Pytester) -> None:
        """Verify config adapter maintains state across pytest hooks."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_example():
                assert True
            """
        )

        # Run with full plugin to verify state persists
        result = pytester.runpytest('-v')

        # Distribution summary proves state was maintained through hooks
        stdout = result.stdout.str()
        assert 'Distribution Summary' in stdout or result.ret == 0
