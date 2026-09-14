"""Test configuration and shared fixtures."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest

pytest_plugins = [
    'pytester',
    'tests._fixtures.timer',
]


def resolve_bash_executable() -> str | None:
    r"""Resolve the bash executable path, preferring Git for Windows on Windows platforms.

    On Windows (sys.platform == 'win32' or os.name == 'nt'), this prefers the known
    Git for Windows bash installation path at C:\Program Files\Git\bin\bash.exe, which
    is the same bash that GitHub Actions' `shell: bash` uses on windows-latest runners.
    Falls back to PATH lookup via shutil.which('bash') on all platforms.

    Returns:
        The path to the bash executable, or None if no usable bash is found.

    """
    if sys.platform == 'win32' or os.name == 'nt':
        # On Windows, prefer Git for Windows' known install location
        git_bash_path = Path('C:/Program Files/Git/bin/bash.exe')
        if git_bash_path.exists() and os.access(str(git_bash_path), os.X_OK):
            return str(git_bash_path)

    # Fall back to PATH lookup on all platforms (or if Git Bash not found on Windows)
    return shutil.which('bash')


@pytest.fixture
def bash_exe() -> str:
    """Fixture that provides the bash executable path, or skips the test if not available.

    This fixture resolves bash using resolve_bash_executable(), which prefers
    Git for Windows on Windows platforms and falls back to PATH lookup elsewhere.
    """
    bash_path = resolve_bash_executable()
    if bash_path is None:
        pytest.skip('no usable bash found on this platform')
    return bash_path
