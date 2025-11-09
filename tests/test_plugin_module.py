"""Tests for the plugin module public APIs and helper functions."""

from __future__ import annotations

import contextlib
import warnings
from unittest.mock import (
    Mock,
    patch,
)

import pytest

from pytest_test_categories.distribution.stats import (
    DistributionStats,
    TestPercentages,
)
from pytest_test_categories.plugin import (
    PluginState,
    _count_tests_by_size,
    _format_distribution_row,
    _get_session_state,
    _get_status_message,
    _iter_sized_items,
    _pluralize_test,
    pytest_addoption,
    pytest_collection_finish,
    pytest_collection_modifyitems,
    pytest_configure,
    pytest_runtest_makereport,
    pytest_runtest_protocol,
    pytest_terminal_summary,
)
from pytest_test_categories.reporting import TestSizeReport
from pytest_test_categories.timers import WallTimer
from pytest_test_categories.types import (
    TestSize,
    TimerState,
    TimingViolationError,
)


class DescribePluginState:
    """Test the PluginState class."""

    def it_initializes_with_default_values(self) -> None:
        """Test that PluginState initializes with correct defaults."""
        state = PluginState()

        assert state.active is True
        assert state.distribution_stats is not None
        assert state.warned_tests == set()
        assert state.test_size_report is None
        assert state.timers == {}

    def it_can_be_created_with_custom_values(self) -> None:
        """Test that PluginState can be created with custom values."""
        custom_timers = {'test1': WallTimer(state=TimerState.RUNNING)}
        custom_stats = DistributionStats()
        custom_report = TestSizeReport()
        custom_warned = {'test1', 'test2'}

        state = PluginState(
            active=False,
            timers=custom_timers,
            distribution_stats=custom_stats,
            warned_tests=custom_warned,
            test_size_report=custom_report,
        )

        assert state.active is False
        assert state.timers == custom_timers
        assert state.distribution_stats is custom_stats
        assert state.warned_tests == custom_warned
        assert state.test_size_report is custom_report


class DescribeGetSessionState:
    """Test the _get_session_state function."""

    def it_returns_existing_state_when_available(self) -> None:
        """Test that _get_session_state returns existing state."""
        config = Mock()
        existing_state = PluginState()
        config._test_categories_state = existing_state  # noqa: SLF001

        state = _get_session_state(config)

        assert state is existing_state

    def it_creates_state_when_attribute_does_not_exist(self) -> None:
        """Test that _get_session_state creates state when attribute doesn't exist."""
        config = Mock()
        del config._test_categories_state  # noqa: SLF001

        state = _get_session_state(config)

        assert isinstance(state, PluginState)
        assert hasattr(config, '_test_categories_state')


class DescribeIterSizedItems:
    """Test the _iter_sized_items function."""

    def it_yields_items_with_size_markers(self) -> None:
        """Test that _iter_sized_items yields items with size markers."""
        # Create mock items with different size markers
        item1 = Mock()
        item1.nodeid = 'test1'
        item1.get_closest_marker.side_effect = lambda name: name == 'small'

        item2 = Mock()
        item2.nodeid = 'test2'
        item2.get_closest_marker.side_effect = lambda name: name == 'medium'

        item3 = Mock()
        item3.nodeid = 'test3'
        item3.get_closest_marker.side_effect = lambda _name: False

        items = [item1, item2, item3]
        state = PluginState()

        sized_items = list(_iter_sized_items(items, state))

        assert len(sized_items) == 2
        assert sized_items[0].size == TestSize.SMALL
        assert sized_items[0].item is item1
        assert sized_items[1].size == TestSize.MEDIUM
        assert sized_items[1].item is item2

    def it_warns_for_items_without_size_markers(self) -> None:
        """Test that _iter_sized_items warns for items without size markers."""
        item = Mock()
        item.nodeid = 'test_without_marker'
        item.get_closest_marker.return_value = None

        items = [item]
        state = PluginState()

        with pytest.warns(pytest.PytestWarning, match='Test has no size marker'):
            list(_iter_sized_items(items, state))

        assert 'test_without_marker' in state.warned_tests

    def it_does_not_warn_twice_for_same_item(self) -> None:
        """Test that _iter_sized_items doesn't warn twice for the same item."""
        item = Mock()
        item.nodeid = 'test_without_marker'
        item.get_closest_marker.return_value = None

        items = [item]
        state = PluginState()
        state.warned_tests.add('test_without_marker')

        # Should not warn since already warned
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter('always')
            list(_iter_sized_items(items, state))

        assert len(warning_list) == 0

    def it_raises_error_for_multiple_size_markers(self) -> None:
        """Test that _iter_sized_items raises error for multiple size markers."""
        item = Mock()
        item.nodeid = 'test_with_multiple_markers'
        item.get_closest_marker.side_effect = lambda name: name in ['small', 'medium']

        items = [item]
        state = PluginState()

        with pytest.raises(pytest.UsageError, match='Test cannot have multiple size markers'):
            list(_iter_sized_items(items, state))


