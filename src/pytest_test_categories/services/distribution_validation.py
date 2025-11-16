"""Distribution validation service for test suite composition.

This module provides the DistributionValidationService that validates test
suite distribution against target percentages. It follows hexagonal architecture
by depending on abstract ports rather than concrete pytest implementations.

The service encapsulates the logic for:
- Validating distribution stats against targets
- Emitting warnings when distribution is out of spec
- Providing formatted warning messages

This is pure domain logic that can be tested without pytest.

Example:
    >>> from pytest_test_categories.distribution.stats import DistributionStats
    >>> from tests._fixtures.warning_system import FakeWarningSystem
    >>> service = DistributionValidationService()
    >>> warning_system = FakeWarningSystem()
    >>> stats = DistributionStats.update_counts({'small': 5, 'large': 5})  # Bad distribution
    >>> service.validate_distribution(stats, warning_system)
    >>> len(warning_system.warnings) > 0  # Should have warnings
    True

"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_test_categories.distribution.stats import DistributionStats
    from pytest_test_categories.types import WarningSystemPort

DISTRIBUTION_WARNING_PREFIX = 'Test distribution does not meet targets: '


class DistributionValidationService:
    """Service for validating test distribution against targets.

    This service encapsulates the logic for validating that the test suite
    distribution meets the target percentages defined in Google's Software
    Engineering at Google book:
    - 80% small tests (±5%)
    - 15% medium tests (±5%)
    - 5% large/xlarge tests (±3%)

    The service delegates to DistributionStats for the actual validation
    logic and emits warnings through the provided WarningSystemPort when
    the distribution is out of spec.

    The service is stateless and thread-safe - all state is passed as parameters.

    Example:
        >>> from pytest_test_categories.distribution.stats import DistributionStats
        >>> from tests._fixtures.warning_system import FakeWarningSystem
        >>> service = DistributionValidationService()
        >>> warning_system = FakeWarningSystem()
        >>> # Good distribution
        >>> stats = DistributionStats.update_counts({'small': 80, 'medium': 15, 'large': 5})
        >>> service.validate_distribution(stats, warning_system)
        >>> len(warning_system.warnings)
        0
        >>> # Bad distribution
        >>> stats = DistributionStats.update_counts({'small': 10, 'large': 90})
        >>> service.validate_distribution(stats, warning_system)
        >>> len(warning_system.warnings)
        1

    """

    def validate_distribution(
        self,
        stats: DistributionStats,
        warning_system: WarningSystemPort,
    ) -> None:
        """Validate test distribution and emit warnings if out of spec.

        Attempts to validate the distribution stats against target percentages.
        If validation fails (raises ValueError), emits a warning through the
        provided warning system.

        Args:
            stats: The distribution stats to validate.
            warning_system: Port for emitting warnings.

        Example:
            >>> service = DistributionValidationService()
            >>> warning_system = FakeWarningSystem()
            >>> # This will emit a warning
            >>> stats = DistributionStats.update_counts({'small': 10, 'large': 90})
            >>> service.validate_distribution(stats, warning_system)
            >>> 'Test distribution does not meet targets' in warning_system.warnings[0]
            True

        """
        try:
            stats.validate_distribution()
        except ValueError as e:
            # Emit warning through the port interface
            warning_message = f'{DISTRIBUTION_WARNING_PREFIX}{e}'
            warning_system.warn(warning_message, category=UserWarning)
