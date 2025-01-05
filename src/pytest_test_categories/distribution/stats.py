"""Test distribution statistics."""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    ClassVar,
    Final,
)

from beartype import beartype
from icontract import (
    ensure,
    require,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from numbers import Number

    from pytest_test_categories.types import TestSize

ONE_HUNDRED_PERCENT: Final[float] = 100.0


class DistributionRange(BaseModel):
    """Valid range for a test size distribution percentage."""

    target: float = Field(ge=0.0, le=ONE_HUNDRED_PERCENT)
    tolerance: float = Field(gt=0.0, le=20.0)

    model_config = ConfigDict(frozen=True)

    @property
    def min_value(self) -> float:
        """Minimum acceptable percentage."""
        return max(0.0, self.target - self.tolerance)

    @property
    def max_value(self) -> float:
        """Maximum acceptable percentage."""
        return min(ONE_HUNDRED_PERCENT, self.target + self.tolerance)


# Define distribution targets
DISTRIBUTION_TARGETS = {
    'small': DistributionRange(target=80.0, tolerance=5.0),  # 75-85%
    'medium': DistributionRange(target=15.0, tolerance=5.0),  # 10-20%
    'large_xlarge': DistributionRange(target=5.0, tolerance=3.0),  # 2-8%
}


class TestCounts(BaseModel):
    """Count of tests by size."""

    small: int = Field(default=0, ge=0)
    medium: int = Field(default=0, ge=0)
    large: int = Field(default=0, ge=0)
    xlarge: int = Field(default=0, ge=0)

    model_config = ConfigDict(frozen=True)


class TestPercentages(BaseModel):
    """Distribution percentages of tests by size."""

    _TOTAL_ERROR: ClassVar[str] = 'Percentages must sum to 100% (within rounding error) unless all are 0'
    ROUNDING_TOLERANCE: ClassVar[float] = 0.01

    small: float = Field(ge=0.0, le=ONE_HUNDRED_PERCENT, default=0.0)
    medium: float = Field(ge=0.0, le=ONE_HUNDRED_PERCENT, default=0.0)
    large: float = Field(ge=0.0, le=ONE_HUNDRED_PERCENT, default=0.0)
    xlarge: float = Field(ge=0.0, le=ONE_HUNDRED_PERCENT, default=0.0)

    @field_validator('small', 'medium', 'large', 'xlarge')
    @classmethod
    def round_to_two_decimals(cls: type[TestPercentages], v: Number) -> float:
        """Round percentage values to two decimal places."""
        return round(v, 2)

    @model_validator(mode='after')
    def validate_total(self) -> TestPercentages:
        """Validate that percentages sum to 100% unless all are 0."""
        values = [self.small, self.medium, self.large, self.xlarge]
        total = sum(values)

        if not (all(x == 0.0 for x in values) or abs(total - ONE_HUNDRED_PERCENT) <= self.ROUNDING_TOLERANCE):
            raise ValueError(self._TOTAL_ERROR)

        return self


class DistributionStats(BaseModel):
    """Test distribution statistics."""

    _RANGE_ERROR = '{name} test percentage ({value:.2f}%) outside target range {min:.2f}%-{max:.2f}%'

    counts: TestCounts = Field(default_factory=TestCounts)

    model_config = ConfigDict(frozen=True)

    @classmethod
    def update_counts(
        cls: type[DistributionStats], counts: Mapping[TestSize, int] | TestCounts
    ) -> type[DistributionStats]:
        """Return a new instance with updated counts."""
        return cls(counts=TestCounts.model_validate(counts))

    @beartype
    @ensure(lambda result: isinstance(result, TestPercentages), 'Must return TestPercentages')
    def calculate_percentages(self) -> TestPercentages:
        """Calculate the percentage distribution of test sizes."""
        total = self.counts.small + self.counts.medium + self.counts.large + self.counts.xlarge
        if total == 0:
            return TestPercentages()

        return TestPercentages(
            small=(self.counts.small * 100.0) / total,
            medium=(self.counts.medium * 100.0) / total,
            large=(self.counts.large * 100.0) / total,
            xlarge=(self.counts.xlarge * 100.0) / total,
        )

    @beartype
    @require(lambda value: 0.0 <= value <= ONE_HUNDRED_PERCENT, 'Percentage value must be between 0 and 100')
    def _validate_range(self, value: float, target_range: DistributionRange, name: str) -> None:
        """Validate a percentage value against its target range."""
        if not target_range.min_value <= value <= target_range.max_value:
            raise ValueError(
                self._RANGE_ERROR.format(
                    name=name,
                    value=value,
                    min=target_range.min_value,
                    max=target_range.max_value,
                )
            )

    def validate_distribution(self) -> None:
        """Validate test distribution against target ranges."""
        percentages = self.calculate_percentages()

        self._validate_range(percentages.small, DISTRIBUTION_TARGETS['small'], 'Small')
        self._validate_range(percentages.medium, DISTRIBUTION_TARGETS['medium'], 'Medium')
        self._validate_range(
            percentages.large + percentages.xlarge, DISTRIBUTION_TARGETS['large_xlarge'], 'Large/XLarge'
        )
