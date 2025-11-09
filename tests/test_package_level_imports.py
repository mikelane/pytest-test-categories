"""Tests that exercise package-level imports to ensure __init__.py coverage.

This module ensures that __init__.py files are executed under coverage tracking
by reloading the package modules after coverage has started.
"""

from __future__ import annotations

import importlib
import sys

import pytest


@pytest.mark.small
def it_covers_main_package_init() -> None:
    """Reload main package __init__.py to ensure coverage tracking."""
    # Reload the main package __init__.py to execute it under coverage
    if 'pytest_test_categories' in sys.modules:
        import pytest_test_categories  # noqa: PLC0415

        importlib.reload(pytest_test_categories)

    # Import public exports to verify they're accessible
    from pytest_test_categories import (  # noqa: PLC0415
        DistributionStats,
        PluginState,
        TestPercentages,
        TestSize,
        TestSizeReport,
        TestTimer,
        TimerState,
        TimingViolationError,
        WallTimer,
        pytest_addoption,
        pytest_collection_finish,
        pytest_collection_modifyitems,
        pytest_configure,
        pytest_runtest_makereport,
        pytest_runtest_protocol,
        pytest_terminal_summary,
    )

    # Verify all imports are not None
    assert TestSize is not None
    assert TestTimer is not None
    assert TimerState is not None
    assert TimingViolationError is not None
    assert WallTimer is not None
    assert PluginState is not None
    assert TestSizeReport is not None
    assert pytest_addoption is not None
    assert pytest_configure is not None
    assert pytest_collection_modifyitems is not None
    assert pytest_collection_finish is not None
    assert pytest_runtest_protocol is not None
    assert pytest_runtest_makereport is not None
    assert pytest_terminal_summary is not None
    assert DistributionStats is not None
    assert TestPercentages is not None


@pytest.mark.small
def it_covers_distribution_subpackage_init() -> None:
    """Reload distribution subpackage __init__.py to ensure coverage tracking."""
    # Reload the distribution subpackage __init__.py to execute it under coverage
    if 'pytest_test_categories.distribution' in sys.modules:
        import pytest_test_categories.distribution  # noqa: PLC0415

        importlib.reload(pytest_test_categories.distribution)

    # Import public exports to verify they're accessible
    from pytest_test_categories.distribution import (  # noqa: PLC0415
        DistributionRange,
        DistributionStats,
        TestCounts,
        TestPercentages,
    )

    # Verify all imports are not None
    assert DistributionStats is not None
    assert DistributionRange is not None
    assert TestCounts is not None
    assert TestPercentages is not None
