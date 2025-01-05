"""Test distribution statistics."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from numbers import Number

    from pytest_test_categories.types import TestSize


class TestCounts(BaseModel):
    """Count of tests by size."""

    small: int = 0
    medium: int = 0
    large: int = 0
    xlarge: int = 0

    model_config = ConfigDict(frozen=True)


class TestPercentages(BaseModel):
    """Distribution percentages of tests by size."""

    small: float = Field(ge=0.0, le=100.0, default=0.0)
    medium: float = Field(ge=0.0, le=100.0, default=0.0)
    large: float = Field(ge=0.0, le=100.0, default=0.0)
    xlarge: float = Field(ge=0.0, le=100.0, default=0.0)

    @field_validator('small', 'medium', 'large', 'xlarge')
    @classmethod
    def round_to_two_decimals(cls: type[TestPercentages], v: Number) -> float:
        """Round percentage values to two decimal places."""
        return round(v, 2)


class DistributionStats(BaseModel):
    """Test distribution statistics."""

    counts: TestCounts = Field(default_factory=TestCounts)

    model_config = ConfigDict(frozen=True)

    @classmethod
    def update_counts(
        cls: type[DistributionStats], counts: Mapping[TestSize, int] | TestCounts
    ) -> type[DistributionStats]:
        """Return a new instance with updated counts."""
        return cls(counts=TestCounts.model_validate(counts))

    def calculate_percentages(self) -> TestPercentages:
        """Calculate the percentage distribution of test sizes."""
        total = self.counts.small + self.counts.medium + self.counts.large + self.counts.xlarge
        if total == 0:
            return TestPercentages()

        return TestPercentages(
            small=self.counts.small * 100.0 / total,
            medium=self.counts.medium * 100.0 / total,
            large=self.counts.large * 100.0 / total,
            xlarge=self.counts.xlarge * 100.0 / total,
        )
