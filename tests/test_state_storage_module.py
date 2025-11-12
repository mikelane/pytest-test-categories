"""Unit tests for StateStorage adapters."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from pytest_test_categories.plugin import PluginState
from pytest_test_categories.state_storage import (
    FakeStateStorage,
    PytestConfigStorage,
)


@pytest.mark.small
class DescribeFakeStateStorage:
    """Tests for FakeStateStorage adapter."""

    def it_stores_and_retrieves_state(self) -> None:
        """Stores and retrieves plugin state."""
        storage = FakeStateStorage()
        state = PluginState(active=True)
        config = object()  # FakeStateStorage doesn't need real Config

        storage.set_state(config, state)
        retrieved = storage.get_state(config)

        assert retrieved is state
        assert retrieved.active is True

    def it_returns_none_when_no_state_exists(self) -> None:
        """Returns None when no state has been set."""
        storage = FakeStateStorage()
        config = object()

        result = storage.get_state(config)

        assert result is None

    def it_reports_whether_state_exists(self) -> None:
        """Reports whether state exists for a config."""
        storage = FakeStateStorage()
        config = object()

        assert not storage.has_state(config)

        storage.set_state(config, PluginState())
        assert storage.has_state(config)

    def it_can_store_multiple_configs(self) -> None:
        """Stores state for multiple configs independently."""
        storage = FakeStateStorage()
        config1 = object()
        config2 = object()
        state1 = PluginState(active=True)
        state2 = PluginState(active=False)

        storage.set_state(config1, state1)
        storage.set_state(config2, state2)

        assert storage.get_state(config1) is state1
        assert storage.get_state(config2) is state2


@pytest.mark.medium
class DescribePytestConfigStorage:
    """Integration tests for PytestConfigStorage adapter."""

    def it_stores_and_retrieves_state_from_config_attribute(self) -> None:
        """Stores and retrieves plugin state from Config attribute."""
        storage = PytestConfigStorage()
        config = Mock(spec=['_test_categories_state'])
        state = PluginState(active=True)

        storage.set_state(config, state)
        retrieved = storage.get_state(config)

        assert retrieved is state
        assert retrieved.active is True

    def it_returns_none_when_no_state_attribute_exists(self) -> None:
        """Returns None when Config has no state attribute."""
        storage = PytestConfigStorage()
        config = Mock(spec=[])  # No _test_categories_state attribute

        result = storage.get_state(config)

        assert result is None

    def it_reports_whether_state_attribute_exists(self) -> None:
        """Reports whether state attribute exists on Config."""
        storage = PytestConfigStorage()
        config = Mock(spec=[])

        assert not storage.has_state(config)

        storage.set_state(config, PluginState())
        assert storage.has_state(config)

    def it_overwrites_existing_state(self) -> None:
        """Overwrites existing state when set_state is called again."""
        storage = PytestConfigStorage()
        config = Mock(spec=['_test_categories_state'])
        state1 = PluginState(active=True)
        state2 = PluginState(active=False)

        storage.set_state(config, state1)
        assert storage.get_state(config) is state1

        storage.set_state(config, state2)
        assert storage.get_state(config) is state2
        assert storage.get_state(config) is not state1

    def it_uses_correct_attribute_name(self) -> None:
        """Uses the correct attribute name on Config."""
        storage = PytestConfigStorage()
        config = Mock(spec=[])
        state = PluginState()

        storage.set_state(config, state)

        # Verify the attribute name matches what plugin.py expects
        assert hasattr(config, '_test_categories_state')
        assert config._test_categories_state is state
