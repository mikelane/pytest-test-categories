"""Unit tests for configurable distribution target options.

This module tests the pytest options for configuring distribution targets via
pyproject.toml, pytest.ini, and CLI arguments.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from pytest_test_categories.distribution.config import (
    DEFAULT_DISTRIBUTION_CONFIG,
    DistributionConfig,
)


@pytest.mark.small
class DescribePytestAddoptionDistributionTargets:
    """Test that pytest_addoption registers distribution target options."""

    def it_registers_individual_target_ini_options(self) -> None:
        """Test that pytest_addoption registers individual target ini options."""
        from pytest_test_categories import pytest_addoption

        parser = Mock()
        group = Mock()
        parser.getgroup.return_value = group

        pytest_addoption(parser)

        expected_ini_options = [
            'test_categories_small_target',
            'test_categories_medium_target',
            'test_categories_large_target',
            'test_categories_tolerance',
        ]
        registered_ini_names = [call[0][0] for call in parser.addini.call_args_list]
        for option in expected_ini_options:
            assert option in registered_ini_names, f'{option} not registered'

    def it_registers_cli_target_options(self) -> None:
        """Test that pytest_addoption registers CLI distribution target options."""
        from pytest_test_categories import pytest_addoption

        parser = Mock()
        group = Mock()
        parser.getgroup.return_value = group

        pytest_addoption(parser)

        expected_cli_options = [
            '--test-categories-small-target',
            '--test-categories-medium-target',
            '--test-categories-large-target',
            '--test-categories-tolerance',
        ]
        registered_cli_options = [call[0][0] for call in group.addoption.call_args_list]
        for option in expected_cli_options:
            assert option in registered_cli_options, f'{option} not registered'


@pytest.mark.small
class DescribeGetDistributionConfig:
    """Test the _get_distribution_config helper function."""

    def it_returns_default_when_no_config_provided(self) -> None:
        """Return default config when no options are set."""
        from pytest_test_categories.plugin import _get_distribution_config

        config = Mock()
        config.getoption.return_value = None
        config.getini.return_value = ''

        result = _get_distribution_config(config)

        assert result == DEFAULT_DISTRIBUTION_CONFIG

    def it_uses_cli_small_target_when_provided(self) -> None:
        """CLI small target overrides defaults."""
        from pytest_test_categories.plugin import _get_distribution_config

        config = Mock()

        def mock_getoption(name: str, default: object = None) -> object:  # noqa: ARG001
            if name == '--test-categories-small-target':
                return 70.0
            return None

        def mock_getini(name: str) -> str:  # noqa: ARG001
            return ''

        config.getoption.side_effect = mock_getoption
        config.getini.side_effect = mock_getini

        result = _get_distribution_config(config)

        assert result.small_target == 70.0
        assert result.medium_target == 15.0  # default

    def it_uses_cli_medium_target_when_provided(self) -> None:
        """CLI medium target overrides defaults."""
        from pytest_test_categories.plugin import _get_distribution_config

        config = Mock()

        def mock_getoption(name: str, default: object = None) -> object:  # noqa: ARG001
            if name == '--test-categories-medium-target':
                return 20.0
            return None

        config.getoption.side_effect = mock_getoption
        config.getini.return_value = ''

        result = _get_distribution_config(config)

        assert result.medium_target == 20.0

    def it_uses_cli_large_target_when_provided(self) -> None:
        """CLI large target overrides defaults."""
        from pytest_test_categories.plugin import _get_distribution_config

        config = Mock()

        def mock_getoption(name: str, default: object = None) -> object:  # noqa: ARG001
            if name == '--test-categories-large-target':
                return 10.0
            return None

        config.getoption.side_effect = mock_getoption
        config.getini.return_value = ''

        result = _get_distribution_config(config)

        assert result.large_target == 10.0

    def it_uses_cli_tolerance_for_all_sizes(self) -> None:
        """CLI tolerance applies to all size categories."""
        from pytest_test_categories.plugin import _get_distribution_config

        config = Mock()

        def mock_getoption(name: str, default: object = None) -> object:  # noqa: ARG001
            if name == '--test-categories-tolerance':
                return 8.0
            return None

        config.getoption.side_effect = mock_getoption
        config.getini.return_value = ''

        result = _get_distribution_config(config)

        assert result.small_tolerance == 8.0
        assert result.medium_tolerance == 8.0
        assert result.large_tolerance == 8.0

    def it_uses_ini_target_when_cli_not_provided(self) -> None:
        """Ini value used when CLI option not provided."""
        from pytest_test_categories.plugin import _get_distribution_config

        config = Mock()
        config.getoption.return_value = None

        def mock_getini(name: str) -> str:
            if name == 'test_categories_small_target':
                return '70.0'
            return ''

        config.getini.side_effect = mock_getini

        result = _get_distribution_config(config)

        assert result.small_target == 70.0

    def it_prefers_cli_over_ini_options(self) -> None:
        """CLI takes precedence over ini options."""
        from pytest_test_categories.plugin import _get_distribution_config

        config = Mock()

        def mock_getoption(name: str, default: object = None) -> object:  # noqa: ARG001
            if name == '--test-categories-small-target':
                return 60.0
            return None

        def mock_getini(name: str) -> str:
            if name == 'test_categories_small_target':
                return '70.0'  # Should be ignored
            return ''

        config.getoption.side_effect = mock_getoption
        config.getini.side_effect = mock_getini

        result = _get_distribution_config(config)

        assert result.small_target == 60.0

    def it_combines_multiple_custom_targets(self) -> None:
        """Combine multiple custom targets from different sources."""
        from pytest_test_categories.plugin import _get_distribution_config

        config = Mock()

        def mock_getoption(name: str, default: object = None) -> object:  # noqa: ARG001
            if name == '--test-categories-small-target':
                return 70.0
            if name == '--test-categories-tolerance':
                return 8.0
            return None

        def mock_getini(name: str) -> str:
            if name == 'test_categories_medium_target':
                return '20.0'
            if name == 'test_categories_large_target':
                return '10.0'
            return ''

        config.getoption.side_effect = mock_getoption
        config.getini.side_effect = mock_getini

        result = _get_distribution_config(config)

        assert result.small_target == 70.0
        assert result.medium_target == 20.0
        assert result.large_target == 10.0
        assert result.small_tolerance == 8.0
        assert result.medium_tolerance == 8.0
        assert result.large_tolerance == 8.0


@pytest.mark.small
class DescribeDistributionConfigInPluginState:
    """Test that distribution config is stored in PluginState."""

    def it_stores_distribution_config_in_plugin_state(self) -> None:
        """Plugin state includes distribution_config field."""
        from pytest_test_categories.types import PluginState

        state = PluginState()

        assert hasattr(state, 'distribution_config')
        assert state.distribution_config == DEFAULT_DISTRIBUTION_CONFIG

    def it_allows_custom_distribution_config(self) -> None:
        """Plugin state can be initialized with custom distribution config."""
        from pytest_test_categories.types import PluginState

        custom_config = DistributionConfig(small_target=70.0, medium_target=20.0, large_target=10.0)
        state = PluginState(distribution_config=custom_config)

        assert state.distribution_config == custom_config
        config = state.distribution_config
        assert isinstance(config, DistributionConfig)
        assert config.small_target == 70.0
