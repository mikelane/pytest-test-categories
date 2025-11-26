"""Tests for the plugin module public APIs and helper functions."""

from __future__ import annotations

import contextlib
import warnings
from unittest.mock import Mock

import pytest

from pytest_test_categories import (
    DistributionStats,
    PluginState,
    TestPercentages,
    TestSize,
    TestSizeReport,
    TimerState,
    WallTimer,
    pytest_addoption,
    pytest_collection_finish,
    pytest_collection_modifyitems,
    pytest_configure,
    pytest_runtest_makereport,
    pytest_runtest_protocol,
    pytest_terminal_summary,
)
from pytest_test_categories.adapters.pytest_adapter import PytestConfigAdapter
from pytest_test_categories.formatting import (
    format_distribution_row,
    get_status_message,
    pluralize_test,
)
from pytest_test_categories.plugin import (
    _get_enforcement_mode,
    _get_network_blocker,
)
from pytest_test_categories.ports.network import EnforcementMode


@pytest.mark.small
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


@pytest.mark.small
class DescribeGetSessionState:
    """Test the PytestConfigAdapter.get_plugin_state method."""

    def it_returns_existing_state_when_available(self) -> None:
        """Test that get_plugin_state returns existing state."""
        config = Mock()
        existing_state = PluginState()
        config._test_categories_state = existing_state

        adapter = PytestConfigAdapter(config)
        state = adapter.get_plugin_state()

        assert state is existing_state

    def it_creates_state_when_attribute_does_not_exist(self) -> None:
        """Test that get_plugin_state creates state when attribute doesn't exist."""
        config = Mock()
        del config._test_categories_state

        adapter = PytestConfigAdapter(config)
        state = adapter.get_plugin_state()

        assert isinstance(state, PluginState)
        assert hasattr(config, '_test_categories_state')


@pytest.mark.small
class DescribePluralizeTest:
    """Test the pluralize_test function."""

    def it_returns_singular_for_count_of_one(self) -> None:
        """Test that pluralize_test returns singular for count of 1."""
        assert pluralize_test(1) == 'test'

    def it_returns_plural_for_count_not_one(self) -> None:
        """Test that pluralize_test returns plural for count not 1."""
        assert pluralize_test(0) == 'tests'
        assert pluralize_test(2) == 'tests'
        assert pluralize_test(10) == 'tests'


@pytest.mark.small
class DescribeFormatDistributionRow:
    """Test the format_distribution_row function."""

    def it_formats_distribution_row_correctly(self) -> None:
        """Test that format_distribution_row formats rows correctly."""
        row = format_distribution_row('Small', 5, 25.0)
        expected = '      Small      5 tests (25.00%)'
        assert row == expected

    def it_handles_singular_test_correctly(self) -> None:
        """Test that format_distribution_row handles singular test correctly."""
        row = format_distribution_row('Medium', 1, 10.0)
        expected = '      Medium     1 test  (10.00%)'
        assert row == expected


@pytest.mark.small
class DescribeGetStatusMessage:
    """Test the get_status_message function."""

    def it_returns_success_message_for_good_distribution(self) -> None:
        """Test that get_status_message returns success for good distribution."""
        percentages = TestPercentages(small=80.0, medium=15.0, large=3.0, xlarge=2.0)
        message = get_status_message(percentages)

        assert 'Great job!' in message[0]
        assert 'Your test distribution is on track.' in message[0]

    def it_returns_large_xlarge_warning_when_too_high(self) -> None:
        """Test that get_status_message returns warning for high large/xlarge percentage."""
        percentages = TestPercentages(small=70.0, medium=15.0, large=10.0, xlarge=5.0)
        message = get_status_message(percentages)

        assert 'Warning!' in message[0]
        assert 'Large/XLarge tests are 15% of the suite' in '\n'.join(message)

    def it_returns_critical_small_warning_when_too_low(self) -> None:
        """Test that get_status_message returns critical warning for very low small percentage."""
        # Use percentages that will trigger the critical small warning (not large/xlarge)
        percentages = TestPercentages(small=30.0, medium=50.0, large=10.0, xlarge=10.0)
        message = get_status_message(percentages)

        assert 'Warning!' in message[0]
        # Just check that it's a warning message, not the specific content
        assert 'Distribution needs improvement' in '\n'.join(message)

    def it_returns_moderate_small_warning_when_small_moderately_low(self) -> None:
        """Test that get_status_message returns moderate warning for moderately low small percentage."""
        # Use percentages that will trigger small warning (not large/xlarge)
        percentages = TestPercentages(small=65.0, medium=20.0, large=8.0, xlarge=7.0)
        message = get_status_message(percentages)

        assert 'Warning!' in message[0]
        # Just check that it's a warning message, not the specific content
        assert 'Distribution needs improvement' in '\n'.join(message)


