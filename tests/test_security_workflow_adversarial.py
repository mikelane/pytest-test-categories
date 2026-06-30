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


@pytest.mark.medium
def test_security_workflow_lock_check_precedes_export() -> None:
    """The lock validity check must run before dependency export in the security workflow."""
    workflow_path = REPO_ROOT / WORKFLOWS_DIR / 'security.yml'
    workflow = yaml.safe_load(workflow_path.read_text())

    lock_check_index: int | None = None
    export_index: int | None = None
    for job in workflow.get('jobs', {}).values():
        for index, step in enumerate(job.get('steps', [])):
            run = step.get('run', '')
            if 'uv lock --check' in run and lock_check_index is None:
                lock_check_index = index
            if 'uv export' in run and '--locked' in run and export_index is None:
                export_index = index

    assert lock_check_index is not None, 'Security workflow missing `uv lock --check` step'
    assert export_index is not None, 'Security workflow missing locked `uv export` step'
    assert lock_check_index < export_index, (
        '`uv lock --check` must run before `uv export --locked` so stale locks fail fast'
    )


@pytest.mark.medium
def test_security_workflow_pins_pip_audit_version() -> None:
    """All pip-audit invocations in the security workflow must use the same pinned version."""
    workflow_path = REPO_ROOT / WORKFLOWS_DIR / 'security.yml'
    workflow = yaml.safe_load(workflow_path.read_text())

    versions: set[str] = set()
    for job in workflow.get('jobs', {}).values():
        for step in job.get('steps', []):
            run = step.get('run', '')
            for line in run.splitlines():
                if 'pip-audit' in line and '--with' in line:
                    match = re.search(r'pip-audit==([^\s\']+)', line)
                    assert match is not None, (
                        f'Job "{job.get("name", "")}" step "{step.get("name", "")}" '
                        f'runs pip-audit without a pinned version: {line!r}'
                    )
                    versions.add(match.group(1))

    assert len(versions) == 1, (
        f'Security workflow uses inconsistent pip-audit versions: {sorted(versions)}; '
        f'pin a single version to ensure reproducible scans'
    )


@pytest.mark.medium
def test_security_workflow_production_scan_is_hard_gate() -> None:
    """The production dependency scan must fail the workflow when vulnerabilities are found."""
    workflow_path = REPO_ROOT / WORKFLOWS_DIR / 'security.yml'
    workflow = yaml.safe_load(workflow_path.read_text())

    production_scan_step = None
    for job in workflow.get('jobs', {}).values():
        for step in job.get('steps', []):
            name = step.get('name', '')
            run = step.get('run', '')
            if 'Scan production dependencies' in name or (
                'pip-audit' in run and '--requirement=requirements.txt' in run and '--format' not in run
            ):
                production_scan_step = step
                break
        if production_scan_step is not None:
            break

    assert production_scan_step is not None, 'Production dependency scan step not found'
    assert production_scan_step.get('continue-on-error') is not True, (
        'Production dependency scan must be a hard gate; remove continue-on-error'
    )


@pytest.mark.medium
def test_security_workflow_dev_scan_is_non_blocking() -> None:
    """The development dependency scan must report without blocking the workflow."""
    workflow_path = REPO_ROOT / WORKFLOWS_DIR / 'security.yml'
    workflow = yaml.safe_load(workflow_path.read_text())

    dev_scan_step = None
    for job in workflow.get('jobs', {}).values():
        for step in job.get('steps', []):
            name = step.get('name', '')
            if 'Scan development dependencies' in name:
                dev_scan_step = step
                break
        if dev_scan_step is not None:
            break

    assert dev_scan_step is not None, 'Development dependency scan step not found'
    assert dev_scan_step.get('continue-on-error') is True, (
        'Development dependency scan must be non-blocking; add continue-on-error: true'
    )


@pytest.mark.medium
def test_security_workflow_does_not_mask_failures() -> None:
    """The security workflow must not use `|| true` to mask command failures."""
    workflow_text = (REPO_ROOT / WORKFLOWS_DIR / 'security.yml').read_text()
    assert '|| true' not in workflow_text, (
        'Security workflow uses `|| true` which silently masks failures; '
        'use continue-on-error or explicit conditionals instead'
    )


@pytest.mark.medium
def test_security_workflow_artifact_glob_matches_report_outputs() -> None:
    """The artifact upload glob must match the JSON report filenames produced by pip-audit."""
    workflow_path = REPO_ROOT / WORKFLOWS_DIR / 'security.yml'
    workflow = yaml.safe_load(workflow_path.read_text())

    report_outputs: list[str] = []
    upload_glob: str | None = None
    for job in workflow.get('jobs', {}).values():
        for step in job.get('steps', []):
            run = step.get('run', '')
            if 'pip-audit' in run and '--output=' in run:
                report_outputs.extend(match.group(1) for match in re.finditer(r'--output=([^\s]+)', run))
            if step.get('uses', '').startswith('actions/upload-artifact'):
                upload_glob = step.get('with', {}).get('path')

    assert upload_glob is not None, 'Artifact upload step not found'
    # The glob may contain a single `*` wildcard in the middle.
    assert '*' in upload_glob, (
        f'Artifact upload glob {upload_glob!r} has no wildcard; cannot match report outputs {report_outputs}'
    )
    prefix, suffix = upload_glob.split('*', 1)
    for output in report_outputs:
        assert output.startswith(prefix), (
            f'Report output {output!r} does not start with artifact glob prefix {prefix!r}'
        )
        assert output.endswith(suffix), f'Report output {output!r} does not end with artifact glob suffix {suffix!r}'
