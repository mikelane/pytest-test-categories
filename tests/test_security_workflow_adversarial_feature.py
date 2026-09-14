from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, cast

import pytest
import yaml

if TYPE_CHECKING:
    from collections.abc import Iterator

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR: Final[Path] = REPO_ROOT / '.github/workflows'
DOCS_DIR: Final[Path] = REPO_ROOT / 'docs'


def _iter_uv_run_pip_audit_commands(text: str) -> Iterator[str]:
    """Yield shell lines that run pip-audit via uv run from a markdown code block."""
    for block in re.finditer(r'```(?:bash|shell|sh|yaml|yml)?\n(.*?)```', text, re.DOTALL):
        for line in block.group(1).splitlines():
            stripped = line.strip()
            if stripped.startswith('uv run') and 'pip-audit' in stripped:
                yield stripped


def _pip_audit_is_project_dependency() -> bool:
    """Return True when pip-audit is declared as a project dependency or group."""
    return 'pip-audit' in (REPO_ROOT / 'pyproject.toml').read_text()


def _manual_audit_commands() -> list[tuple[Path, str]]:
    """Return every documented uv-run pip-audit command across security docs."""
    docs = [DOCS_DIR / 'deployment.md', REPO_ROOT / 'SECURITY.md']
    return [(doc, command) for doc in docs for command in _iter_uv_run_pip_audit_commands(doc.read_text())]


@pytest.mark.parametrize(('doc', 'command'), _manual_audit_commands())
@pytest.mark.medium
def test_manual_audit_documentation_can_run_pip_audit(doc: Path, command: str) -> None:
    """Docs that tell users to run `uv run pip-audit` must add it with --with because it is not a project dep."""
    assert '--with pip-audit' in command or _pip_audit_is_project_dependency(), (
        f'{doc} documents command {command!r} but pip-audit is not a project dependency; '
        f'use `uv run --with pip-audit ... pip-audit` so the command works on a clean clone'
    )


def _load_security_workflow() -> dict[str, Any]:
    """Return the parsed security workflow YAML."""
    return cast('dict[str, Any]', yaml.safe_load((WORKFLOWS_DIR / 'security.yml').read_text()))


def _workflow_has_lock_check_and_locked_export(workflow: dict[str, Any]) -> tuple[bool, bool]:
    """Return whether the workflow validates uv.lock and exports with --locked."""
    has_lock_check = False
    export_uses_locked = False
    for job in workflow.get('jobs', {}).values():
        for step in job.get('steps', []):
            run = step.get('run', '')
            if 'uv lock --check' in run:
                has_lock_check = True
            if 'uv export' in run and '--locked' in run:
                export_uses_locked = True
    return has_lock_check, export_uses_locked


@pytest.mark.medium
def test_security_workflow_validates_uv_lock_before_export() -> None:
    """The security workflow must scan the committed uv.lock, not silently re-resolve dependencies."""
    has_lock_check, export_uses_locked = _workflow_has_lock_check_and_locked_export(_load_security_workflow())
    assert has_lock_check or export_uses_locked, (
        'Security workflow must run `uv lock --check` or `uv export --locked` '
        'before scanning so it audits the committed lock file'
    )


def _job_lock_check_and_export_indices(job: dict[str, Any]) -> tuple[int | None, int | None]:
    """Return the first indices of uv lock check and locked export within a single job."""
    lock_check_index: int | None = None
    export_index: int | None = None
    for index, step in enumerate(job.get('steps', [])):
        run = step.get('run', '')
        if 'uv lock --check' in run and lock_check_index is None:
            lock_check_index = index
        if 'uv export' in run and '--locked' in run and export_index is None:
            export_index = index
    return lock_check_index, export_index


def _jobs_with_lock_and_export(workflow: dict[str, Any]) -> list[tuple[str, int, int]]:
    """Return job names with the indices of their lock check and locked export steps."""
    result: list[tuple[str, int, int]] = []
    for job_name, job in workflow.get('jobs', {}).items():
        lock_index, export_index = _job_lock_check_and_export_indices(job)
        if lock_index is not None and export_index is not None:
            result.append((cast('str', job_name), lock_index, export_index))
    return result


@pytest.mark.medium
def test_security_workflow_has_lock_check_and_export_pair() -> None:
    """The security workflow must have at least one job that validates and exports uv dependencies."""
    jobs = _jobs_with_lock_and_export(_load_security_workflow())
    assert jobs, 'Security workflow must have at least one job that runs `uv lock --check` before `uv export --locked`'


@pytest.mark.parametrize(
    ('job_name', 'lock_index', 'export_index'), _jobs_with_lock_and_export(_load_security_workflow())
)
@pytest.mark.medium
def test_security_workflow_lock_check_precedes_export(job_name: str, lock_index: int, export_index: int) -> None:
    """The lock validity check must run before dependency export within every job that does both."""
    assert lock_index < export_index, (
        f'Job "{job_name}": `uv lock --check` must run before `uv export --locked` so stale locks fail fast'
    )