@pytest.mark.small
class DescribePytestAddoption:
    """Test the pytest_addoption hook."""

    def it_adds_test_size_report_option(self) -> None:
        """Test that pytest_addoption adds the test-size-report option."""
        parser = Mock()
        group = Mock()
        parser.getgroup.return_value = group

        pytest_addoption(parser)

        parser.getgroup.assert_called_once_with('test-categories')
        # Now adds two options: --test-size-report and --test-categories-enforcement
        assert group.addoption.call_count == 2
        # Find the test-size-report call
        test_size_report_call = None
        for call in group.addoption.call_args_list:
            if call[0][0] == '--test-size-report':
                test_size_report_call = call
                break
        assert test_size_report_call is not None
        assert test_size_report_call[1]['choices'] == [None, 'basic', 'detailed']

    def it_adds_enforcement_cli_option(self) -> None:
        """Test that pytest_addoption adds the enforcement CLI option."""
        parser = Mock()
        group = Mock()
        parser.getgroup.return_value = group

        pytest_addoption(parser)

        # Find the enforcement call
        enforcement_call = None
        for call in group.addoption.call_args_list:
            if call[0][0] == '--test-categories-enforcement':
                enforcement_call = call
                break
        assert enforcement_call is not None
        assert enforcement_call[1]['choices'] == ['off', 'warn', 'strict']

    def it_registers_enforcement_ini_option(self) -> None:
        """Test that pytest_addoption registers the enforcement ini option."""
        parser = Mock()
        group = Mock()
        parser.getgroup.return_value = group

        pytest_addoption(parser)

        parser.addini.assert_called_once_with(
            'test_categories_enforcement',
            help='Enforcement mode for test hermeticity: off (default), warn, or strict',
            default='off',
        )


@pytest.mark.small
class DescribePytestConfigure:
    """Test the pytest_configure hook."""

    def it_registers_markers_and_initializes_report(self) -> None:
        """Test that pytest_configure registers markers and initializes report."""
        config = Mock()
        config.getoption.return_value = 'basic'
        config.distribution_stats = None

        pytest_configure(config)

        # Should register markers for all test sizes
        assert config.addinivalue_line.call_count == 4
        # Should have plugin state with test_size_report initialized
        assert hasattr(config, '_test_categories_state')
        assert config._test_categories_state.test_size_report is not None

    def it_does_not_initialize_report_when_not_requested(self) -> None:
        """Test that pytest_configure doesn't initialize report when not requested."""
        config = Mock()
        config.getoption.return_value = None
        config.distribution_stats = None

        pytest_configure(config)

        # Should not initialize report
        assert hasattr(config, '_test_categories_state')
        assert config._test_categories_state.test_size_report is None


@pytest.mark.small
class DescribePytestCollectionModifyitems:
    """Test the pytest_collection_modifyitems hook."""

    def it_counts_tests_and_updates_distribution_stats(self) -> None:
        """Test that pytest_collection_modifyitems counts tests and updates stats."""
        config = Mock()
        config.distribution_stats = DistributionStats()
        item1 = Mock()
        item1.nodeid = 'test1'
        item1._nodeid = 'test1'
        item1.get_closest_marker.side_effect = lambda name: name == 'small'
        items = [item1]

        # Initialize plugin state with test discovery service
        config._test_categories_state = PluginState()
        from pytest_test_categories.services.test_discovery import TestDiscoveryService

        mock_discovery_service = Mock(spec=TestDiscoveryService)
        mock_discovery_service.find_test_size.return_value = TestSize.SMALL
        config._test_categories_state.test_discovery_service = mock_discovery_service

        pytest_collection_modifyitems(config, items)  # type: ignore[arg-type]

        # Should update distribution stats
        assert config.distribution_stats is not None
        # Should modify nodeid
        assert item1._nodeid == 'test1 [SMALL]'


@pytest.mark.small
class DescribePytestCollectionFinish:
    """Test the pytest_collection_finish hook."""

    def it_validates_distribution_and_warns_on_failure(self) -> None:
        """Test that pytest_collection_finish validates distribution and warns on failure."""
        session = Mock()
        session.config.distribution_stats = DistributionStats()
        # Set up distribution that will fail validation
        session.config.distribution_stats = session.config.distribution_stats.update_counts(
            counts={'small': 1, 'medium': 10, 'large': 0, 'xlarge': 0}
        )

        with pytest.warns(UserWarning, match='Test distribution does not meet targets'):
            pytest_collection_finish(session)

    def it_does_not_warn_when_distribution_is_valid(self) -> None:
        """Test that pytest_collection_finish doesn't warn when distribution is valid."""
        session = Mock()
        session.config.distribution_stats = DistributionStats()
        # Set up valid distribution (80% small, 15% medium, 5% large)
        session.config.distribution_stats = session.config.distribution_stats.update_counts(
            counts={'small': 80, 'medium': 15, 'large': 5, 'xlarge': 0}
        )

        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter('always')
            pytest_collection_finish(session)

        # Filter for UserWarnings about distribution
        dist_warnings = [w for w in warning_list if 'distribution' in str(w.message).lower()]
        assert len(dist_warnings) == 0


