"""State storage adapters for plugin state management."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytest_test_categories.types import StateStoragePort

if TYPE_CHECKING:
    import pytest


class FakeStateStorage(StateStoragePort):
    """Test adapter for state storage using in-memory dict.

    This is a test double that allows tests to verify state storage behavior
    without depending on pytest.Config. This eliminates pytest dependencies
    in unit tests and makes tests fast and deterministic.

    The FakeStateStorage follows hexagonal architecture principles:
    - Implements the StateStoragePort (interface)
    - Provides in-memory dict-based storage
    - Used in tests as a substitute for PytestConfigStorage
    - Enables testing behavior without implementation details

    Example:
        >>> storage = FakeStateStorage()
        >>> config = object()  # Any object works as "config"
        >>> storage.set_state(config, PluginState())
        >>> state = storage.get_state(config)
        >>> assert storage.has_state(config)

    """

    def __init__(self) -> None:
        """Initialize the fake storage with an empty dict."""
        self._storage: dict[int, object] = {}

    def get_state(self, config: pytest.Config) -> object | None:
        """Retrieve plugin state from in-memory storage.

        Args:
            config: Any object to use as key (doesn't need to be real Config).

        Returns:
            The stored state object, or None if no state exists.

        """
        return self._storage.get(id(config))

    def set_state(self, config: pytest.Config, state: object) -> None:
        """Store plugin state in in-memory dict.

        Args:
            config: Any object to use as key (doesn't need to be real Config).
            state: The state object to store.

        """
        self._storage[id(config)] = state

    def has_state(self, config: pytest.Config) -> bool:
        """Check if state exists in in-memory storage.

        Args:
            config: Any object to use as key (doesn't need to be real Config).

        Returns:
            True if state exists, False otherwise.

        """
        return id(config) in self._storage


class PytestConfigStorage(StateStoragePort):
    """Production adapter for state storage using pytest.Config attributes.

    This is the production adapter that stores plugin state as an attribute
    on the pytest.Config object, following pytest's standard pattern for
    plugin state management.

    The PytestConfigStorage follows hexagonal architecture principles:
    - Implements the StateStoragePort (interface)
    - Stores state as _test_categories_state attribute on Config
    - Used in production with real pytest
    - Provides pytest-idiomatic state management

    Example:
        >>> storage = PytestConfigStorage()
        >>> storage.set_state(config, PluginState())
        >>> state = storage.get_state(config)
        >>> assert storage.has_state(config)

    """

    _ATTR_NAME = '_test_categories_state'

    def get_state(self, config: pytest.Config) -> object | None:
        """Retrieve plugin state from pytest.Config attribute.

        Args:
            config: The pytest Config object.

        Returns:
            The stored state object, or None if no state exists.

        """
        return getattr(config, self._ATTR_NAME, None)

    def set_state(self, config: pytest.Config, state: object) -> None:
        """Store plugin state as pytest.Config attribute.

        Args:
            config: The pytest Config object.
            state: The state object to store.

        """
        setattr(config, self._ATTR_NAME, state)

    def has_state(self, config: pytest.Config) -> bool:
        """Check if state exists on pytest.Config.

        Args:
            config: The pytest Config object.

        Returns:
            True if state exists, False otherwise.

        """
        return hasattr(config, self._ATTR_NAME)
