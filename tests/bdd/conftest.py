"""Pytest configuration for BDD tests.

This module configures pytest-bdd for the enforcement feature tests.
It provides shared fixtures used across all BDD scenarios.

NOTE: BDD tests are currently in the "red phase" of TDD. They define
the expected behavior for enforcement features that are not yet implemented.
Once the enforcement features are implemented (issues #213-#221), these
tests will be unskipped and should pass.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Skip all BDD tests - they're in red phase pending enforcement implementation.

    The BDD scenarios define expected behavior for:
    - Sleep/time manipulation detection (#213)
    - Subprocess spawn detection (#214)
    - Threading constraint detection (#215)
    - Filesystem I/O detection (#216)
    - Network access enforcement (#217)
    - Configuration system (#218)
    - CLI flags and pytest options (#219)
    - Error messages with remediation guidance (#220)

    These tests will be unskipped as each enforcement feature is implemented.
    """
    skip_marker = pytest.mark.skip(reason='BDD red phase - enforcement implementation pending (see #212)')
    for item in items:
        # Only skip tests in the bdd directory
        if '/bdd/' in str(item.fspath) or '\\bdd\\' in str(item.fspath):
            item.add_marker(skip_marker)


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