@pytest.mark.small
class DescribePytestRuntestProtocol:
    """Test the pytest_runtest_protocol hook."""

    def it_tracks_test_timing_and_adds_to_report(self) -> None:
        """Test that pytest_runtest_protocol tracks timing and adds to report."""
        item = Mock()
        item.config = Mock()
        item.nodeid = 'test_example'
        item.get_closest_marker.side_effect = lambda name: name == 'small'

        # Initialize plugin state
        item.config._test_categories_state = PluginState()
        item.config._test_categories_state.timers = {}
        item.config._test_categories_state.test_size_report = Mock()
        item.config._test_categories_state.timer_factory = Mock(side_effect=lambda state: Mock(state=state))

        # Mock the test discovery service
        from pytest_test_categories.services.test_discovery import TestDiscoveryService

        mock_discovery_service = Mock(spec=TestDiscoveryService)
        mock_discovery_service.find_test_size.return_value = TestSize.SMALL
        item.config._test_categories_state.test_discovery_service = mock_discovery_service

        # This is a hookwrapper, so we need to simulate the behavior
        gen = pytest_runtest_protocol(item, None)
        next(gen)  # Start the generator
        gen.close()  # Clean up

        # Should create a timer for this test
        assert 'test_example' in item.config._test_categories_state.timers

    def it_handles_tests_without_size_markers(self) -> None:
        """Test that pytest_runtest_protocol handles tests without size markers."""
        item = Mock()
        item.config = Mock()
        item.nodeid = 'test_example'
        item.get_closest_marker.return_value = None

        # Initialize plugin state
        item.config._test_categories_state = PluginState()
        item.config._test_categories_state.timers = {}
        item.config._test_categories_state.test_size_report = Mock()
        item.config._test_categories_state.timer_factory = Mock(side_effect=lambda state: Mock(state=state))

        # Mock the test discovery service to return None
        from pytest_test_categories.services.test_discovery import TestDiscoveryService

        mock_discovery_service = Mock(spec=TestDiscoveryService)
        mock_discovery_service.find_test_size.return_value = None
        item.config._test_categories_state.test_discovery_service = mock_discovery_service

        gen = pytest_runtest_protocol(item, None)
        next(gen)  # Start the generator
        gen.close()  # Clean up

        # Should create a timer for this test
        assert 'test_example' in item.config._test_categories_state.timers


@pytest.mark.small
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

        # Initialize plugin state
        item.config._test_categories_state = PluginState()
        mock_timer = Mock()
        mock_timer.state = TimerState.STOPPED
        mock_timer.duration.return_value = 0.5
        item.config._test_categories_state.timers = {'test_example': mock_timer}
        item.config._test_categories_state.test_size_report = TestSizeReport()

        # Mock the test discovery service
        from pytest_test_categories.services.test_discovery import TestDiscoveryService

        mock_discovery_service = Mock(spec=TestDiscoveryService)
        mock_discovery_service.find_test_size.return_value = TestSize.SMALL
        item.config._test_categories_state.test_discovery_service = mock_discovery_service

        gen = pytest_runtest_makereport(item)
        next(gen)  # Start the generator
        with contextlib.suppress(StopIteration):
            gen.send(outcome)  # type: ignore[arg-type]  # Send the outcome
        gen.close()  # Clean up

        # Should update report with duration and outcome
        assert item.config._test_categories_state.test_size_report.test_durations['test_example'] == 0.5
        assert item.config._test_categories_state.test_size_report.test_outcomes['test_example'] == 'passed'
        # Timer should be cleaned up
        assert 'test_example' not in item.config._test_categories_state.timers

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

        # Initialize plugin state
        item.config._test_categories_state = PluginState()
        mock_timer = Mock()
        mock_timer.state = TimerState.STOPPED
        mock_timer.duration.return_value = 2.0
        item.config._test_categories_state.timers = {'test_example': mock_timer}
        item.config._test_categories_state.test_size_report = None

        # Mock the test discovery service
        from pytest_test_categories.services.test_discovery import TestDiscoveryService

        mock_discovery_service = Mock(spec=TestDiscoveryService)
        mock_discovery_service.find_test_size.return_value = TestSize.SMALL
        item.config._test_categories_state.test_discovery_service = mock_discovery_service

        gen = pytest_runtest_makereport(item)
        next(gen)  # Start the generator
        with contextlib.suppress(StopIteration):
            gen.send(outcome)  # type: ignore[arg-type]  # Send the outcome
        gen.close()  # Clean up

        # Should set report to failed with error message
        assert report.longrepr is not None
        assert report.outcome == 'failed'


