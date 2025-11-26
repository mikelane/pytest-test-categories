"""Fake warning system implementation for testing.

This module provides FakeWarningSystem, a controllable test double that implements
the WarningSystemPort interface. It records warnings without emitting them, enabling
deterministic testing without side effects.

The FakeWarningSystem follows hexagonal architecture principles:
- Implements the WarningSystemPort interface
- Records warnings without emitting them to the system
- Provides helper methods for test assertions
- Used in tests as a substitute for PytestWarningAdapter
- Enables testing behavior without system warnings
"""

from __future__ import annotations

from pytest_test_categories.types import WarningSystemPort


class FakeWarningSystem(WarningSystemPort):
    """Controllable warning system adapter for testing.

    This is a test double that records warnings without emitting them to Python's
    warnings system. It allows tests to verify warning behavior without side effects
    and without depending on the warnings module's implementation.

    The FakeWarningSystem follows hexagonal architecture principles:
    - Implements the WarningSystemPort interface
    - Records warnings in memory for inspection
    - Provides helper methods for test assertions
    - Used in tests as a substitute for PytestWarningAdapter
    - Enables testing behavior without actual warnings

    Example:
        >>> fake = FakeWarningSystem()
        >>> fake.warn('Test warning', category=UserWarning)
        >>> assert fake.has_warning('Test warning')
        >>> assert fake.has_warning_with_category(UserWarning)
        >>> warnings = fake.get_warnings()
        >>> assert warnings == [('Test warning', UserWarning)]
        >>> fake.clear()
        >>> assert not fake.has_warning('Test warning')

    """

    def __init__(self) -> None:
        """Initialize the fake warning system with an empty warning list."""
        self._warnings: list[tuple[str, type[Warning]]] = []

    def warn(self, message: str, category: type[Warning] | None = None) -> None:
        """Record a warning without emitting it.

        Args:
            message: The warning message to record.
            category: The warning category (default: UserWarning if None).

        """
        actual_category = category if category is not None else UserWarning
        self._warnings.append((message, actual_category))

    def has_warning(self, message: str) -> bool:
        """Check if a warning with the given message was recorded.

        Args:
            message: The warning message to search for.

        Returns:
            True if a warning with this message exists, False otherwise.

        """
        return any(msg == message for msg, _ in self._warnings)

    def has_warning_with_category(self, category: type[Warning], message: str | None = None) -> bool:
        """Check if a warning with the given category (and optionally message) was recorded.

        Args:
            category: The warning category to search for.
            message: Optional warning message to match. If None, matches any message.

        Returns:
            True if a matching warning exists, False otherwise.

        """
        if message is None:
            return any(cat == category for _, cat in self._warnings)
        return any(msg == message and cat == category for msg, cat in self._warnings)

    def get_warnings(self) -> list[tuple[str, type[Warning]]]:
        """Get all recorded warnings.

        Returns:
            A list of tuples containing (message, category) for each warning.

        """
        return self._warnings.copy()

    def clear(self) -> None:
        """Clear all recorded warnings."""
        self._warnings.clear()
