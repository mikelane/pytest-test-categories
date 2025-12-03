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

from pytest_test_categories.errors import ERROR_CODES
from pytest_test_categories.ports.network import EnforcementMode

if TYPE_CHECKING:
    from pytest_test_categories.distribution.config import DistributionConfig
    from pytest_test_categories.distribution.stats import DistributionStats
    from pytest_test_categories.types import WarningSystemPort

# Error code for distribution warnings
_DISTRIBUTION_ERROR_CODE = ERROR_CODES['distribution_warning']

DISTRIBUTION_WARNING_PREFIX = f'[{_DISTRIBUTION_ERROR_CODE.code}] Test distribution does not meet targets: '


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
        config: DistributionConfig | None = None,
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
            config: Optional DistributionConfig with custom targets and tolerances.
                If not provided, uses DEFAULT_DISTRIBUTION_CONFIG.

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
            stats.validate_distribution(config=config)
        except ValueError as e:
            if enforcement_mode == EnforcementMode.STRICT:
                error_message = self._format_violation_error(stats, str(e), config)
                raise DistributionViolationError(error_message) from e

            warning_message = f'{DISTRIBUTION_WARNING_PREFIX}{e}'
            warning_system.warn(warning_message)

    def _format_violation_error(
        self,
        stats: DistributionStats,
        original_error: str,
        config: DistributionConfig | None = None,
    ) -> str:
        """Format a detailed error message for distribution violations.

        Creates a comprehensive error message that includes:
        - Error code for grep-friendly CI log parsing
        - The violation header
        - Current distribution percentages
        - Target ranges (based on provided config or defaults)
        - The original validation error
        - Why distribution matters
        - Actionable recommendations
        - Bypass instructions
        - Documentation link

        Args:
            stats: The distribution stats that failed validation.
            original_error: The original error message from validate_distribution().
            config: Optional DistributionConfig with custom targets and tolerances.
                If not provided, uses DEFAULT_DISTRIBUTION_CONFIG.

        Returns:
            A formatted error message string.

        """
        if config is None:
            from pytest_test_categories.distribution.config import DEFAULT_DISTRIBUTION_CONFIG  # noqa: PLC0415

            effective_config = DEFAULT_DISTRIBUTION_CONFIG
        else:
            effective_config = config

        percentages = stats.calculate_percentages()
        error_code = _DISTRIBUTION_ERROR_CODE

        # Build target range strings from config
        small_range = effective_config.get_small_range()
        medium_range = effective_config.get_medium_range()
        large_range = effective_config.get_large_xlarge_range()

        # Build formatted lines for each category
        small_line = f'  Small:        {percentages.small:5.1f}%'
        small_line += f' (target: {small_range.target:.0f}% +/-{small_range.tolerance:.0f}%)'
        medium_line = f'  Medium:       {percentages.medium:5.1f}%'
        medium_line += f' (target: {medium_range.target:.0f}% +/-{medium_range.tolerance:.0f}%)'
        large_xlarge_pct = percentages.large + percentages.xlarge
        large_line = f'  Large/XLarge: {large_xlarge_pct:5.1f}%'
        large_line += f' (target: {large_range.target:.0f}% +/-{large_range.tolerance:.0f}%)'

        lines = [
            '',
            '=' * 70,
            f'[{error_code.code}] {error_code.title}',
            '=' * 70,
            '',
            'What happened:',
            f'  {original_error}',
            '',
            'Current Distribution:',
            small_line,
            medium_line,
            large_line,
            '',
            'Why it matters:',
            f'  {error_code.why_it_matters}',
            '',
            'To fix this (choose one):',
            '  \u2022 Convert medium tests to small tests (mock external dependencies)',
            '  \u2022 Convert large tests to medium tests (use localhost services)',
            '  \u2022 Split large tests into smaller, focused tests',
            '  \u2022 Use @pytest.mark.small for truly unit-level tests',
            '',
            f'See: {error_code.doc_url}',
            '',
            'To bypass: pytest --test-categories-distribution-enforcement=off',
            '=' * 70,
        ]

        return '\n'.join(lines)
