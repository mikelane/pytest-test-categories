"""Tests for __init__.py modules to ensure imports work correctly."""

from __future__ import annotations

import pytest_test_categories
import pytest_test_categories.distribution
from pytest_test_categories import (
    TestSizeReport,
    get_limit,
    pytest_addoption,
    pytest_collection_modifyitems,
    pytest_configure,
    pytest_terminal_summary,
)
from pytest_test_categories.distribution import (
    DistributionStats,
    TestCounts,
    TestPercentages,
)
from pytest_test_categories.timing import validate
from pytest_test_categories.types import (
    TestSize,
    TimingViolationError,
)


class DescribeMainInitModule:
    """Test the main __init__.py module."""

    def it_can_import_plugin_functions(self) -> None:
        """Test that plugin functions can be imported from main module."""
        assert pytest_addoption is not None
        assert pytest_configure is not None

    def it_can_import_reporting_classes(self) -> None:
        """Test that reporting classes can be imported from main module."""
        assert TestSizeReport is not None

    def it_has_correct_module_docstring(self) -> None:
        """Test that the main module has the expected docstring."""
        assert 'pytest plugin to enforce test timing constraints' in pytest_test_categories.__doc__


class DescribeDistributionInitModule:
    """Test the distribution __init__.py module."""

    def it_can_import_distribution_classes(self) -> None:
        """Test that distribution classes can be imported from distribution module."""
        assert DistributionStats is not None
        assert TestCounts is not None
        assert TestPercentages is not None

    def it_has_correct_module_docstring(self) -> None:
        """Test that the distribution module has the expected docstring."""
        assert 'Distribution analysis' in pytest_test_categories.distribution.__doc__


class DescribeImportCompatibility:
    """Test that imports work as expected for users."""

    def it_allows_importing_from_main_package(self) -> None:
        """Test that users can import from the main package."""
        # Test importing key classes that users might need
        # Verify they are the expected types
        assert TestSizeReport is not None
        assert DistributionStats is not None
        assert TestSize is not None
        assert TimingViolationError is not None

    def it_allows_importing_plugin_hooks(self) -> None:
        """Test that plugin hooks can be imported."""
        # Verify they are callable (functions)
        assert callable(pytest_addoption)
        assert callable(pytest_configure)
        assert callable(pytest_collection_modifyitems)
        assert callable(pytest_terminal_summary)

    def it_provides_access_to_timing_functions(self) -> None:
        """Test that timing functions can be accessed."""
        # Test that they work
        limit = get_limit(TestSize.SMALL)
        assert limit.limit == 1.0

        # Test that validate works (should not raise)
        validate(TestSize.SMALL, 0.5)
