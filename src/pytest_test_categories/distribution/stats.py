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

    from pytest_test_categories.distribution.config import DistributionConfig
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
    # Tolerance needs to account for up to 4 values each potentially being off by 0.005 after rounding
    # Maximum error from rounding 4 values: 4 * 0.005 = 0.02
    # Using 0.03 to provide a small safety margin
    ROUNDING_TOLERANCE: ClassVar[float] = 0.03

    small: float = Field(ge=0.0, le=ONE_HUNDRED_PERCENT, default=0.0)
    medium: float = Field(ge=0.0, le=ONE_HUNDRED_PERCENT, default=0.0)
    large: float = Field(ge=0.0, le=ONE_HUNDRED_PERCENT, default=0.0)
    xlarge: float = Field(ge=0.0, le=ONE_HUNDRED_PERCENT, default=0.0)

    @field_validator('small', 'medium', 'large', 'xlarge', mode='before')
    @classmethod
    def round_to_two_decimals(cls: type[TestPercentages], v: float) -> float:
        """Round percentage values to two decimal places."""
        return round(float(v), 2)

    @model_validator(mode='after')
    def validate_total(self) -> TestPercentages:
        """Validate that percentages sum to 100% unless all are 0.

        Returns:
            The validated TestPercentages instance.

        Raises:
            ValueError: If percentages don't sum to 100% (within rounding tolerance).

        """
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
    def update_counts(cls: type[DistributionStats], counts: Mapping[TestSize, int] | TestCounts) -> DistributionStats:
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

    def validate_distribution(self, config: DistributionConfig | None = None) -> None:
        """Validate test distribution against target ranges.

        Args:
            config: Optional DistributionConfig with custom targets and tolerances.
                If not provided, uses DEFAULT_DISTRIBUTION_CONFIG.

        Raises:
            ValueError: If the distribution is outside the configured target ranges.

        """
        if config is None:
            from pytest_test_categories.distribution.config import DEFAULT_DISTRIBUTION_CONFIG  # noqa: PLC0415

            effective_config = DEFAULT_DISTRIBUTION_CONFIG
        else:
            effective_config = config

        percentages = self.calculate_percentages()

        self._validate_range(percentages.small, effective_config.get_small_range(), 'Small')
        self._validate_range(percentages.medium, effective_config.get_medium_range(), 'Medium')
        self._validate_range(
            percentages.large + percentages.xlarge, effective_config.get_large_xlarge_range(), 'Large/XLarge'
        )
