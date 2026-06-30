from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import yaml

if TYPE_CHECKING:
    from collections.abc import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = Path('.github/workflows')
DOCS_DIR = Path('docs')


def _iter_uv_run_pip_audit_commands(text: str) -> Iterable[str]:
    """Yield shell lines that run pip-audit via uv run from a markdown code block."""
    for block in re.finditer(r'```(?:bash|shell|sh|yaml|yml)?\n(.*?)```', text, re.DOTALL):
        for line in block.group(1).splitlines():
            stripped = line.strip()
            if stripped.startswith('uv run') and 'pip-audit' in stripped:
                yield stripped


def _pip_audit_is_project_dependency() -> bool:
    """Return True when pip-audit is declared as a project dependency or group."""
    return 'pip-audit' in (REPO_ROOT / 'pyproject.toml').read_text()


@pytest.mark.medium
def test_manual_audit_documentation_can_run_pip_audit() -> None:
    """Docs that tell users to run `uv run pip-audit` must add it with --with because it is not a project dep."""
    docs = [
        DOCS_DIR / 'deployment.md',
        Path('SECURITY.md'),
    ]

    for doc in docs:
        text = (REPO_ROOT / doc).read_text()
        for command in _iter_uv_run_pip_audit_commands(text):
            assert '--with pip-audit' in command or _pip_audit_is_project_dependency(), (
                f'{doc} documents command {command!r} but pip-audit is not a project dependency; '
                f'use `uv run --with pip-audit ... pip-audit` so the command works on a clean clone'
            )


@pytest.mark.medium
def test_security_workflow_validates_uv_lock_before_export() -> None:
    """The security workflow must scan the committed uv.lock, not silently re-resolve dependencies."""
    workflow_path = REPO_ROOT / WORKFLOWS_DIR / 'security.yml'
    workflow = yaml.safe_load(workflow_path.read_text())

    has_lock_check = False
    export_uses_locked = False
    for job in workflow.get('jobs', {}).values():
        for step in job.get('steps', []):
            run = step.get('run', '')
            if 'uv lock --check' in run:
                has_lock_check = True
            if 'uv export' in run and '--locked' in run:
                export_uses_locked = True

    assert has_lock_check or export_uses_locked, (
        'Security workflow must run `uv lock --check` or `uv export --locked` '
        'before scanning so it audits the committed lock file'
    )
