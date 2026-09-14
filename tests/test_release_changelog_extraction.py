"""Adversarial test: the release workflow's changelog-extraction awk command.

`.github/workflows/release.yml` extracts release notes with:

    awk "/^## v$VERSION /{flag=1; next} /^## v/{flag=0} flag" CHANGELOG.md

`$VERSION` is interpolated directly into the awk *regular expression* without
escaping. Periods in a version string (e.g. "1.2.2") are regex metacharacters
that match any single character, not just a literal period. A changelog
heading crafted to align with those wildcard positions can therefore satisfy
`/^## v$VERSION /` even though it names a different (or bogus) version --
and because that heading appears before the real one, its content is
captured into (and, since the real heading *also* still matches the first
pattern and re-triggers `next` instead of the reset pattern, merged with)
the release notes that ship in the GitHub Release body.

This test extracts the real awk command straight out of release.yml (so it
fails the moment anyone changes the command, keeping the test honest) and
proves that untrusted changelog content preceding the real version heading
leaks into the extracted release notes.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
WORKFLOW_PATH = REPO_ROOT / '.github' / 'workflows' / 'release.yml'

SPOOFED_CHANGELOG = """## [Unreleased]

## v1a2a2 (2020-01-01)

### Fixed

- SPOOFED CONTENT injected by an untrusted changelog edit

## v1.2.2 (2026-09-13)

### Fixed

- Real content for this release
"""


def _extract_changelog_extraction_script() -> str:
    """Extract the changelog-extraction shell script from release.yml.

    Returns a script that is one line (just the awk command) when no
    VERSION_RE setup precedes it in the workflow, or two lines (the
    VERSION_RE assignment followed by the awk command) when it does.
    Callers must not assume a single line.
    """
    workflow_text = WORKFLOW_PATH.read_text()

    # Try to extract both VERSION_RE (if present) and the awk command
    match_version_re = re.search(
        r'(VERSION_RE=\$\(printf \'%s\' "\$VERSION"[^\)]+\))',
        workflow_text,
    )
    match_awk = re.search(r'(awk "[^"]+" CHANGELOG\.md)', workflow_text)

    assert match_awk is not None, 'release.yml no longer contains the expected awk extraction command'

    if match_version_re:
        # Return both VERSION_RE setup and awk command
        return match_version_re.group(1) + '\n' + match_awk.group(1)
    # Just return the awk command
    return match_awk.group(1)


@pytest.mark.medium
@pytest.mark.skipif(
    sys.platform == 'win32',
    reason=(
        'The VERSION_RE/awk changelog-extraction script this test validates only runs in the '
        'github-release job, which is runs-on: ubuntu-latest with no OS matrix — it never '
        "executes on a Windows runner in production. Git for Windows' bundled awk/sed differ "
        'from GNU coreutils in ways that make this test unreliable there (confirmed via CI: '
        'the script returns exit 0 but empty output) without validating anything that actually '
        'happens in the release pipeline.'
    ),
)
def it_does_not_leak_content_preceding_the_real_version_heading(bash_exe: str) -> None:
    """A changelog heading that only coincidentally matches via wildcard dots must not be extracted."""
    extraction_script = _extract_changelog_extraction_script()

    with tempfile.TemporaryDirectory() as tmp:
        changelog_path = Path(tmp) / 'CHANGELOG.md'
        changelog_path.write_text(SPOOFED_CHANGELOG)

        # Run exactly as the workflow does: bash expands $VERSION into the
        # awk program text before awk ever sees it.
        extraction_result = subprocess.run(  # noqa: S603
            [bash_exe, '-c', f'VERSION=1.2.2\n{extraction_script}'],
            capture_output=True,
            text=True,
            cwd=tmp,
            check=True,
        )

    assert 'SPOOFED CONTENT' not in extraction_result.stdout
    assert 'Real content for this release' in extraction_result.stdout
