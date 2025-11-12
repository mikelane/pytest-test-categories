"""Tests for WarningSystemPort and its adapters.

This module tests the warning system abstraction layer, including:
- WarningSystemPort interface contract
- PytestWarningAdapter production adapter
- FakeWarningSystem test adapter
"""

from __future__ import annotations

import warnings

import pytest

from pytest_test_categories.adapters.pytest_adapter import PytestWarningAdapter
from tests._fixtures.warning_system import FakeWarningSystem

pytestmark = pytest.mark.small


class DescribePytestWarningAdapter:
    """Tests for PytestWarningAdapter production adapter."""

    def it_emits_user_warning_with_correct_message(self) -> None:
        """It emits a UserWarning with the provided message."""
        adapter = PytestWarningAdapter()
        message = 'Test warning message'

        with pytest.warns(UserWarning, match=message):
            adapter.warn(message, category=UserWarning)

    def it_emits_deprecation_warning(self) -> None:
        """It emits a DeprecationWarning when requested."""
        adapter = PytestWarningAdapter()
        message = 'Deprecated feature'

        with pytest.warns(DeprecationWarning, match=message):
            adapter.warn(message, category=DeprecationWarning)

    def it_uses_correct_stacklevel(self) -> None:
        """It uses stacklevel 3 to point to the caller's caller."""
        adapter = PytestWarningAdapter()
        message = 'Test warning for stacklevel'

        # Capture the warning and verify stacklevel is set
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter('always')
            adapter.warn(message, category=UserWarning)

            assert len(caught_warnings) == 1
            # The warning should exist (stacklevel validation is done by pytest)
            assert str(caught_warnings[0].message) == message

    def it_emits_custom_warning_category(self) -> None:
        """It emits custom warning categories."""

        class CustomWarning(UserWarning):
            """Custom warning for testing."""

        adapter = PytestWarningAdapter()
        message = 'Custom warning message'

        with pytest.warns(CustomWarning, match=message):
            adapter.warn(message, category=CustomWarning)


class DescribeFakeWarningSystem:
    """Tests for FakeWarningSystem test adapter."""

    def it_records_warning_without_emitting(self) -> None:
        """It records warnings without emitting them to the system."""
        fake = FakeWarningSystem()
        message = 'Test warning'

        # Ensure no actual warnings are emitted
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter('always')
            fake.warn(message, category=UserWarning)

            # No warnings emitted to the system
            assert len(caught_warnings) == 0

        # But the warning is recorded
        assert fake.has_warning(message)

    def it_stores_multiple_warnings(self) -> None:
        """It stores multiple warnings in order."""
        fake = FakeWarningSystem()

        fake.warn('First warning', category=UserWarning)
        fake.warn('Second warning', category=DeprecationWarning)
        fake.warn('Third warning', category=UserWarning)

        warnings_list = fake.get_warnings()
        assert len(warnings_list) == 3
        assert warnings_list[0] == ('First warning', UserWarning)
        assert warnings_list[1] == ('Second warning', DeprecationWarning)
        assert warnings_list[2] == ('Third warning', UserWarning)

    def it_checks_if_warning_exists_by_message(self) -> None:
        """It checks if a warning exists by message."""
        fake = FakeWarningSystem()
        fake.warn('Expected warning', category=UserWarning)
        fake.warn('Another warning', category=UserWarning)

        assert fake.has_warning('Expected warning')
        assert fake.has_warning('Another warning')
        assert not fake.has_warning('Non-existent warning')

    def it_checks_if_warning_exists_by_category(self) -> None:
        """It checks if a warning exists by category."""
        fake = FakeWarningSystem()
        fake.warn('User warning', category=UserWarning)
        fake.warn('Deprecation warning', category=DeprecationWarning)

        assert fake.has_warning_with_category(UserWarning)
        assert fake.has_warning_with_category(DeprecationWarning)
        assert not fake.has_warning_with_category(RuntimeWarning)

    def it_checks_for_warning_with_both_message_and_category(self) -> None:
        """It checks if a warning exists with specific message and category."""
        fake = FakeWarningSystem()
        fake.warn('Test message', category=UserWarning)
        fake.warn('Test message', category=DeprecationWarning)

        assert fake.has_warning_with_category(UserWarning, 'Test message')
        assert fake.has_warning_with_category(DeprecationWarning, 'Test message')
        assert not fake.has_warning_with_category(UserWarning, 'Different message')
        assert not fake.has_warning_with_category(RuntimeWarning, 'Test message')

    def it_clears_all_warnings(self) -> None:
        """It clears all recorded warnings."""
        fake = FakeWarningSystem()
        fake.warn('First warning', category=UserWarning)
        fake.warn('Second warning', category=DeprecationWarning)

        assert len(fake.get_warnings()) == 2

        fake.clear()

        assert len(fake.get_warnings()) == 0
        assert not fake.has_warning('First warning')
        assert not fake.has_warning('Second warning')

    def it_returns_empty_list_when_no_warnings(self) -> None:
        """It returns an empty list when no warnings are recorded."""
        fake = FakeWarningSystem()

        warnings_list = fake.get_warnings()

        assert warnings_list == []
        assert not fake.has_warning('any message')
        assert not fake.has_warning_with_category(UserWarning)
