from __future__ import annotations

from pathlib import Path
from typing import Any, Final

import pytest
import yaml

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR: Final[Path] = REPO_ROOT / '.github/workflows'
DOCS_DIR: Final[Path] = REPO_ROOT / 'docs'


def _read_deployment_security_section() -> str:
    """Return the Security Workflow subsection from docs/deployment.md."""
    deployment_path = DOCS_DIR / 'deployment.md'
    text = deployment_path.read_text()
    start = text.find('### Security Workflow')
    assert start != -1, 'Security Workflow section not found in docs/deployment.md'
    section = text[start:]
    next_section = section.find('###', 3)
    return section if next_section == -1 else section[:next_section]


@pytest.mark.medium
def test_deployment_docs_describe_security_scanner_as_pip_audit() -> None:
    """The deployment guide must describe the security workflow using pip-audit, not Safety."""
    section = _read_deployment_security_section()
    assert 'pip-audit' in section, 'Security Workflow section must mention pip-audit'
    assert 'Safety' not in section, 'Security Workflow section must not mention Safety check'


def _security_workflow_steps() -> list[tuple[str, dict[str, Any]]]:
    """Return every (job_name, step) tuple in the security workflow."""
    workflow_path = WORKFLOWS_DIR / 'security.yml'
    workflow = yaml.safe_load(workflow_path.read_text())
    return [(job_name, step) for job_name, job in workflow.get('jobs', {}).items() for step in job.get('steps', [])]


@pytest.mark.parametrize(('job_name', 'step'), _security_workflow_steps())
@pytest.mark.medium
def test_security_workflow_step_does_not_install_to_system_python(job_name: str, step: dict[str, Any]) -> None:
    """The security workflow must not use uv pip install --system on PEP 668 managed environments."""
    run = step.get('run', '')
    assert 'uv pip install' not in run or '--system' not in run, (
        f'Job {job_name} step "{step.get("name", "")}" uses uv pip install --system, '
        f'which can fail on externally managed Python environments'
    )


@pytest.mark.medium
def test_security_workflow_artifact_jobs_have_actions_write_permission() -> None:
    """Jobs that upload artifacts must explicitly grant actions: write when workflow permissions are restricted."""
    workflow_path = WORKFLOWS_DIR / 'security.yml'
    workflow = yaml.safe_load(workflow_path.read_text())

    top_level_permissions = workflow.get('permissions', {})
    for job_name, job in workflow.get('jobs', {}).items():
        uses_upload_artifact = any(
            step.get('uses', '').startswith('actions/upload-artifact') for step in job.get('steps', [])
        )
        if not uses_upload_artifact:
            continue

        job_permissions = job.get('permissions')
        if job_permissions is None:
            # Inheriting restricted top-level permissions means actions: write is not available.
            assert 'actions' in top_level_permissions, (
                f'Job {job_name} uploads artifacts but inherits restricted top-level permissions '
                f'without any actions scope'
            )
            assert top_level_permissions['actions'] == 'write', (
                f'Job {job_name} uploads artifacts but top-level permissions do not grant actions: write'
            )
        else:
            assert job_permissions.get('actions') == 'write', (
                f'Job {job_name} uploads artifacts but its permissions do not include actions: write'
            )
