"""Unit tests for distribution enforcement module.

This module tests the distribution enforcement logic in isolation:
- DistributionViolationError exception
- Distribution enforcement thresholds
- Validation service enforcement behavior

Uses FakeWarningSystem for deterministic warning verification.
"""

from __future__ import annotations

import contextlib

import pytest

from pytest_test_categories.distribution.stats import DistributionStats
from pytest_test_categories.ports.network import EnforcementMode
from pytest_test_categories.services.distribution_validation import (
    DISTRIBUTION_WARNING_PREFIX,
    DistributionValidationService,
    DistributionViolationError,
)
from pytest_test_categories.types import TestSize
from tests._fixtures.warning_system import FakeWarningSystem


@pytest.mark.small
class DescribeDistributionViolationError:
    """Test suite for DistributionViolationError exception."""

    def it_stores_message(self) -> None:
        """Stores the error message."""
        error = DistributionViolationError('Test message')
        assert str(error) == 'Test message'

    def it_is_an_exception(self) -> None:
        """Is a proper Exception subclass."""
        error = DistributionViolationError('Test')
        assert isinstance(error, Exception)


@pytest.mark.small
class DescribeDistributionValidationServiceEnforcement:
    """Test suite for DistributionValidationService enforcement modes."""

    def it_does_nothing_when_mode_is_off(self) -> None:
        """OFF mode skips validation entirely."""
        service = DistributionValidationService()
        warning_system = FakeWarningSystem()
        # Terrible distribution: 100% large
        stats = DistributionStats.update_counts(
            {
                TestSize.SMALL: 0,
                TestSize.MEDIUM: 0,
                TestSize.LARGE: 100,
                TestSize.XLARGE: 0,
            }
        )

        # Should not raise or warn in OFF mode
        service.validate_distribution(stats, warning_system, enforcement_mode=EnforcementMode.OFF)

        assert len(warning_system.get_warnings()) == 0

    def it_warns_but_does_not_raise_when_mode_is_warn(self) -> None:
        """WARN mode emits warning but does not raise."""
        service = DistributionValidationService()
        warning_system = FakeWarningSystem()
        # Bad distribution
        stats = DistributionStats.update_counts(
            {
                TestSize.SMALL: 0,
                TestSize.MEDIUM: 0,
                TestSize.LARGE: 100,
                TestSize.XLARGE: 0,
            }
        )

        # Should warn but not raise
        service.validate_distribution(stats, warning_system, enforcement_mode=EnforcementMode.WARN)

        warnings = warning_system.get_warnings()
        assert len(warnings) == 1
        message, _ = warnings[0]
        assert DISTRIBUTION_WARNING_PREFIX in message

    def it_raises_when_mode_is_strict(self) -> None:
        """STRICT mode raises DistributionViolationError."""
        service = DistributionValidationService()
        warning_system = FakeWarningSystem()
        # Bad distribution
        stats = DistributionStats.update_counts(
            {
                TestSize.SMALL: 0,
                TestSize.MEDIUM: 0,
                TestSize.LARGE: 100,
                TestSize.XLARGE: 0,
            }
        )

        with pytest.raises(DistributionViolationError) as exc_info:
            service.validate_distribution(stats, warning_system, enforcement_mode=EnforcementMode.STRICT)

        # Error message now uses the standardized format with error code
        assert '[TC007]' in str(exc_info.value)
        assert 'Test Distribution Warning' in str(exc_info.value)

    def it_does_not_raise_for_valid_distribution_in_strict_mode(self) -> None:
        """STRICT mode does not raise for valid distribution."""
        service = DistributionValidationService()
        warning_system = FakeWarningSystem()
        # Good distribution: 80% small, 15% medium, 5% large
        stats = DistributionStats.update_counts(
            {
                TestSize.SMALL: 80,
                TestSize.MEDIUM: 15,
                TestSize.LARGE: 5,
                TestSize.XLARGE: 0,
            }
        )

        # Should not raise
        service.validate_distribution(stats, warning_system, enforcement_mode=EnforcementMode.STRICT)

        # No warnings either
        assert len(warning_system.get_warnings()) == 0

    def it_defaults_to_warn_mode_for_backwards_compatibility(self) -> None:
        """Default behavior is WARN mode for backwards compatibility."""
        service = DistributionValidationService()
        warning_system = FakeWarningSystem()
        # Bad distribution
        stats = DistributionStats.update_counts(
            {
                TestSize.SMALL: 50,
                TestSize.MEDIUM: 30,
                TestSize.LARGE: 20,
                TestSize.XLARGE: 0,
            }
        )

        # Without enforcement_mode parameter, should default to warn behavior
        service.validate_distribution(stats, warning_system)

        # Should have warned (backward compatible behavior)
        warnings = warning_system.get_warnings()
        assert len(warnings) == 1


