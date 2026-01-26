"""Pytest configuration for BDD tests.

This module configures pytest-bdd for the enforcement feature tests.
It provides shared fixtures used across all BDD scenarios.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def test_project_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for test projects.

    This fixture provides an isolated directory where test files
    can be created and pytest can be run via pytester.
    """
    project_dir = tmp_path / 'test_project'
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def enforcement_config() -> dict[str, str | bool | None]:
    """Fixture to hold enforcement configuration state.

    This dictionary is populated by Given steps and consumed by When steps.
    """
    return {
        'mode': None,
        'cli_mode': None,
        'ini_mode': None,
        'quiet': False,
    }


@pytest.fixture
def test_file_content() -> dict[str, str]:
    """Fixture to hold generated test file content.

    This dictionary maps file names to their content.
    """
    return {}


@pytest.fixture
def test_result() -> dict[str, object]:
    """Fixture to hold test execution results.

    This dictionary is populated by When steps and consumed by Then steps.
    """
    return {
        'return_code': None,
        'stdout': '',
        'stderr': '',
        'outcome': None,
    }
