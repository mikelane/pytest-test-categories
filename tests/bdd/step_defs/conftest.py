"""Shared fixtures for BDD step definitions.

This module provides the pytest-bdd fixtures and shared state
used across all enforcement scenarios.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from _pytest.pytester import Pytester


@dataclass
class EnforcementContext:
    """Context object holding state across BDD steps.

    This dataclass captures the test setup and results for verification
    in Then steps.
    """

    # Configuration
    enforcement_mode: str | None = None
    cli_enforcement_mode: str | None = None
    ini_enforcement_mode: str | None = None
    quiet_mode: bool = False

    # Test file content
    test_files: dict[str, str] = field(default_factory=dict)

    # Execution results
    return_code: int | None = None
    stdout: str = ''
    stderr: str = ''

    @property
    def output(self) -> str:
        """Combined stdout and stderr for easier assertion."""
        return f'{self.stdout}\n{self.stderr}'

    @property
    def passed(self) -> bool:
        """Check if all tests passed."""
        return self.return_code == 0

    @property
    def failed(self) -> bool:
        """Check if any tests failed."""
        return self.return_code != 0


@pytest.fixture
def context() -> EnforcementContext:
    """Provide a fresh context for each BDD scenario."""
    return EnforcementContext()


@pytest.fixture
def pytester_with_plugin(pytester: Pytester) -> Pytester:
    """Pytester fixture with the test-categories plugin enabled.

    This fixture ensures the plugin is available in the test subprocess.
    """
    # The plugin is already installed in the test environment
    # via the package installation, so we just need to make sure
    # enforcement is not accidentally configured via conftest
    pytester.makeconftest(
        """
# Empty conftest - configuration will be set by test steps
"""
    )
    return pytester