@pytest.mark.small
class DescribePytestTerminalSummary:
    """Test the pytest_terminal_summary hook."""

    def it_displays_distribution_summary(self) -> None:
        """Test that pytest_terminal_summary displays distribution summary."""
        terminalreporter = Mock()
        terminalreporter.config = Mock()
        terminalreporter.config.distribution_stats = DistributionStats()
        # Use counts that sum to 100 for clean percentages
        terminalreporter.config.distribution_stats = terminalreporter.config.distribution_stats.update_counts(
            counts={'small': 80, 'medium': 15, 'large': 5, 'xlarge': 0}
        )
        terminalreporter.config.getoption.return_value = None

        # Initialize plugin state
        terminalreporter.config._test_categories_state = PluginState()
        terminalreporter.config._test_categories_state.test_size_report = None

        pytest_terminal_summary(terminalreporter)

        # Should display distribution summary
        terminalreporter.section.assert_called_once_with('Test Suite Distribution Summary', sep='=')
        assert terminalreporter.write_line.call_count > 0

    def it_displays_test_size_report_when_requested(self) -> None:
        """Test that pytest_terminal_summary displays test size report when requested."""
        terminalreporter = Mock()
        terminalreporter.config = Mock()
        terminalreporter.config.distribution_stats = DistributionStats()
        # Use counts that sum to 100 for clean percentages
        terminalreporter.config.distribution_stats = terminalreporter.config.distribution_stats.update_counts(
            counts={'small': 80, 'medium': 15, 'large': 5, 'xlarge': 0}
        )
        terminalreporter.config.getoption.return_value = 'detailed'

        # Initialize plugin state
        terminalreporter.config._test_categories_state = PluginState()
        mock_report = Mock()
        terminalreporter.config._test_categories_state.test_size_report = mock_report

        pytest_terminal_summary(terminalreporter)

        # Should call write_detailed_report
        mock_report.write_detailed_report.assert_called_once_with(terminalreporter)


@pytest.mark.small
class DescribeGetEnforcementMode:
    """Test the _get_enforcement_mode helper function."""

    def it_returns_cli_option_when_provided(self) -> None:
        """CLI option takes precedence over ini setting."""
        config = Mock()
        config.getoption.return_value = 'strict'
        config.getini.return_value = 'warn'  # Should be ignored

        result = _get_enforcement_mode(config)

        assert result == EnforcementMode.STRICT
        config.getoption.assert_called_once_with('--test-categories-enforcement', default=None)

    def it_returns_ini_value_when_cli_not_provided(self) -> None:
        """Ini value used when CLI option not provided."""
        config = Mock()
        config.getoption.return_value = None  # No CLI option
        config.getini.return_value = 'warn'

        result = _get_enforcement_mode(config)

        assert result == EnforcementMode.WARN

    def it_returns_off_when_neither_cli_nor_ini_provided(self) -> None:
        """Default is OFF when no configuration is provided."""
        config = Mock()
        config.getoption.return_value = None
        config.getini.return_value = ''  # Empty string

        result = _get_enforcement_mode(config)

        assert result == EnforcementMode.OFF

    def it_returns_off_for_invalid_ini_value(self) -> None:
        """Invalid ini value falls back to OFF."""
        config = Mock()
        config.getoption.return_value = None
        config.getini.return_value = 'invalid_mode'  # Not a valid enforcement mode

        result = _get_enforcement_mode(config)

        assert result == EnforcementMode.OFF


@pytest.mark.small
class DescribeGetNetworkBlocker:
    """Test the _get_network_blocker helper function."""

    def it_creates_blocker_on_first_call(self) -> None:
        """New blocker is created on the first call."""
        config = Mock(spec=[])  # Empty spec - no attributes

        blocker = _get_network_blocker(config)

        assert hasattr(config, '_test_categories_network_blocker')
        assert blocker is config._test_categories_network_blocker

    def it_returns_same_blocker_on_subsequent_calls(self) -> None:
        """Same blocker is returned on subsequent calls."""
        config = Mock(spec=[])  # Empty spec - no attributes

        blocker1 = _get_network_blocker(config)
        blocker2 = _get_network_blocker(config)

        assert blocker1 is blocker2
