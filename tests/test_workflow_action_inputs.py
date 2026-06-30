from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

WORKFLOWS_DIR = Path('.github/workflows')
USES_RE = re.compile(r'^([^/]+/[^/@]+)(?:/([^@]+))?@(.+)$')
CURL_BIN = shutil.which('curl')


def _fetch_action_yaml(url: str) -> dict[str, Any] | None:
    assert CURL_BIN is not None
    result = subprocess.run(  # noqa: S603
        [CURL_BIN, '-fsSL', '--proto', '=https', '--max-time', '15', url],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    parsed: dict[str, Any] | None = yaml.safe_load(result.stdout)
    if parsed is None or not isinstance(parsed, dict):
        return None
    return parsed


def _action_yaml_urls(owner_repo: str, subpath: str | None, ref: str) -> list[str]:
    base_path = f'{subpath}/' if subpath else ''
    return [
        f'https://raw.githubusercontent.com/{owner_repo}/{ref}/{base_path}action.yml',
        f'https://raw.githubusercontent.com/{owner_repo}/{ref}/{base_path}action.yaml',
    ]


def _invalid_inputs_for_step(
    path: Path,
    uses: str,
    inputs: dict[str, object],
) -> list[str]:
    match = USES_RE.match(uses)
    if not match:
        return [f'{path.name}: {uses}: unable to parse action reference']

    owner_repo, subpath, ref = match.groups()
    action_yaml = None
    for url in _action_yaml_urls(owner_repo, subpath, ref):
        action_yaml = _fetch_action_yaml(url)
        if action_yaml is not None:
            break

    if action_yaml is None:
        return [f'{path.name}: {uses}: unable to fetch action.yml or action.yaml']

    defined_inputs = set(action_yaml.get('inputs', {}).keys())
    return [
        f'{path.name}: {uses}: input "{input_name}" is not defined in action.yml'
        for input_name in inputs
        if input_name not in defined_inputs
    ]


@pytest.mark.large
def test_all_workflow_action_inputs_are_valid() -> None:
    """Every input passed to a GitHub Action must be defined in its action.yml."""
    workflow_dir = Path(__file__).resolve().parents[1] / WORKFLOWS_DIR
    failures: list[str] = []

    for path in sorted(workflow_dir.glob('*.yml')):
        workflow = yaml.safe_load(path.read_text())
        for job in workflow.get('jobs', {}).values():
            for step in job.get('steps', []):
                uses = step.get('uses')
                inputs = step.get('with')
                if not uses or not inputs:
                    continue
                failures.extend(_invalid_inputs_for_step(path, uses, inputs))

    assert not failures, '\n'.join(failures)


@pytest.mark.medium
def test_codecov_validation_is_not_disabled() -> None:
    """The Codecov upload step must verify the CLI binary integrity."""
    workflow_path = Path(__file__).resolve().parents[1] / WORKFLOWS_DIR / 'ci.yml'
    workflow = yaml.safe_load(workflow_path.read_text())
    failures: list[str] = []

    for job in workflow.get('jobs', {}).values():
        for step in job.get('steps', []):
            uses = step.get('uses', '')
            inputs = step.get('with') or {}
            if not isinstance(inputs, dict):
                continue
            skip_validation = str(inputs.get('skip_validation', '')).lower()
            if 'codecov/codecov-action' in uses and skip_validation == 'true':
                failures.append(f'{workflow_path.name}: {uses}: skip_validation must not be true')

    assert not failures, '\n'.join(failures)
