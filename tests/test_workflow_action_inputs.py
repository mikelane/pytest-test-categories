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


def _codecov_skip_validation_failures(path: Path, workflow: dict[str, Any]) -> list[str]:
    """Return failures for any official Codecov step that disables CLI validation."""
    failures: list[str] = []
    for job in workflow.get('jobs', {}).values():
        for step in job.get('steps', []):
            uses = step.get('uses', '')
            inputs = step.get('with') or {}
            if not isinstance(inputs, dict):
                continue
            match = USES_RE.match(uses)
            if not match:
                continue
            owner_repo = match.group(1).lower()
            if owner_repo != 'codecov/codecov-action':
                continue
            for key, value in inputs.items():
                normalized_key = key.upper().replace(' ', '_')
                if normalized_key != 'SKIP_VALIDATION':
                    continue
                value_str = str(value).strip().lower()
                if value_str in {'true', 'yes', 'on', 'y', '1'}:
                    failures.append(f'{path.name}: {uses}: skip_validation must not be set to a truthy value')
                elif '${{' in value_str:
                    failures.append(f'{path.name}: {uses}: skip_validation must not be an expression')
    return failures


@pytest.mark.medium
def test_codecov_validation_is_not_disabled() -> None:
    """The Codecov upload step must verify the CLI binary integrity."""
    workflow_path = Path(__file__).resolve().parents[1] / WORKFLOWS_DIR / 'ci.yml'
    workflow = yaml.safe_load(workflow_path.read_text())
    failures = _codecov_skip_validation_failures(workflow_path, workflow)
    assert not failures, '\n'.join(failures)


@pytest.mark.small
@pytest.mark.parametrize(
    'value',
    ['true', 'True', 'TRUE', 'yes', 'Yes', 'YES', 'on', 'On', 'ON', '1', True, 1],
)
def test_rejects_truthy_skip_validation_values(value: object) -> None:
    """Any GitHub-Actions truthy value for skip_validation must be rejected."""
    workflow: dict[str, Any] = {
        'jobs': {
            'test': {
                'steps': [
                    {
                        'uses': 'codecov/codecov-action@v5',
                        'with': {'skip_validation': value},
                    },
                ],
            },
        },
    }
    failures = _codecov_skip_validation_failures(Path('ci.yml'), workflow)
    assert failures, f'Expected failure for skip_validation={value!r}'


@pytest.mark.small
@pytest.mark.parametrize(
    'value',
    [
        'false',
        'False',
        'FALSE',
        'no',
        'No',
        'NO',
        'n',
        'N',
        'off',
        'Off',
        'OFF',
        '0',
        False,
        0,
    ],
)
def test_allows_falsy_skip_validation_values(value: object) -> None:
    """GitHub-Actions falsy values for skip_validation must be allowed."""
    workflow: dict[str, Any] = {
        'jobs': {
            'test': {
                'steps': [
                    {
                        'uses': 'codecov/codecov-action@v5',
                        'with': {'skip_validation': value},
                    },
                ],
            },
        },
    }
    failures = _codecov_skip_validation_failures(Path('ci.yml'), workflow)
    assert not failures, f'Unexpected failure for skip_validation={value!r}'
