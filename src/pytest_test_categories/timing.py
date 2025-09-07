"""Time limit configuration and validation for test categories."""

from __future__ import annotations

from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from pytest_test_categories.types import (
    TestSize,
    TimingViolationError,
)


class TimeLimit(BaseModel):
    """Configuration for a test size's time limit in seconds."""

    limit: Annotated[float, Field(gt=0)]  # Time limit in seconds must be positive

    model_config = ConfigDict(frozen=True)


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
    """Get the time limit for a test size."""
    return TIME_LIMITS[size]


def validate(size: TestSize, duration: float) -> None:
    """Validate a test's duration against its size's limit.

    Args:
        size: The test size category.
        duration: The actual test duration.

    Raises:
        TimingViolationError: If the test exceeds its time limit.

    """
    limit = get_limit(size)
    if duration > limit.limit:
        msg = f'{size.name} test exceeded time limit of {limit.limit:.1f} seconds (took {duration:.1f} seconds)'
        raise TimingViolationError(msg)
