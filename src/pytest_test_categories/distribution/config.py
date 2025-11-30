"""Distribution configuration for configurable target percentages.

This module provides the DistributionConfig model for configuring
custom distribution targets and tolerances for test sizes.

Example:
    >>> from pytest_test_categories.distribution.config import DistributionConfig
    >>> config = DistributionConfig(
    ...     small_target=70.0,
    ...     medium_target=20.0,
    ...     large_target=10.0,
    ... )
    >>> config.get_small_range()
    DistributionRange(target=70.0, tolerance=5.0)

"""

from __future__ import annotations

from typing import (
    Annotated,
    Final,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from pytest_test_categories.distribution.stats import DistributionRange

__all__ = [
    'DEFAULT_DISTRIBUTION_CONFIG',
    'DistributionConfig',
]

ONE_HUNDRED_PERCENT: Final[float] = 100.0
ROUNDING_TOLERANCE: Final[float] = 0.03


class DistributionConfig(BaseModel):
    """Configuration for distribution targets across all test sizes.

    This model holds configurable distribution targets and tolerances for each
    test size category. Users can override the defaults via pyproject.toml,
    pytest.ini, or CLI options.

    Default values match Google's Software Engineering at Google recommendations:
    - Small: 80% target (+/-5% tolerance)
    - Medium: 15% target (+/-5% tolerance)
    - Large/XLarge: 5% target (+/-3% tolerance)

    Example:
        >>> config = DistributionConfig(small_target=70.0, medium_target=20.0, large_target=10.0)
        >>> config.get_small_range()
        DistributionRange(target=70.0, tolerance=5.0)

    """

    small_target: Annotated[
        float,
        Field(ge=0.0, le=ONE_HUNDRED_PERCENT, description='Target percentage for small tests'),
    ] = 80.0

    medium_target: Annotated[
        float,
        Field(ge=0.0, le=ONE_HUNDRED_PERCENT, description='Target percentage for medium tests'),
    ] = 15.0

    large_target: Annotated[
        float,
        Field(ge=0.0, le=ONE_HUNDRED_PERCENT, description='Target percentage for large/xlarge tests'),
    ] = 5.0

    small_tolerance: Annotated[
        float,
        Field(gt=0.0, le=20.0, description='Tolerance percentage for small tests'),
    ] = 5.0

    medium_tolerance: Annotated[
        float,
        Field(gt=0.0, le=20.0, description='Tolerance percentage for medium tests'),
    ] = 5.0

    large_tolerance: Annotated[
        float,
        Field(gt=0.0, le=20.0, description='Tolerance percentage for large/xlarge tests'),
    ] = 3.0

    model_config = ConfigDict(frozen=True)

    @property
    def targets_sum(self) -> float:
        """Calculate the sum of all target percentages.

        Returns:
            The sum of small_target, medium_target, and large_target.

        """
        return self.small_target + self.medium_target + self.large_target

    @property
    def targets_sum_to_100(self) -> bool:
        """Check if targets sum to 100% within rounding tolerance.

        Returns:
            True if targets sum to approximately 100%, False otherwise.

        """
        return abs(self.targets_sum - ONE_HUNDRED_PERCENT) <= ROUNDING_TOLERANCE

    def get_small_range(self) -> DistributionRange:
        """Get the DistributionRange for small tests.

        Returns:
            DistributionRange configured for small tests.

        """
        return DistributionRange(target=self.small_target, tolerance=self.small_tolerance)

    def get_medium_range(self) -> DistributionRange:
        """Get the DistributionRange for medium tests.

        Returns:
            DistributionRange configured for medium tests.

        """
        return DistributionRange(target=self.medium_target, tolerance=self.medium_tolerance)

    def get_large_xlarge_range(self) -> DistributionRange:
        """Get the DistributionRange for large/xlarge tests combined.

        Returns:
            DistributionRange configured for large/xlarge tests.

        """
        return DistributionRange(target=self.large_target, tolerance=self.large_tolerance)


# Default configuration matching Google's test size recommendations
DEFAULT_DISTRIBUTION_CONFIG = DistributionConfig()
