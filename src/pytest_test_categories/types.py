"""Type definitions for pytest-test-categories."""

from __future__ import annotations

from enum import StrEnum


class TimingViolationError(Exception):
    """Exception raised for timing violations."""


class TestSize(StrEnum):
    """Test size categories."""

    SMALL = 'small'
    MEDIUM = 'medium'
    LARGE = 'large'
    XLARGE = 'xlarge'

    @property
    def marker_name(self) -> str:
        """Get the pytest marker name for this size."""
        return self.name.lower()

    @property
    def description(self) -> str:
        """Get the description for this test size marker."""
        return f'mark test as {self.name} size'

    @property
    def label(self) -> str:
        """Get the label to show in test output."""
        return f'[{self.name}]'