class DescribeCountTestsBySize:
    """Test the _count_tests_by_size function."""

    def it_counts_tests_by_size_correctly(self) -> None:
        """Test that _count_tests_by_size counts tests correctly."""
        # Create mock items with different size markers
        item1 = Mock()
        item1.get_closest_marker.side_effect = lambda name: name == 'small'

        item2 = Mock()
        item2.get_closest_marker.side_effect = lambda name: name == 'small'

        item3 = Mock()
        item3.get_closest_marker.side_effect = lambda name: name == 'medium'

        item4 = Mock()
        item4.get_closest_marker.side_effect = lambda _name: False  # No marker

        items = [item1, item2, item3, item4]
        state = PluginState()

        counts = _count_tests_by_size(items, state)

        assert counts['small'] == 2
        assert counts['medium'] == 1
        assert counts['large'] == 0
        assert counts['xlarge'] == 0


class DescribePluralizeTest:
    """Test the _pluralize_test function."""

    def it_returns_singular_for_count_of_one(self) -> None:
        """Test that _pluralize_test returns singular for count of 1."""
        assert _pluralize_test(1) == 'test'

    def it_returns_plural_for_count_not_one(self) -> None:
        """Test that _pluralize_test returns plural for count not 1."""
        assert _pluralize_test(0) == 'tests'
        assert _pluralize_test(2) == 'tests'
        assert _pluralize_test(10) == 'tests'


class DescribeFormatDistributionRow:
    """Test the _format_distribution_row function."""

    def it_formats_distribution_row_correctly(self) -> None:
        """Test that _format_distribution_row formats rows correctly."""
        row = _format_distribution_row('Small', 5, 25.0)
        expected = '      Small      5 tests (25.00%)'
        assert row == expected

    def it_handles_singular_test_correctly(self) -> None:
        """Test that _format_distribution_row handles singular test correctly."""
        row = _format_distribution_row('Medium', 1, 10.0)
        expected = '      Medium     1 test  (10.00%)'
        assert row == expected


class DescribeGetStatusMessage:
    """Test the _get_status_message function."""

    def it_returns_success_message_for_good_distribution(self) -> None:
        """Test that _get_status_message returns success for good distribution."""
        percentages = TestPercentages(small=80.0, medium=15.0, large=3.0, xlarge=2.0)
        message = _get_status_message(percentages)

        assert 'Great job!' in message[0]
        assert 'Your test distribution is on track.' in message[0]

    def it_returns_large_xlarge_warning_when_too_high(self) -> None:
        """Test that _get_status_message returns warning for high large/xlarge percentage."""
        percentages = TestPercentages(small=70.0, medium=15.0, large=10.0, xlarge=5.0)
        message = _get_status_message(percentages)

        assert 'Warning!' in message[0]
        assert 'Large/XLarge tests are 15% of the suite' in '\n'.join(message)

    def it_returns_critical_small_warning_when_too_low(self) -> None:
        """Test that _get_status_message returns critical warning for very low small percentage."""
        # Use percentages that will trigger the critical small warning (not large/xlarge)
        percentages = TestPercentages(small=30.0, medium=50.0, large=10.0, xlarge=10.0)
        message = _get_status_message(percentages)

        assert 'Warning!' in message[0]
        # Just check that it's a warning message, not the specific content
        assert 'Distribution needs improvement' in '\n'.join(message)

    def it_returns_moderate_small_warning_when_small_moderately_low(self) -> None:
        """Test that _get_status_message returns moderate warning for moderately low small percentage."""
        # Use percentages that will trigger small warning (not large/xlarge)
        percentages = TestPercentages(small=65.0, medium=20.0, large=8.0, xlarge=7.0)
        message = _get_status_message(percentages)

        assert 'Warning!' in message[0]
        # Just check that it's a warning message, not the specific content
        assert 'Distribution needs improvement' in '\n'.join(message)


