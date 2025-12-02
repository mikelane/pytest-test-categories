"""Time limit definitions and validation for test categories.

Test sizes are DEFINITIONS, not configurable options. This follows Google's
"Software Engineering at Google" philosophy where test sizes have fixed
meanings:

- Small tests (< 1s): Fast unit tests without external dependencies
- Medium tests (< 5 min): Integration tests with local services
- Large tests (< 15 min): Full system/E2E tests
- XLarge tests (< 15 min): Extended tests with same limits as large

If a test exceeds its category's time limit, the correct action is to
RECATEGORIZE the test to a larger size, not extend the limit.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from pytest_test_categories.errors import (
    ERROR_CODES,
    format_error_message,
)
from pytest_test_categories.types import TestSize

__all__ = [
    'LARGE_LIMIT',
    'MEDIUM_LIMIT',
    'SMALL_LIMIT',
    'TIME_LIMITS',
    'XLARGE_LIMIT',
    'TimeLimit',
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
    """Fixed time limit for a test size category.

    This is an immutable value object representing a test size's time limit.
    Time limits are fixed definitions based on Google's test size standards,
    not configurable options.
    """

    limit: Annotated[float, Field(gt=0)]  # Time limit in seconds must be positive

    model_config = ConfigDict(frozen=True)


# Fixed time limits matching Google's test size definitions
# These are DEFINITIONS, not defaults that can be overridden
SMALL_LIMIT = TimeLimit(limit=1.0)
MEDIUM_LIMIT = TimeLimit(limit=300.0)
LARGE_LIMIT = TimeLimit(limit=900.0)
XLARGE_LIMIT = TimeLimit(limit=900.0)

# Mapping of test sizes to their fixed limits
TIME_LIMITS = {
    TestSize.SMALL: SMALL_LIMIT,
    TestSize.MEDIUM: MEDIUM_LIMIT,
    TestSize.LARGE: LARGE_LIMIT,
    TestSize.XLARGE: XLARGE_LIMIT,
}


def get_limit(size: TestSize) -> TimeLimit:
    """Get the fixed time limit for a test size.

    Args:
        size: The test size category.

    Returns:
        The TimeLimit for the given test size.

    Example:
        >>> get_limit(TestSize.SMALL).limit
        1.0
        >>> get_limit(TestSize.MEDIUM).limit
        300.0

    """
    return TIME_LIMITS[size]


def validate(
    size: TestSize,
    duration: float,
    test_nodeid: str = '',
) -> None:
    """Validate a test's duration against its size's fixed time limit.

    Test sizes have fixed time limits that are not configurable. If a test
    exceeds its limit, the correct action is to recategorize the test to
    a larger size, not extend the limit.

    Args:
        size: The test size category.
        duration: The actual test duration in seconds.
        test_nodeid: Optional pytest node ID for enhanced error messages.

    Raises:
        TimingViolationError: If the test exceeds its time limit.

    Example:
        >>> validate(TestSize.SMALL, 0.5)  # Passes (0.5s < 1s limit)
        >>> validate(TestSize.SMALL, 2.0)  # Raises TimingViolationError
        >>> validate(TestSize.SMALL, 2.0, test_nodeid='tests/test_slow.py::test_compute')

    """
    limit = get_limit(size).limit
    if duration > limit:
        raise TimingViolationError(
            test_size=size,
            test_nodeid=test_nodeid,
            limit=limit,
            actual=duration,
        )
