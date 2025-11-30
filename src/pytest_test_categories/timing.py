"""Time limit configuration and validation for test categories."""

from __future__ import annotations

from typing import (
    Annotated,
    Self,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from pytest_test_categories.errors import (
    ERROR_CODES,
    format_error_message,
)
from pytest_test_categories.types import TestSize

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


class TimingViolationError(Exception):
    """Exception raised when a test exceeds its time limit.

    This exception is raised when a test's execution time exceeds the
    configured time limit for its size category.

    The error message includes:
    - Error code [TC006]
    - Test identification (nodeid, size category)
    - Timing details (limit vs actual duration)
    - Why timing limits matter
    - Remediation suggestions
    - Documentation link

    Attributes:
        test_size: The test's size category.
        test_nodeid: The pytest node ID of the failing test.
        limit: The time limit in seconds.
        actual: The actual test duration in seconds.

    Example:
        >>> raise TimingViolationError(
        ...     test_size=TestSize.SMALL,
        ...     test_nodeid='tests/test_slow.py::test_compute',
        ...     limit=1.0,
        ...     actual=2.5
        ... )

    """

    def __init__(
        self,
        test_size: TestSize,
        test_nodeid: str,
        limit: float,
        actual: float,
    ) -> None:
        """Initialize a timing violation error.

        Args:
            test_size: The test's size category.
            test_nodeid: The pytest node ID of the failing test.
            limit: The time limit in seconds.
            actual: The actual test duration in seconds.

        """
        self.test_size = test_size
        self.test_nodeid = test_nodeid
        self.limit = limit
        self.actual = actual

        remediation = self._get_remediation(test_size)
        what_happened = f'{test_size.name} test exceeded time limit of {limit:.1f} seconds (took {actual:.1f} seconds)'

        message = format_error_message(
            error_code=ERROR_CODES['timing_violation'],
            what_happened=what_happened,
            remediation=remediation,
            test_nodeid=test_nodeid,
            test_size=test_size.name,
        )
        super().__init__(message)

    @staticmethod
    def _get_remediation(test_size: TestSize) -> list[str]:
        """Get remediation suggestions based on test size.

        Args:
            test_size: The test's size category.

        Returns:
            List of remediation suggestions.

        """
        next_size = {
            TestSize.SMALL: '@pytest.mark.medium',
            TestSize.MEDIUM: '@pytest.mark.large',
            TestSize.LARGE: '@pytest.mark.xlarge',
            TestSize.XLARGE: None,
        }

        suggestions = [
            'Optimize the test to run faster (reduce setup, use fixtures)',
            'Mock slow dependencies (network, filesystem, database)',
            'Split the test into smaller, focused tests',
        ]

        next_marker = next_size.get(test_size)
        if next_marker:
            suggestions.append(f'Change test category to {next_marker} (if more time is genuinely needed)')
        else:
            suggestions.append('Review if this test is doing too much work')

        return suggestions


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


def validate(
    size: TestSize,
    duration: float,
    config: TimeLimitConfig | None = None,
    test_nodeid: str = '',
) -> None:
    """Validate a test's duration against its size's limit.

    Args:
        size: The test size category.
        duration: The actual test duration.
        config: Optional time limit configuration. If None, uses
            DEFAULT_TIME_LIMIT_CONFIG.
        test_nodeid: Optional pytest node ID for enhanced error messages.

    Raises:
        TimingViolationError: If the test exceeds its time limit.

    Example:
        >>> validate(TestSize.SMALL, 0.5)  # Uses default 1s limit
        >>> validate(TestSize.SMALL, 2.0, config=TimeLimitConfig(small=5.0))  # Uses custom 5s limit
        >>> validate(TestSize.SMALL, 2.0, test_nodeid='tests/test_slow.py::test_compute')

    """
    effective_config = config if config is not None else DEFAULT_TIME_LIMIT_CONFIG
    limit = effective_config.get_limit(size)
    if duration > limit:
        raise TimingViolationError(
            test_size=size,
            test_nodeid=test_nodeid,
            limit=limit,
            actual=duration,
        )
