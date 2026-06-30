from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.test_workflow_action_inputs import _codecov_validation_bypass_failures


@pytest.mark.small
@pytest.mark.parametrize(
    'uses',
    [
        'mycodecov/codecov-action@v5',
        'acodecov/codecov-action@v5',
        'codecov/codecov-action-fork@v5',
        'codecov/codecov-action-private@v5',
    ],
)
def test_does_not_flag_non_official_codecov_actions(uses: str) -> None:
    """Only the official codecov/codecov-action action should be checked."""
    workflow: dict[str, Any] = {
        'jobs': {
            'test': {
                'steps': [
                    {
                        'uses': uses,
                        'with': {'skip_validation': True},
                    },
                ],
            },
        },
    }
    failures = _codecov_validation_bypass_failures(Path('ci.yml'), workflow)
    assert not failures, f'False positive for unrelated action {uses!r}: {failures}'


@pytest.mark.small
@pytest.mark.parametrize(
    'uses',
    [
        'CODECOV/codecov-action@v5',
        'Codecov/codecov-action@v5',
        'codecov/CODECOV-ACTION@v5',
    ],
)
def test_detects_codecov_action_regardless_of_case(uses: str) -> None:
    """GitHub owner and repo names are case-insensitive; checks must match."""
    workflow: dict[str, Any] = {
        'jobs': {
            'test': {
                'steps': [
                    {
                        'uses': uses,
                        'with': {'skip_validation': True},
                    },
                ],
            },
        },
    }
    failures = _codecov_validation_bypass_failures(Path('ci.yml'), workflow)
    assert failures, f'Case-variant bypass for {uses!r}'


@pytest.mark.small
@pytest.mark.parametrize(
    'value',
    [
        '${{ true }}',
        '${{ env.ALLOW_SKIP }}',
        '${{ inputs.skip_validation }}',
        '${{ vars.SKIP_VALIDATION }}',
    ],
)
def test_rejects_expression_based_truthy_skip_validation(value: str) -> None:
    """GitHub Actions expressions that evaluate to true must not bypass the check."""
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
    failures = _codecov_validation_bypass_failures(Path('ci.yml'), workflow)
    assert failures, f'Expression bypass for skip_validation={value!r}'


@pytest.mark.small
@pytest.mark.parametrize(
    'key',
    [
        'Skip_Validation',
        'SKIP_VALIDATION',
        'skip_Validation',
        'skip validation',
        'SKIP VALIDATION',
    ],
)
def test_detects_skip_validation_with_case_insensitive_keys(key: str) -> None:
    """GitHub Actions input names are case-insensitive and spaces become underscores."""
    workflow: dict[str, Any] = {
        'jobs': {
            'test': {
                'steps': [
                    {
                        'uses': 'codecov/codecov-action@v5',
                        'with': {key: True},
                    },
                ],
            },
        },
    }
    failures = _codecov_validation_bypass_failures(Path('ci.yml'), workflow)
    assert failures, f'Case-variant key bypass for {key!r}'


@pytest.mark.small
@pytest.mark.parametrize(
    'value',
    ['y', 'Y'],
)
def test_rejects_yaml_truthy_y_values(value: str) -> None:
    """YAML truthy spellings 'y' and 'Y' must be rejected like 'yes' and 'on'."""
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
    failures = _codecov_validation_bypass_failures(Path('ci.yml'), workflow)
    assert failures, f'YAML truthy bypass for skip_validation={value!r}'


@pytest.mark.small
@pytest.mark.parametrize(
    'value',
    [
        './codecov',
        '/usr/local/bin/codecov',
        '${{ vars.CODECOV_BINARY }}',
    ],
)
def test_rejects_binary_input_that_bypasses_validation(value: str) -> None:
    """The binary input supplies a pre-downloaded CLI and bypasses integrity checking."""
    workflow: dict[str, Any] = {
        'jobs': {
            'test': {
                'steps': [
                    {
                        'uses': 'codecov/codecov-action@v5',
                        'with': {'binary': value},
                    },
                ],
            },
        },
    }
    failures = _codecov_validation_bypass_failures(Path('ci.yml'), workflow)
    assert failures, f'binary input bypass for binary={value!r}'


@pytest.mark.small
@pytest.mark.parametrize(
    'value',
    [True, 'true', 'yes', 'on', '1', '${{ vars.USE_PYPI }}'],
)
def test_rejects_use_pypi_input_that_bypasses_validation(value: object) -> None:
    """The use_pypi input installs the CLI from PyPI and bypasses GPG/SHA validation."""
    workflow: dict[str, Any] = {
        'jobs': {
            'test': {
                'steps': [
                    {
                        'uses': 'codecov/codecov-action@v5',
                        'with': {'use_pypi': value},
                    },
                ],
            },
        },
    }
    failures = _codecov_validation_bypass_failures(Path('ci.yml'), workflow)
    assert failures, f'use_pypi input bypass for use_pypi={value!r}'
