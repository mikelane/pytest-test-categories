"""Adversarial test: __version__ must not resolve to an unrelated, stale distribution.

`importlib.metadata.version()` looks up distribution metadata by scanning
`sys.path` for any matching `*.dist-info` directory -- it has no knowledge of
which `pytest_test_categories` module was actually imported. If a stale
installation of this package exists anywhere on `sys.path` (a common
occurrence with multiple git worktrees or environments sharing a Python
installation), `__version__` can silently report that stale distribution's
version even though the code actually executing came from a completely
different, newer checkout.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
SRC = REPO_ROOT / 'src'


@pytest.mark.xfail(
    reason=(
        'Known gap: importlib.metadata.version() can resolve to a stale sys.path '
        'distribution rather than the actually-imported module. Tracked in #263.'
    ),
    strict=True,
)
@pytest.mark.medium
def it_reports_the_version_of_the_code_actually_executing() -> None:
    """__version__ must match the running source tree, not a stale sys.path distribution."""
    with tempfile.TemporaryDirectory() as tmp:
        # Simulate a stale installation of this package elsewhere on sys.path --
        # e.g. an editable install left over in a different worktree's venv,
        # or a previously-synced environment that hasn't been re-synced after
        # a version bump. This directory contains ONLY distribution metadata,
        # not the package's actual code, so it cannot shadow the real module.
        stale_site_packages = Path(tmp) / 'site-packages'
        stale_dist_info = stale_site_packages / 'pytest_test_categories-1.2.1.dist-info'
        stale_dist_info.mkdir(parents=True)
        (stale_dist_info / 'METADATA').write_text(
            'Metadata-Version: 2.1\nName: pytest-test-categories\nVersion: 1.2.1\n',
        )
        (stale_dist_info / 'RECORD').write_text('')
        (stale_dist_info / 'INSTALLER').write_text('pip\n')

        env = dict(os.environ)
        env['PYTHONPATH'] = os.pathsep.join([str(stale_site_packages), str(SRC)])
        env.pop('VIRTUAL_ENV', None)

        result = subprocess.run(  # noqa: S603
            [sys.executable, '-c', 'import pytest_test_categories as p; print(p.__version__)'],
            env=env,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            check=True,
        )

    pyproject_path = REPO_ROOT / 'pyproject.toml'
    with pyproject_path.open('rb') as pyproject_file:
        pyproject_data = tomllib.load(pyproject_file)
    expected_version = pyproject_data['project']['version']

    assert result.stdout.strip() == expected_version
