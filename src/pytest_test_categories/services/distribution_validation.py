"""Distribution validation service for test suite composition.

This module provides the DistributionValidationService that validates test
suite distribution against target percentages. It follows hexagonal architecture
by depending on abstract ports rather than concrete pytest implementations.

The service encapsulates the logic for:
- Validating distribution stats against targets
- Emitting warnings when distribution is out of spec (WARN mode)
- Failing the build when distribution is outside acceptable range (STRICT mode)
- Providing formatted error/warning messages with actionable guidance

This is pure domain logic that can be tested without pytest.

Example:
    >>> from pytest_test_categories.distribution.stats import DistributionStats
    >>> from pytest_test_categories.ports.network import EnforcementMode
    >>> from tests._fixtures.warning_system import FakeWarningSystem
    >>> service = DistributionValidationService()
    >>> warning_system = FakeWarningSystem()
    >>> stats = DistributionStats.update_counts({'small': 5, 'large': 5})  # Bad distribution
    >>> service.validate_distribution(stats, warning_system, EnforcementMode.WARN)
    >>> len(warning_system.warnings) > 0  # Should have warnings
    True

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytest_test_categories.ports.network import EnforcementMode

if TYPE_CHECKING:
    from pytest_test_categories.distribution.stats import DistributionStats
    from pytest_test_categories.types import WarningSystemPort

DISTRIBUTION_WARNING_PREFIX = 'Test distribution does not meet targets: '


class DistributionViolationError(Exception):
    """Exception raised when distribution enforcement fails in strict mode.

    This exception is raised during test collection when the distribution
    of test sizes violates the configured thresholds and enforcement mode
    is set to STRICT.

    The error message includes:
    - Current distribution percentages
    - Target ranges for each size category
    - Actionable guidance for improving distribution
    - Instructions to bypass enforcement if needed

    Example:
        >>> raise DistributionViolationError(
        ...     "Distribution violation: Small tests at 50% (target: 75-85%)"
        ... )

    """


class DistributionValidationService:
    """Service for validating test distribution against targets.

    This service encapsulates the logic for validating that the test suite
    distribution meets the target percentages defined in Google's Software
    Engineering at Google book:
    - 80% small tests (+/-5%)
    - 15% medium tests (+/-5%)
    - 5% large/xlarge tests (+/-3%)

    The service supports three enforcement modes:
    - OFF: Skip validation entirely (silent operation)
    - WARN: Emit warnings but allow build to continue (default for backwards compatibility)
    - STRICT: Fail immediately if distribution is outside acceptable range

    The service delegates to DistributionStats for the actual validation
    logic and either emits warnings or raises DistributionViolationError
    depending on the enforcement mode.

    The service is stateless and thread-safe - all state is passed as parameters.

    Example:
        >>> from pytest_test_categories.distribution.stats import DistributionStats
        >>> from pytest_test_categories.ports.network import EnforcementMode
        >>> from tests._fixtures.warning_system import FakeWarningSystem
        >>> service = DistributionValidationService()
        >>> warning_system = FakeWarningSystem()
        >>> # Good distribution
        >>> stats = DistributionStats.update_counts({'small': 80, 'medium': 15, 'large': 5})
        >>> service.validate_distribution(stats, warning_system, EnforcementMode.STRICT)
        >>> # No exception raised
        >>> # Bad distribution in WARN mode
        >>> stats = DistributionStats.update_counts({'small': 10, 'large': 90})
        >>> service.validate_distribution(stats, warning_system, EnforcementMode.WARN)
        >>> len(warning_system.get_warnings())
        1

    """

    def validate_distribution(
        self,
        stats: DistributionStats,
        warning_system: WarningSystemPort,
        enforcement_mode: EnforcementMode = EnforcementMode.WARN,
    ) -> None:
        """Validate test distribution based on enforcement mode.

        Behavior varies by enforcement mode:
        - OFF: Skip validation entirely, no warnings or errors
        - WARN: Emit warning if out of spec, allow build to continue
        - STRICT: Raise DistributionViolationError if out of spec

        Args:
            stats: The distribution stats to validate.
            warning_system: Port for emitting warnings.
            enforcement_mode: How to handle validation failures. Defaults to WARN
                for backwards compatibility with existing behavior.

        Raises:
            DistributionViolationError: If enforcement_mode is STRICT and
                distribution is outside acceptable range.

        Example:
            >>> service = DistributionValidationService()
            >>> warning_system = FakeWarningSystem()
            >>> # STRICT mode raises on bad distribution
            >>> stats = DistributionStats.update_counts({'small': 10, 'large': 90})
            >>> service.validate_distribution(stats, warning_system, EnforcementMode.STRICT)
            DistributionViolationError: Distribution violation...

        """
        if enforcement_mode == EnforcementMode.OFF:
            return

        try:
            stats.validate_distribution()
        except ValueError as e:
            if enforcement_mode == EnforcementMode.STRICT:
                error_message = self._format_violation_error(stats, str(e))
                raise DistributionViolationError(error_message) from e

            warning_message = f'{DISTRIBUTION_WARNING_PREFIX}{e}'
            warning_system.warn(warning_message)

    def _format_violation_error(self, stats: DistributionStats, original_error: str) -> str:
        """Format a detailed error message for distribution violations.

        Creates a comprehensive error message that includes:
        - The violation header
        - Current distribution percentages
        - Target ranges
        - The original validation error
        - Actionable recommendations
        - Bypass instructions

        Args:
            stats: The distribution stats that failed validation.
            original_error: The original error message from validate_distribution().

        Returns:
            A formatted error message string.

        """
        percentages = stats.calculate_percentages()

        lines = [
            'Distribution violation: Test pyramid requirements not met',
            '',
            'Current Distribution:',
            f'  Small:        {percentages.small:5.1f}% (target: 80% +/-5%)',
            f'  Medium:       {percentages.medium:5.1f}% (target: 15% +/-5%)',
            f'  Large/XLarge: {percentages.large + percentages.xlarge:5.1f}% (target: 5% +/-3%)',
            '',
            f'Validation Error: {original_error}',
            '',
            'Recommendations:',
            '  - Convert medium tests to small tests (mock external dependencies)',
            '  - Convert large tests to medium tests (use localhost services)',
            '  - See docs for guidance on test categorization',
            '',
            'To bypass: pytest --test-categories-distribution-enforcement=off',
        ]

        return '\n'.join(lines)