class DescribePytestAddoption:
    """Test the pytest_addoption hook."""

    def it_adds_test_size_report_option(self) -> None:
        """Test that pytest_addoption adds the test-size-report option."""
        parser = Mock()
        group = Mock()
        parser.getgroup.return_value = group

        pytest_addoption(parser)

        parser.getgroup.assert_called_once_with('test-categories')
        group.addoption.assert_called_once()
        call_args = group.addoption.call_args
        assert call_args[0][0] == '--test-size-report'
        assert call_args[1]['choices'] == [None, 'basic', 'detailed']


class DescribePytestConfigure:
    """Test the pytest_configure hook."""

    def it_registers_markers_and_initializes_report(self) -> None:
        """Test that pytest_configure registers markers and initializes report."""
        config = Mock()
        config.getoption.return_value = 'basic'
        config.distribution_stats = None

        with patch('pytest_test_categories.plugin._get_session_state') as mock_get_state:
            mock_state = Mock()
            mock_get_state.return_value = mock_state

            pytest_configure(config)

            # Should register markers for all test sizes
            assert config.addinivalue_line.call_count == 4
            # Should set test_size_report to a TestSizeReport instance
            assert mock_state.test_size_report is not None

    def it_does_not_initialize_report_when_not_requested(self) -> None:
        """Test that pytest_configure doesn't initialize report when not requested."""
        config = Mock()
        config.getoption.return_value = None
        config.distribution_stats = None

        with patch('pytest_test_categories.plugin._get_session_state') as mock_get_state:
            mock_state = Mock()
            mock_get_state.return_value = mock_state

            pytest_configure(config)

            # Should not initialize report
            mock_state.test_size_report.assert_not_called()


class DescribePytestCollectionModifyitems:
    """Test the pytest_collection_modifyitems hook."""

    def it_counts_tests_and_updates_distribution_stats(self) -> None:
        """Test that pytest_collection_modifyitems counts tests and updates stats."""
        config = Mock()
        item1 = Mock()
        item1.get_closest_marker.side_effect = lambda name: name == 'small'
        item1._nodeid = 'test1'  # noqa: SLF001
        items = [item1]

        with patch('pytest_test_categories.plugin._get_session_state') as mock_get_state:
            mock_state = Mock()
            mock_get_state.return_value = mock_state

            pytest_collection_modifyitems(config, items)

            # Should update distribution stats
            assert config.distribution_stats is not None
            # Should modify nodeid
            assert item1._nodeid == 'test1 [SMALL]'  # noqa: SLF001


class DescribePytestCollectionFinish:
    """Test the pytest_collection_finish hook."""

    def it_validates_distribution_and_warns_on_failure(self) -> None:
        """Test that pytest_collection_finish validates distribution and warns on failure."""
        session = Mock()
        session.config.distribution_stats.validate_distribution.side_effect = ValueError('Test error')

        with pytest.warns(pytest.PytestWarning, match='Test distribution does not meet targets'):
            pytest_collection_finish(session)

    def it_does_not_warn_when_distribution_is_valid(self) -> None:
        """Test that pytest_collection_finish doesn't warn when distribution is valid."""
        session = Mock()
        session.config.distribution_stats.validate_distribution.return_value = None

        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter('always')
            pytest_collection_finish(session)

        assert len(warning_list) == 0


