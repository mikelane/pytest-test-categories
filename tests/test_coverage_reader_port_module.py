"""Tests for CoverageReaderPort interface."""

from __future__ import annotations

import pytest

from pytest_test_categories.types import CoverageReaderPort


@pytest.mark.small
class DescribeCoverageReaderPort:
    """Tests for the CoverageReaderPort abstract interface."""

    def it_requires_get_total_coverage_method(self) -> None:
        """CoverageReaderPort cannot be instantiated without get_total_coverage implementation."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            CoverageReaderPort()  # type: ignore[abstract]

    def it_defines_get_total_coverage_abstract_method(self) -> None:
        """CoverageReaderPort has get_total_coverage as abstract method."""
        assert hasattr(CoverageReaderPort, 'get_total_coverage')
        assert CoverageReaderPort.get_total_coverage.__isabstractmethod__
