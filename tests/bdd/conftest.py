"""Pytest configuration for BDD tests.

This module configures pytest-bdd for the enforcement feature tests.
It provides shared fixtures used across all BDD scenarios.

The BDD tests validate the hermeticity enforcement features implemented
in issues #213-#221. They cover:
- Sleep/time manipulation detection (#213)
- Subprocess spawn detection (#214)
- Threading constraint detection (#215)
- Filesystem I/O detection (#216)
- Network access enforcement (#217)
- Configuration system (#218)
- CLI flags and pytest options (#219)
- Error messages with remediation guidance (#220)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


# NOTE: BDD tests are no longer skipped - enforcement features are now implemented.
# The hook below was removed after completing issues #213-#221.


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