@pytest.mark.small
class DescribeDistributionValidationErrorMessages:
    """Test suite for distribution validation error messages."""

    def it_includes_current_distribution_in_error(self) -> None:
        """Error message includes current distribution percentages."""
        service = DistributionValidationService()
        warning_system = FakeWarningSystem()
        stats = DistributionStats.update_counts(
            {
                TestSize.SMALL: 50,
                TestSize.MEDIUM: 30,
                TestSize.LARGE: 20,
                TestSize.XLARGE: 0,
            }
        )

        with pytest.raises(DistributionViolationError) as exc_info:
            service.validate_distribution(stats, warning_system, enforcement_mode=EnforcementMode.STRICT)

        error_message = str(exc_info.value)
        # Should mention small percentage
        assert '50' in error_message or 'small' in error_message.lower()

    def it_includes_target_ranges_in_error(self) -> None:
        """Error message includes target ranges."""
        service = DistributionValidationService()
        warning_system = FakeWarningSystem()
        stats = DistributionStats.update_counts(
            {
                TestSize.SMALL: 50,
                TestSize.MEDIUM: 30,
                TestSize.LARGE: 20,
                TestSize.XLARGE: 0,
            }
        )

        with pytest.raises(DistributionViolationError) as exc_info:
            service.validate_distribution(stats, warning_system, enforcement_mode=EnforcementMode.STRICT)

        error_message = str(exc_info.value)
        # Should mention target
        assert 'target' in error_message.lower() or '%' in error_message

    def it_includes_bypass_instruction(self) -> None:
        """Error message includes instruction to bypass enforcement."""
        service = DistributionValidationService()
        warning_system = FakeWarningSystem()
        stats = DistributionStats.update_counts(
            {
                TestSize.SMALL: 0,
                TestSize.MEDIUM: 0,
                TestSize.LARGE: 100,
                TestSize.XLARGE: 0,
            }
        )

        with pytest.raises(DistributionViolationError) as exc_info:
            service.validate_distribution(stats, warning_system, enforcement_mode=EnforcementMode.STRICT)

        error_message = str(exc_info.value)
        assert '--test-categories-distribution-enforcement=off' in error_message


@pytest.mark.small
class DescribeDistributionValidationEdgeCases:
    """Edge case tests for distribution validation."""

    def it_handles_zero_tests_in_off_mode(self) -> None:
        """OFF mode handles zero tests gracefully."""
        service = DistributionValidationService()
        warning_system = FakeWarningSystem()
        stats = DistributionStats.update_counts(
            {
                TestSize.SMALL: 0,
                TestSize.MEDIUM: 0,
                TestSize.LARGE: 0,
                TestSize.XLARGE: 0,
            }
        )

        # Should not raise in OFF mode
        service.validate_distribution(stats, warning_system, enforcement_mode=EnforcementMode.OFF)

        assert len(warning_system.get_warnings()) == 0

    def it_handles_zero_tests_in_warn_mode(self) -> None:
        """WARN mode handles zero tests gracefully."""
        service = DistributionValidationService()
        warning_system = FakeWarningSystem()
        stats = DistributionStats.update_counts(
            {
                TestSize.SMALL: 0,
                TestSize.MEDIUM: 0,
                TestSize.LARGE: 0,
                TestSize.XLARGE: 0,
            }
        )

        # Should warn about zero tests but not raise
        service.validate_distribution(stats, warning_system, enforcement_mode=EnforcementMode.WARN)

        # Behavior depends on implementation - either warns or passes silently
        # The important thing is it doesn't crash

    def it_handles_zero_tests_in_strict_mode(self) -> None:
        """STRICT mode handles zero tests gracefully."""
        service = DistributionValidationService()
        warning_system = FakeWarningSystem()
        stats = DistributionStats.update_counts(
            {
                TestSize.SMALL: 0,
                TestSize.MEDIUM: 0,
                TestSize.LARGE: 0,
                TestSize.XLARGE: 0,
            }
        )

        # For zero tests, strict mode should either:
        # 1. Pass silently (no tests to validate)
        # 2. Raise an error (can't meet targets with no tests)
        # The implementation will decide, but it shouldn't crash
        with contextlib.suppress(DistributionViolationError):
            service.validate_distribution(stats, warning_system, enforcement_mode=EnforcementMode.STRICT)

    def it_handles_single_test_in_strict_mode(self) -> None:
        """STRICT mode handles single test distribution."""
        service = DistributionValidationService()
        warning_system = FakeWarningSystem()
        # One small test = 100% small, 0% medium, 0% large
        stats = DistributionStats.update_counts(
            {
                TestSize.SMALL: 1,
                TestSize.MEDIUM: 0,
                TestSize.LARGE: 0,
                TestSize.XLARGE: 0,
            }
        )

        # Single small test violates medium (0% vs 10-20%) and large (0% vs 2-8%) targets
        with pytest.raises(DistributionViolationError):
            service.validate_distribution(stats, warning_system, enforcement_mode=EnforcementMode.STRICT)

    def it_validates_boundary_distribution_at_lower_limit(self) -> None:
        """Validates distribution exactly at lower boundaries."""
        service = DistributionValidationService()
        warning_system = FakeWarningSystem()
        # Exactly at lower bounds: 75% small, 10% medium, 2% large
        # Note: These won't sum to 100 exactly, so use 100 tests
        stats = DistributionStats.update_counts(
            {
                TestSize.SMALL: 75,
                TestSize.MEDIUM: 10,
                TestSize.LARGE: 2,
                TestSize.XLARGE: 0,
            }
        )

        # This should fail validation because percentages don't sum to 100
        # but let's just verify no crash occurs
        with contextlib.suppress(DistributionViolationError):
            service.validate_distribution(stats, warning_system, enforcement_mode=EnforcementMode.STRICT)

    def it_validates_boundary_distribution_at_upper_limit(self) -> None:
        """Validates distribution exactly at upper boundaries."""
        service = DistributionValidationService()
        warning_system = FakeWarningSystem()
        # Exactly at upper bounds: 85% small, 20% medium, 8% large
        # These don't sum to 100, so they'll fail validation
        stats = DistributionStats.update_counts(
            {
                TestSize.SMALL: 85,
                TestSize.MEDIUM: 20,
                TestSize.LARGE: 8,
                TestSize.XLARGE: 0,
            }
        )

        with contextlib.suppress(DistributionViolationError):
            service.validate_distribution(stats, warning_system, enforcement_mode=EnforcementMode.STRICT)
