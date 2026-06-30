from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

WORKFLOWS_DIR = Path('.github/workflows')
URL_RE = re.compile(r'https?://[^\s\'"`\<\>]+')
CURL_BIN = shutil.which('curl')


@pytest.mark.large
def test_all_workflow_curl_urls_are_reachable() -> None:
    """Every URL fetched by curl in a workflow must be reachable."""
    assert CURL_BIN is not None
    workflow_dir = Path(__file__).resolve().parents[1] / WORKFLOWS_DIR
    failures = []

    for path in sorted(workflow_dir.glob('*.yml')):
        text = path.read_text()
        for line in text.splitlines():
            if 'curl' not in line:
                continue
            for url in URL_RE.findall(line):
                result = subprocess.run(  # noqa: S603
                    [CURL_BIN, '-fsSL', '--head', '--proto', '=https', '--max-time', '15', url],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode != 0:
                    failures.append(
                        f'{path.name}: {url} -> failed ({result.returncode}): {result.stderr.strip()}',
                    )

    assert not failures, '\n'.join(failures)
