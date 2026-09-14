"""Tests that exercise package-level imports to ensure __init__.py coverage.

This module ensures that __init__.py files are executed under coverage tracking
by reloading the package modules after coverage has started.
"""

from __future__ import annotations

import importlib
import tomllib
from pathlib import Path

import pytest

import pytest_test_categories


@pytest.mark.medium
def it_returns_version_matching_pyproject_toml() -> None:
    """__version__ must track the version declared in pyproject.toml."""
    pyproject_path = Path(__file__).parent.parent / 'pyproject.toml'
    with pyproject_path.open('rb') as pyproject_file:
        pyproject_data = tomllib.load(pyproject_file)

    assert pytest_test_categories.__version__ == pyproject_data['project']['version']


@pytest.mark.medium
def it_covers_main_package_init() -> None:
    """Reload main package __init__.py to ensure coverage tracking."""
    # The module-level `import pytest_test_categories` above guarantees it is
    # already in sys.modules by the time this test runs, so reload it directly
    # using that binding instead of importing it again locally.
    importlib.reload(pytest_test_categories)

    # Import public exports to verify they're accessible
    from pytest_test_categories import (
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


@pytest.mark.medium
def it_covers_distribution_subpackage_init() -> None:
    """Reload distribution subpackage __init__.py to ensure coverage tracking."""
    # Importing `pytest_test_categories` above transitively imports
    # `pytest_test_categories.distribution` (via `__init__.py`'s
    # `from .distribution.stats import ...`), setting it as an attribute of the
    # parent package. Reload it directly using that attribute access.
    importlib.reload(pytest_test_categories.distribution)

    # Import public exports to verify they're accessible
    from pytest_test_categories.distribution import (
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