def _pip_audit_versions_and_unpinned(workflow: dict[str, Any]) -> tuple[set[str], list[tuple[str, str, str]]]:
    """Return the set of pinned pip-audit versions and any unpinned invocations."""
    versions: set[str] = set()
    unpinned: list[tuple[str, str, str]] = []
    for job_name, job in workflow.get('jobs', {}).items():
        for step in job.get('steps', []):
            run = step.get('run', '')
            for line in run.splitlines():
                if 'pip-audit' in line and '--with' in line:
                    match = re.search(r"pip-audit==([^\s']+)", line)
                    if match is None:
                        unpinned.append((job_name, step.get('name', ''), line))
                    else:
                        versions.add(match.group(1))
    return versions, unpinned


@pytest.mark.medium
def test_security_workflow_pins_pip_audit_version() -> None:
    """All pip-audit invocations in the security workflow must use the same pinned version."""
    versions, unpinned = _pip_audit_versions_and_unpinned(_load_security_workflow())
    assert unpinned == [], f'Unpinned pip-audit invocations: {unpinned!r}; pin pip-audit==X.Y.Z'
    assert len(versions) == 1, (
        f'Security workflow uses inconsistent pip-audit versions: {sorted(versions)}; '
        f'pin a single version to ensure reproducible scans'
    )


def _find_production_scan_step(workflow: dict[str, Any]) -> dict[str, Any] | None:
    """Return the production dependency scan step, if present."""
    for job in workflow.get('jobs', {}).values():
        for step in job.get('steps', []):
            name = step.get('name', '')
            run = step.get('run', '')
            if 'Scan production dependencies' in name or (
                'pip-audit' in run and '--requirement=requirements.txt' in run and '--format' not in run
            ):
                return cast('dict[str, Any]', step)
    return None


@pytest.mark.medium
def test_security_workflow_production_scan_is_hard_gate() -> None:
    """The production dependency scan must fail the workflow when vulnerabilities are found."""
    step = _find_production_scan_step(_load_security_workflow())
    assert step is not None, 'Production dependency scan step not found'
    assert step.get('continue-on-error') is not True, (
        'Production dependency scan must be a hard gate; remove continue-on-error'
    )


def _find_dev_scan_step(workflow: dict[str, Any]) -> dict[str, Any] | None:
    """Return the development dependency scan step, if present."""
    for job in workflow.get('jobs', {}).values():
        for step in job.get('steps', []):
            if 'Scan development dependencies' in step.get('name', ''):
                return cast('dict[str, Any]', step)
    return None


@pytest.mark.medium
def test_security_workflow_dev_scan_is_non_blocking() -> None:
    """The development dependency scan must report without blocking the workflow."""
    step = _find_dev_scan_step(_load_security_workflow())
    assert step is not None, 'Development dependency scan step not found'
    assert step.get('continue-on-error') is True, (
        'Development dependency scan must be non-blocking; add continue-on-error: true'
    )


@pytest.mark.medium
def test_security_workflow_does_not_mask_failures() -> None:
    """The security workflow must not use `|| true` to mask command failures."""
    workflow_text = (WORKFLOWS_DIR / 'security.yml').read_text()
    assert '|| true' not in workflow_text, (
        'Security workflow uses `|| true` which silently masks failures; '
        'use continue-on-error or explicit conditionals instead'
    )


def _report_outputs(workflow: dict[str, Any]) -> list[str]:
    """Return all --output filenames produced by pip-audit in the workflow."""
    report_outputs: list[str] = []
    for job in workflow.get('jobs', {}).values():
        for step in job.get('steps', []):
            run = step.get('run', '')
            if 'pip-audit' in run and '--output=' in run:
                report_outputs.extend(match.group(1) for match in re.finditer(r'--output=([^\s]+)', run))
    return report_outputs


def _artifact_upload_glob(workflow: dict[str, Any]) -> str | None:
    """Return the artifact upload path glob, if present."""
    for job in workflow.get('jobs', {}).values():
        for step in job.get('steps', []):
            if step.get('uses', '').startswith('actions/upload-artifact'):
                return cast('str | None', step.get('with', {}).get('path'))
    return None


@pytest.mark.medium
def test_security_workflow_artifact_upload_uses_glob() -> None:
    """The artifact upload path must contain a wildcard to match JSON report filenames."""
    workflow = _load_security_workflow()
    upload_glob = _artifact_upload_glob(workflow)
    report_outputs = _report_outputs(workflow)
    assert upload_glob is not None, 'Artifact upload step not found'
    assert '*' in upload_glob, (
        f'Artifact upload glob {upload_glob!r} has no wildcard; cannot match report outputs {report_outputs}'
    )


@pytest.mark.parametrize('output', _report_outputs(_load_security_workflow()))
@pytest.mark.medium
def test_security_workflow_report_output_matches_artifact_glob(output: str) -> None:
    """Each JSON report filename must match the artifact upload glob."""
    upload_glob = _artifact_upload_glob(_load_security_workflow())
    assert upload_glob is not None, 'Artifact upload step not found'
    prefix, suffix = upload_glob.split('*', 1)
    assert output.startswith(prefix), f'Report output {output!r} does not start with artifact glob prefix {prefix!r}'
    assert output.endswith(suffix), f'Report output {output!r} does not end with artifact glob suffix {suffix!r}'