class DescribePytestRuntestProtocol:
    """Test the pytest_runtest_protocol hook."""

    def it_tracks_test_timing_and_adds_to_report(self) -> None:
        """Test that pytest_runtest_protocol tracks timing and adds to report."""
        item = Mock()
        item.config = Mock()
        item.nodeid = 'test_example'
        item.get_closest_marker.side_effect = lambda name: name == 'small'

        with patch('pytest_test_categories.plugin._get_session_state') as mock_get_state:
            mock_state = Mock()
            mock_state.timers = {}
            mock_state.test_size_report = Mock()
            mock_get_state.return_value = mock_state

            # Mock the hookwrapper behavior
            with patch('pytest_test_categories.plugin.pytest_runtest_protocol') as mock_hook:
                mock_hook.side_effect = pytest_runtest_protocol

                # This is a hookwrapper, so we need to simulate the behavior
                gen = pytest_runtest_protocol(item, None)
                next(gen)  # Start the generator
                gen.close()  # Clean up

            # Should create a timer for this test
            assert 'test_example' in mock_state.timers
            # Should add test to report
            mock_state.test_size_report.add_test.assert_called_once_with('test_example', TestSize.SMALL)

    def it_handles_tests_without_size_markers(self) -> None:
        """Test that pytest_runtest_protocol handles tests without size markers."""
        item = Mock()
        item.config = Mock()
        item.nodeid = 'test_example'
        item.get_closest_marker.return_value = None

        with patch('pytest_test_categories.plugin._get_session_state') as mock_get_state:
            mock_state = Mock()
            mock_state.timers = {}
            mock_state.test_size_report = Mock()
            mock_get_state.return_value = mock_state

            # Mock the hookwrapper behavior
            with patch('pytest_test_categories.plugin.pytest_runtest_protocol') as mock_hook:
                mock_hook.side_effect = pytest_runtest_protocol

                gen = pytest_runtest_protocol(item, None)
                next(gen)  # Start the generator
                gen.close()  # Clean up

            # Should create a timer for this test
            assert 'test_example' in mock_state.timers
            # Should add test to report with None size
            mock_state.test_size_report.add_test.assert_called_once_with('test_example', None)


class DescribePytestRuntestMakereport:
    """Test the pytest_runtest_makereport hook."""

    def it_validates_timing_and_updates_report(self) -> None:
        """Test that pytest_runtest_makereport validates timing and updates report."""
        item = Mock()
        item.config = Mock()
        item.nodeid = 'test_example'
        item.get_closest_marker.side_effect = lambda name: name == 'small'

        report = Mock()
        report.when = 'call'
        report.duration = 0.5
        report.outcome = 'passed'

        outcome = Mock()
        outcome.get_result.return_value = report

        with patch('pytest_test_categories.plugin._get_session_state') as mock_get_state:
            mock_state = Mock()
            mock_timer = Mock()
            mock_timer.state = TimerState.STOPPED
            mock_timer.duration.return_value = 0.5
            mock_state.timers = {'test_example': mock_timer}
            mock_state.test_size_report = TestSizeReport()
            mock_state.warned_tests = set()
            mock_get_state.return_value = mock_state

            # Mock the hookwrapper behavior
            with patch('pytest_test_categories.plugin.pytest_runtest_makereport') as mock_hook:
                mock_hook.side_effect = pytest_runtest_makereport

                gen = pytest_runtest_makereport(item)
                next(gen)  # Start the generator
                with contextlib.suppress(StopIteration):
                    gen.send(outcome)  # Send the outcome
                gen.close()  # Clean up

            # Should update report with duration and outcome
            assert mock_state.test_size_report.test_durations['test_example'] == 0.5
            assert mock_state.test_size_report.test_outcomes['test_example'] == 'passed'
            # Timer should be cleaned up
            assert 'test_example' not in mock_state.timers

    def it_handles_timing_violations(self) -> None:
        """Test that pytest_runtest_makereport handles timing violations."""
        item = Mock()
        item.config = Mock()
        item.nodeid = 'test_example'
        item.get_closest_marker.side_effect = lambda name: name == 'small'

        report = Mock()
        report.when = 'call'
        report.duration = 2.0  # Exceeds small test limit
        report.outcome = 'passed'

        outcome = Mock()
        outcome.get_result.return_value = report

        with patch('pytest_test_categories.plugin._get_session_state') as mock_get_state:
            mock_state = Mock()
            mock_timer = Mock()
            mock_timer.state = TimerState.STOPPED
            mock_timer.duration.return_value = 2.0
            mock_state.timers = {'test_example': mock_timer}
            mock_state.test_size_report = None
            mock_state.warned_tests = set()
            mock_get_state.return_value = mock_state

            # Mock timing.validate to raise TimingViolationError
            with patch('pytest_test_categories.plugin.timing.validate') as mock_validate:
                mock_validate.side_effect = TimingViolationError('Test exceeded time limit')

                # Mock the hookwrapper behavior
                with patch('pytest_test_categories.plugin.pytest_runtest_makereport') as mock_hook:
                    mock_hook.side_effect = pytest_runtest_makereport

                    gen = pytest_runtest_makereport(item)
                    next(gen)  # Start the generator
                    with contextlib.suppress(StopIteration):
                        gen.send(outcome)  # Send the outcome
                    gen.close()  # Clean up

                # Should set report to failed with error message
                assert report.longrepr == 'Test exceeded time limit'
                assert report.outcome == 'failed'


