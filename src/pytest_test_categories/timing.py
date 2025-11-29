"""Time limit configuration and validation for test categories."""

from __future__ import annotations

from typing import (
    Annotated,
    Any,
    Self,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from pytest_test_categories.types import (
    TestSize,
    TimingViolationError,
)

__all__ = [
    'DEFAULT_TIME_LIMIT_CONFIG',
    'LARGE_LIMIT',
    'MEDIUM_LIMIT',
    'SMALL_LIMIT',
    'TIME_LIMITS',
    'XLARGE_LIMIT',
    'TimeLimit',
    'TimeLimitConfig',
    'TimingViolationError',
    'get_limit',
    'validate',
]


class TimeLimit(BaseModel):
    """Configuration for a test size's time limit in seconds."""

    limit: Annotated[float, Field(gt=0)]  # Time limit in seconds must be positive

    model_config = ConfigDict(frozen=True)


class TimeLimitConfig(BaseModel):
    """Configuration for time limits across all test sizes.

    This model holds configurable time limits for each test size category.
    Users can override the defaults via pyproject.toml, pytest.ini, or CLI options.

    The limits must follow ordering constraints:
    - small < medium < large <= xlarge

    Default values match Google's test size definitions:
    - Small: 1 second (fast unit tests)
    - Medium: 300 seconds (5 minutes, integration tests)
    - Large: 900 seconds (15 minutes, end-to-end tests)
    - XLarge: 900 seconds (15 minutes, same as large by default)

    Example:
        >>> config = TimeLimitConfig(small=2.0, medium=600.0)
        >>> config.get_limit(TestSize.SMALL)
        2.0
        >>> config.get_limit(TestSize.MEDIUM)
        600.0

    """

    small: Annotated[float, Field(gt=0, description='Time limit in seconds for small tests')] = 1.0
    medium: Annotated[float, Field(gt=0, description='Time limit in seconds for medium tests')] = 300.0
    large: Annotated[float, Field(gt=0, description='Time limit in seconds for large tests')] = 900.0
    xlarge: Annotated[float, Field(gt=0, description='Time limit in seconds for xlarge tests')] = 900.0

    model_config = ConfigDict(frozen=True)

    @model_validator(mode='after')
    def validate_ordering(self) -> Self:
        """Validate that time limits are properly ordered.

        Ensures: small < medium < large <= xlarge

        Raises:
            ValueError: If limits are not properly ordered.

        """
        if self.small >= self.medium:
            msg = f'small ({self.small}s) must be less than medium ({self.medium}s)'
            raise ValueError(msg)
        if self.medium >= self.large:
            msg = f'medium ({self.medium}s) must be less than large ({self.large}s)'
            raise ValueError(msg)
        if self.large > self.xlarge:
            msg = f'large ({self.large}s) must be less than or equal to xlarge ({self.xlarge}s)'
            raise ValueError(msg)
        return self

    def get_limit(self, size: TestSize) -> float:
        """Get the time limit for a test size.

        Args:
            size: The test size category.

        Returns:
            The time limit in seconds for the given test size.

        Example:
            >>> config = TimeLimitConfig()
            >>> config.get_limit(TestSize.SMALL)
            1.0

        """
        limits = {
            TestSize.SMALL: self.small,
            TestSize.MEDIUM: self.medium,
            TestSize.LARGE: self.large,
            TestSize.XLARGE: self.xlarge,
        }
        return limits[size]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TimeLimitConfig:
        """Create a TimeLimitConfig from a dictionary.

        Handles type coercion from strings (as from ini files) and
        ignores unknown keys. Uses defaults for missing values.

        Args:
            data: Dictionary with time limit values. Keys can be
                'small', 'medium', 'large', 'xlarge'. Values can be
                int, float, or string representations of numbers.

        Returns:
            A new TimeLimitConfig instance.

        Example:
            >>> TimeLimitConfig.from_dict({'small': '2.0', 'medium': 600})
            TimeLimitConfig(small=2.0, medium=600.0, large=900.0, xlarge=900.0)

        """
        valid_keys = {'small', 'medium', 'large', 'xlarge'}
        filtered = {}
        for key, value in data.items():
            if key in valid_keys:
                filtered[key] = float(value)
        return cls(**filtered)


# Default configuration matching Google's test size definitions
DEFAULT_TIME_LIMIT_CONFIG = TimeLimitConfig()

SMALL_LIMIT = TimeLimit(limit=1.0)
MEDIUM_LIMIT = TimeLimit(limit=300.0)
LARGE_LIMIT = TimeLimit(limit=900.0)
XLARGE_LIMIT = TimeLimit(limit=900.0)

# Mapping of test sizes to their limits
TIME_LIMITS = {
    TestSize.SMALL: SMALL_LIMIT,
    TestSize.MEDIUM: MEDIUM_LIMIT,
    TestSize.LARGE: LARGE_LIMIT,
    TestSize.XLARGE: XLARGE_LIMIT,
}


def get_limit(size: TestSize) -> TimeLimit:
    """Get the time limit for a test size.

    Note: This function uses the hardcoded TIME_LIMITS mapping and is
    kept for backward compatibility. For configurable limits, use
    TimeLimitConfig.get_limit() instead.
    """
    return TIME_LIMITS[size]


def validate(size: TestSize, duration: float, config: TimeLimitConfig | None = None) -> None:
    """Validate a test's duration against its size's limit.

    Args:
        size: The test size category.
        duration: The actual test duration.
        config: Optional time limit configuration. If None, uses
            DEFAULT_TIME_LIMIT_CONFIG.

    Raises:
        TimingViolationError: If the test exceeds its time limit.

    Example:
        >>> validate(TestSize.SMALL, 0.5)  # Uses default 1s limit
        >>> validate(TestSize.SMALL, 2.0, config=TimeLimitConfig(small=5.0))  # Uses custom 5s limit

    """
    effective_config = config if config is not None else DEFAULT_TIME_LIMIT_CONFIG
    limit = effective_config.get_limit(size)
    if duration > limit:
        msg = f'{size.name} test exceeded time limit of {limit:.1f} seconds (took {duration:.1f} seconds)'
        raise TimingViolationError(msg)
