"""Adversarial test: the release workflow's "Verify plugin registration" check.

`.github/workflows/release.yml` verifies the published wheel registers with
pytest via:

    if pytest --trace-config 2>&1 | grep -qi "test_categories"; then
      echo "Plugin registered with pytest"
    else
      echo "::warning::pytest_test_categories not found in pytest's plugin list (--trace-config)"
    fi

This step declares `shell: bash`, which GitHub Actions runs as
`bash --noprofile --norc -eo pipefail {0}` -- i.e. with `pipefail` active.

The job that runs this step has no `actions/checkout` step, so the working
directory contains no test files. `pytest --trace-config` in an empty
directory still prints the registered-plugins banner (which contains
"test_categories") to stdout, but then finds zero tests to collect and exits
with status 5 ("no tests collected").

Under `pipefail`, the pipeline's exit status is the *last command to exit
non-zero* -- not the terminal command's (`grep -qi`) status. Since `grep`
matches early and exits 0, but `pytest` still exits 5, the pipeline as a
whole reports non-zero. That sends the `if` to the `else` branch and emits
the "registration unverified" warning even though the plugin **is**
correctly registered.

This test extracts the real if/else block from release.yml and runs it,
under the same `bash --noprofile --norc -eo pipefail` semantics GitHub
Actions uses, from an empty directory with a `pytest` on PATH that has this
plugin installed -- proving the check reports "unverified" even when
registration actually succeeded.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
WORKFLOW_PATH = REPO_ROOT / '.github' / 'workflows' / 'release.yml'


def _extract_plugin_registration_check() -> str:
    """Extract the plugin-registration if/else block from release.yml."""
    workflow_text = WORKFLOW_PATH.read_text()

    # Match the full bash block starting from plugin_trace and ending with fi
    match = re.search(
        r'(plugin_trace=\$\(pytest --trace-config 2>&1 \|\| true\).*?^\s+fi)',
        workflow_text,
        re.MULTILINE | re.DOTALL,
    )

    assert match is not None, 'release.yml no longer contains the expected plugin-registration check'

    return match.group(1)


@pytest.mark.medium
def it_reports_the_plugin_as_registered_when_it_actually_is() -> None:
    """The check must report success, not the unverified warning, when the plugin is really installed."""
    registration_check = _extract_plugin_registration_check()
    venv_bin = Path(sys.executable).parent

    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ)
        env['PATH'] = os.pathsep.join([str(venv_bin), env.get('PATH', '')])

        # Run exactly as the release.yml step does: GitHub Actions' `shell:
        # bash` runs steps as `bash --noprofile --norc -eo pipefail {0}`.
        check_result = subprocess.run(  # noqa: S603
            ['bash', '--noprofile', '--norc', '-eo', 'pipefail', '-c', registration_check],  # noqa: S607
            capture_output=True,
            text=True,
            cwd=tmp,
            env=env,
            check=False,
        )

    assert 'Plugin registered with pytest' in check_result.stdout
    assert '::warning::' not in check_result.stdout


@pytest.mark.medium
def it_emits_the_warning_when_the_plugin_is_genuinely_not_registered(tmp_path: Path) -> None:
    """The check must still warn when the plugin trace genuinely lacks the plugin.

    This guards against a fix for the exit-code-decoupling bug accidentally
    making the check pass unconditionally -- e.g. by matching on something
    that is always present, or by no longer treating a non-matching trace as
    a registration failure.
    """
    registration_check = _extract_plugin_registration_check()

    fake_pytest = tmp_path / 'pytest'
    fake_pytest.write_text(
        '#!/usr/bin/env bash\necho "plugins: cacheprovider, some-other-plugin"\nexit 5\n',
    )
    fake_pytest.chmod(0o755)

    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ)
        env['PATH'] = os.pathsep.join([str(tmp_path), env.get('PATH', '')])

        check_result = subprocess.run(  # noqa: S603
            ['bash', '--noprofile', '--norc', '-eo', 'pipefail', '-c', registration_check],  # noqa: S607
            capture_output=True,
            text=True,
            cwd=tmp,
            env=env,
            check=False,
        )

    assert '::warning::' in check_result.stdout
    assert 'Plugin registered with pytest' not in check_result.stdout
