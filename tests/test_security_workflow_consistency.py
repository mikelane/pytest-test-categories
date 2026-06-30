from __future__ import annotations

from pathlib import Path

import pytest
import yaml

WORKFLOWS_DIR = Path('.github/workflows')
DOCS_DIR = Path('docs')


@pytest.mark.medium
def test_deployment_docs_describe_security_scanner_as_pip_audit() -> None:
    """The deployment guide must describe the security workflow using pip-audit, not Safety."""
    deployment_path = Path(__file__).resolve().parents[1] / DOCS_DIR / 'deployment.md'
    text = deployment_path.read_text()

    start = text.find('### Security Workflow')
    assert start != -1, 'Security Workflow section not found in docs/deployment.md'

    section = text[start:]
    section = section[: section.find('###', 3)]  # stop at next subsection

    assert 'pip-audit' in section, 'Security Workflow section must mention pip-audit'
    assert 'Safety' not in section, 'Security Workflow section must not mention Safety check'


@pytest.mark.medium
def test_security_workflow_does_not_install_to_system_python() -> None:
    """The security workflow must not use uv pip install --system, which fails on PEP 668 managed environments."""
    workflow_path = Path(__file__).resolve().parents[1] / WORKFLOWS_DIR / 'security.yml'
    workflow = yaml.safe_load(workflow_path.read_text())

    for job_name, job in workflow.get('jobs', {}).items():
        for step in job.get('steps', []):
            run = step.get('run', '')
            assert 'uv pip install' not in run or '--system' not in run, (
                f'Job {job_name} step "{step.get("name", "")}" uses uv pip install --system, '
                f'which can fail on externally managed Python environments'
            )
