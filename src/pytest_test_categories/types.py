"""Type definitions for pytest-test-categories."""

from __future__ import annotations

from enum import (
    Enum,
    auto,
)


class TestSize(Enum):
    """Test size categories."""

    SMALL = auto()
    MEDIUM = auto()
    LARGE = auto()
    XLARGE = auto()

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
