"""Unit tests for configurable time limit options.

This module tests the pytest options for configuring time limits via
pyproject.toml, pytest.ini, and CLI arguments.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from pytest_test_categories.timing import (
    DEFAULT_TIME_LIMIT_CONFIG,
    TimeLimitConfig,
)


@pytest.mark.small
class DescribePytestAddoptionTimeLimits:
    """Test that pytest_addoption registers time limit options."""

    def it_registers_time_limits_ini_option(self) -> None:
        """Test that pytest_addoption registers time_limits ini option."""
        from pytest_test_categories import pytest_addoption

        parser = Mock()
        group = Mock()
        parser.getgroup.return_value = group

        pytest_addoption(parser)

        # Find the time_limits ini call
        time_limits_ini_call = None
        for call in parser.addini.call_args_list:
            if call[0][0] == 'test_categories_time_limits':
                time_limits_ini_call = call
                break
        assert time_limits_ini_call is not None
        assert 'Time limit configuration' in time_limits_ini_call[1]['help']

    def it_registers_individual_time_limit_ini_options(self) -> None:
        """Test that pytest_addoption registers individual time limit ini options."""
        from pytest_test_categories import pytest_addoption

        parser = Mock()
        group = Mock()
        parser.getgroup.return_value = group

        pytest_addoption(parser)

        # Check all individual size options are registered
        expected_ini_options = [
            'test_categories_small_time_limit',
            'test_categories_medium_time_limit',
            'test_categories_large_time_limit',
            'test_categories_xlarge_time_limit',
        ]
        registered_ini_names = [call[0][0] for call in parser.addini.call_args_list]
        for option in expected_ini_options:
            assert option in registered_ini_names, f'{option} not registered'

    def it_registers_cli_time_limit_options(self) -> None:
        """Test that pytest_addoption registers CLI time limit options."""
        from pytest_test_categories import pytest_addoption

        parser = Mock()
        group = Mock()
        parser.getgroup.return_value = group

        pytest_addoption(parser)

        # Check CLI options are registered
        expected_cli_options = [
            '--test-categories-small-time-limit',
            '--test-categories-medium-time-limit',
            '--test-categories-large-time-limit',
            '--test-categories-xlarge-time-limit',
        ]
        registered_cli_options = [call[0][0] for call in group.addoption.call_args_list]
        for option in expected_cli_options:
            assert option in registered_cli_options, f'{option} not registered'


@pytest.mark.small
class DescribeGetTimeLimitConfig:
    """Test the _get_time_limit_config helper function."""

    def it_returns_default_when_no_config_provided(self) -> None:
        """Return default config when no options are set."""
        from pytest_test_categories.plugin import _get_time_limit_config

        config = Mock()
        config.getoption.return_value = None
        config.getini.return_value = ''

        result = _get_time_limit_config(config)

        assert result == DEFAULT_TIME_LIMIT_CONFIG

    def it_uses_cli_small_time_limit_when_provided(self) -> None:
        """CLI small time limit overrides defaults."""
        from pytest_test_categories.plugin import _get_time_limit_config

        config = Mock()

        def mock_getoption(name: str, default: object = None) -> object:  # noqa: ARG001
            if name == '--test-categories-small-time-limit':
                return 2.0
            return None

        def mock_getini(name: str) -> str:  # noqa: ARG001
            return ''

        config.getoption.side_effect = mock_getoption
        config.getini.side_effect = mock_getini

        result = _get_time_limit_config(config)

        assert result.small == 2.0
        assert result.medium == 300.0  # default

    def it_uses_cli_medium_time_limit_when_provided(self) -> None:
        """CLI medium time limit overrides defaults."""
        from pytest_test_categories.plugin import _get_time_limit_config

        config = Mock()

        def mock_getoption(name: str, default: object = None) -> object:  # noqa: ARG001
            if name == '--test-categories-medium-time-limit':
                return 600.0
            return None

        config.getoption.side_effect = mock_getoption
        config.getini.return_value = ''

        result = _get_time_limit_config(config)

        assert result.medium == 600.0

    def it_uses_ini_time_limit_when_cli_not_provided(self) -> None:
        """Ini value used when CLI option not provided."""
        from pytest_test_categories.plugin import _get_time_limit_config

        config = Mock()
        config.getoption.return_value = None

        def mock_getini(name: str) -> str:
            if name == 'test_categories_small_time_limit':
                return '2.0'
            return ''

        config.getini.side_effect = mock_getini

        result = _get_time_limit_config(config)

        assert result.small == 2.0

    def it_prefers_cli_over_ini_options(self) -> None:
        """CLI takes precedence over ini options."""
        from pytest_test_categories.plugin import _get_time_limit_config

        config = Mock()

        def mock_getoption(name: str, default: object = None) -> object:  # noqa: ARG001
            if name == '--test-categories-small-time-limit':
                return 3.0
            return None

        def mock_getini(name: str) -> str:
            if name == 'test_categories_small_time_limit':
                return '2.0'  # Should be ignored
            return ''

        config.getoption.side_effect = mock_getoption
        config.getini.side_effect = mock_getini

        result = _get_time_limit_config(config)

        assert result.small == 3.0

    def it_combines_multiple_custom_limits(self) -> None:
        """Combine multiple custom limits from different sources."""
        from pytest_test_categories.plugin import _get_time_limit_config

        config = Mock()

        def mock_getoption(name: str, default: object = None) -> object:  # noqa: ARG001
            if name == '--test-categories-small-time-limit':
                return 2.0
            if name == '--test-categories-xlarge-time-limit':
                return 1800.0
            return None

        def mock_getini(name: str) -> str:
            if name == 'test_categories_medium_time_limit':
                return '600.0'
            if name == 'test_categories_large_time_limit':
                return '1200.0'
            return ''

        config.getoption.side_effect = mock_getoption
        config.getini.side_effect = mock_getini

        result = _get_time_limit_config(config)

        assert result.small == 2.0
        assert result.medium == 600.0
        assert result.large == 1200.0
        assert result.xlarge == 1800.0

    def it_validates_ordering_after_combining(self) -> None:
        """Raise error if combined limits violate ordering."""
        from pytest_test_categories.plugin import _get_time_limit_config

        config = Mock()

        def mock_getoption(name: str, default: object = None) -> object:  # noqa: ARG001
            if name == '--test-categories-small-time-limit':
                return 500.0  # larger than default medium (300)
            return None

        config.getoption.side_effect = mock_getoption
        config.getini.return_value = ''

        with pytest.raises(ValueError, match=r'small .* must be less than medium'):
            _get_time_limit_config(config)


@pytest.mark.small
class DescribeTimeLimitConfigInPluginState:
    """Test that time limit config is stored in PluginState."""

    def it_stores_time_limit_config_in_plugin_state(self) -> None:
        """Plugin state includes time_limit_config field."""
        from pytest_test_categories.types import PluginState

        state = PluginState()

        # Should have time_limit_config field with default
        assert hasattr(state, 'time_limit_config')
        assert state.time_limit_config == DEFAULT_TIME_LIMIT_CONFIG

    def it_allows_custom_time_limit_config(self) -> None:
        """Plugin state can be initialized with custom time limit config."""
        from pytest_test_categories.types import PluginState

        custom_config = TimeLimitConfig(small=2.0)
        state = PluginState(time_limit_config=custom_config)

        assert state.time_limit_config == custom_config
        # Cast to access typed attributes since time_limit_config is object | None
        config = state.time_limit_config
        assert isinstance(config, TimeLimitConfig)
        assert config.small == 2.0