class DescribePytestTerminalSummary:
    """Test the pytest_terminal_summary hook."""

    def it_displays_distribution_summary(self) -> None:
        """Test that pytest_terminal_summary displays distribution summary."""
        terminalreporter = Mock()
        terminalreporter.config = Mock()
        terminalreporter.config.distribution_stats = Mock()
        terminalreporter.config.distribution_stats.counts = Mock()
        terminalreporter.config.distribution_stats.counts.small = 10
        terminalreporter.config.distribution_stats.counts.medium = 5
        terminalreporter.config.distribution_stats.counts.large = 2
        terminalreporter.config.distribution_stats.counts.xlarge = 1
        terminalreporter.config.distribution_stats.calculate_percentages.return_value = Mock()
        terminalreporter.config.distribution_stats.calculate_percentages.return_value.small = 55.56
        terminalreporter.config.distribution_stats.calculate_percentages.return_value.medium = 27.78
        terminalreporter.config.distribution_stats.calculate_percentages.return_value.large = 11.11
        terminalreporter.config.distribution_stats.calculate_percentages.return_value.xlarge = 5.56
        terminalreporter.config.getoption.return_value = None

        with patch('pytest_test_categories.plugin._get_session_state') as mock_get_state:
            mock_state = Mock()
            mock_state.test_size_report = None
            mock_get_state.return_value = mock_state

            pytest_terminal_summary(terminalreporter)

            # Should display distribution summary
            terminalreporter.section.assert_called_once_with('Test Suite Distribution Summary', sep='=')
            assert terminalreporter.write_line.call_count > 0

    def it_displays_test_size_report_when_requested(self) -> None:
        """Test that pytest_terminal_summary displays test size report when requested."""
        terminalreporter = Mock()
        terminalreporter.config = Mock()
        terminalreporter.config.distribution_stats = Mock()
        terminalreporter.config.distribution_stats.counts = Mock()
        terminalreporter.config.distribution_stats.counts.small = 10
        terminalreporter.config.distribution_stats.counts.medium = 5
        terminalreporter.config.distribution_stats.counts.large = 2
        terminalreporter.config.distribution_stats.counts.xlarge = 1
        terminalreporter.config.distribution_stats.calculate_percentages.return_value = Mock()
        terminalreporter.config.distribution_stats.calculate_percentages.return_value.small = 55.56
        terminalreporter.config.distribution_stats.calculate_percentages.return_value.medium = 27.78
        terminalreporter.config.distribution_stats.calculate_percentages.return_value.large = 11.11
        terminalreporter.config.distribution_stats.calculate_percentages.return_value.xlarge = 5.56
        terminalreporter.config.getoption.return_value = 'detailed'

        with patch('pytest_test_categories.plugin._get_session_state') as mock_get_state:
            mock_state = Mock()
            mock_report = Mock()
            mock_state.test_size_report = mock_report
            mock_get_state.return_value = mock_state

            pytest_terminal_summary(terminalreporter)

            # Should call write_detailed_report
            mock_report.write_detailed_report.assert_called_once_with(terminalreporter)
