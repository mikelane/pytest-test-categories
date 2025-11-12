"""Tests for FakeCoverageReader test adapter."""

from __future__ import annotations

import pytest

from pytest_test_categories.coverage.readers import FakeCoverageReader


@pytest.mark.small
class DescribeFakeCoverageReader:
    """Tests for the FakeCoverageReader test adapter."""

    def it_returns_default_coverage_of_zero(self) -> None:
        """FakeCoverageReader returns 0.0 coverage by default."""
        reader = FakeCoverageReader()
        assert reader.get_total_coverage() == 0.0

    def it_returns_configured_coverage_value(self) -> None:
        """FakeCoverageReader returns the configured coverage value."""
        reader = FakeCoverageReader(coverage=85.5)
        assert reader.get_total_coverage() == 85.5

    def it_allows_updating_coverage_value(self) -> None:
        """FakeCoverageReader allows updating coverage after instantiation."""
        reader = FakeCoverageReader(coverage=50.0)
        assert reader.get_total_coverage() == 50.0

        reader.coverage = 75.0
        assert reader.get_total_coverage() == 75.0

    def it_accepts_coverage_values_from_zero_to_hundred(self) -> None:
        """FakeCoverageReader accepts valid coverage percentages (0-100)."""
        reader_zero = FakeCoverageReader(coverage=0.0)
        assert reader_zero.get_total_coverage() == 0.0

        reader_hundred = FakeCoverageReader(coverage=100.0)
        assert reader_hundred.get_total_coverage() == 100.0

        reader_partial = FakeCoverageReader(coverage=42.7)
        assert reader_partial.get_total_coverage() == 42.7

    def it_is_deterministic_and_repeatable(self) -> None:
        """FakeCoverageReader returns the same value on multiple calls."""
        reader = FakeCoverageReader(coverage=90.0)
        assert reader.get_total_coverage() == 90.0
        assert reader.get_total_coverage() == 90.0
        assert reader.get_total_coverage() == 90.0
