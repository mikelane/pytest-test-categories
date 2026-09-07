"""Integration tests for pyfakefs compatibility with filesystem enforcement.

Regression coverage for issue #254: a @pytest.mark.small test using pyfakefs's `fs`
fixture got a false FilesystemAccessViolationError ([TC002]) under
--test-categories-enforcement=strict, even though every operation was purely
in-memory. The docs (docs/compatibility.md) recommend pyfakefs as the fix for
TC002, so this false positive broke the documented contract.

Root cause: pyfakefs rebinds module-level globals (`pathlib`, `os`, `shutil`,
`builtins.open`) in every already-imported module -- including this plugin's own
filesystem adapter -- to its own fake implementations. The blocker was patching
those fakes instead of the real filesystem, intercepting purely in-memory
operations and misreporting them as hermeticity violations.

These tests spawn real pytest runs (via the `pytester` fixture) with pyfakefs
installed, so they exercise the real pyfakefs patching machinery rather than a
simulation of it. All tests are marked medium because they involve real pytest
subprocess-style execution via `pytester`.
"""

from __future__ import annotations

import pytest


@pytest.mark.medium
class DescribeFilesystemEnforcementWithPyfakefs:
    """Integration tests for filesystem enforcement when pyfakefs is active."""

    @pytest.fixture(autouse=True)
    def _strict_enforcement_ini(self, pytester: pytest.Pytester) -> None:
        """Configure every pytester run in this class for strict enforcement."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)

    def it_allows_open_write_for_small_tests_with_pyfakefs(self, pytester: pytest.Pytester) -> None:
        """Verify open() writes through pyfakefs don't false-positive under strict mode."""
        pytester.makepyfile(
            test_example="""
            import pytest
            from pyfakefs import fake_filesystem

            pytestmark = pytest.mark.small

            @pytest.fixture(autouse=True)
            def prepare(fs: fake_filesystem.FakeFilesystem) -> None:
                fs.create_file('/data/file.txt', contents='hi')

            def test_open_write():
                with open('/data/file.txt', 'w') as f:
                    f.write('x')
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)

    def it_allows_path_write_text_for_small_tests_with_pyfakefs(self, pytester: pytest.Pytester) -> None:
        """Verify Path.write_text through pyfakefs doesn't false-positive under strict mode."""
        pytester.makepyfile(
            test_example="""
            import pathlib
            import pytest
            from pyfakefs import fake_filesystem

            pytestmark = pytest.mark.small

            @pytest.fixture(autouse=True)
            def prepare(fs: fake_filesystem.FakeFilesystem) -> None:
                fs.create_file('/data/file.txt', contents='hi')

            def test_path_write_text():
                pathlib.Path('/data/file.txt').write_text('x')
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)

    def it_allows_path_read_text_for_small_tests_with_pyfakefs(self, pytester: pytest.Pytester) -> None:
        """Verify Path.read_text through pyfakefs doesn't false-positive under strict mode."""
        pytester.makepyfile(
            test_example="""
            import pathlib
            import pytest
            from pyfakefs import fake_filesystem

            pytestmark = pytest.mark.small

            @pytest.fixture(autouse=True)
            def prepare(fs: fake_filesystem.FakeFilesystem) -> None:
                fs.create_file('/data/file.txt', contents='hi')

            def test_path_read_text():
                assert pathlib.Path('/data/file.txt').read_text() == 'hi'
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)

    def it_allows_path_mkdir_for_small_tests_with_pyfakefs(self, pytester: pytest.Pytester) -> None:
        """Verify Path.mkdir through pyfakefs doesn't false-positive under strict mode."""
        pytester.makepyfile(
            test_example="""
            import pathlib
            import pytest
            from pyfakefs import fake_filesystem

            pytestmark = pytest.mark.small

            @pytest.fixture(autouse=True)
            def prepare(fs: fake_filesystem.FakeFilesystem) -> None:
                pass

            def test_path_mkdir():
                pathlib.Path('/data').mkdir()
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)

    def it_allows_os_remove_for_small_tests_with_pyfakefs(self, pytester: pytest.Pytester) -> None:
        """Verify os.remove through pyfakefs doesn't false-positive under strict mode."""
        pytester.makepyfile(
            test_example="""
            import os
            import pytest
            from pyfakefs import fake_filesystem

            pytestmark = pytest.mark.small

            @pytest.fixture(autouse=True)
            def prepare(fs: fake_filesystem.FakeFilesystem) -> None:
                fs.create_file('/data/file.txt', contents='hi')

            def test_os_remove():
                os.remove('/data/file.txt')
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)

    def it_allows_shutil_copy_for_small_tests_with_pyfakefs(self, pytester: pytest.Pytester) -> None:
        """Verify shutil.copy through pyfakefs doesn't false-positive under strict mode."""
        pytester.makepyfile(
            test_example="""
            import shutil
            import pytest
            from pyfakefs import fake_filesystem

            pytestmark = pytest.mark.small

            @pytest.fixture(autouse=True)
            def prepare(fs: fake_filesystem.FakeFilesystem) -> None:
                fs.create_file('/data/file.txt', contents='hi')

            def test_shutil_copy():
                shutil.copy('/data/file.txt', '/data/file_copy.txt')
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)

    def it_still_blocks_real_filesystem_access_for_small_tests_without_pyfakefs(
        self,
        pytester: pytest.Pytester,
    ) -> None:
        """Verify the fix doesn't disable enforcement wholesale.

        A small test that touches the REAL filesystem (no `fs` fixture, no
        pyfakefs involved at all) must still fail with
        FilesystemAccessViolationError.
        """
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_real_filesystem_access():
                with open('/etc/passwd', 'r') as f:
                    f.read()
            """
        )

        result = pytester.runpytest('-v')

        stdout = result.stdout.str()
        assert 'FilesystemAccessViolationError' in stdout
        result.assert_outcomes(failed=1)

    @pytest.mark.xfail(
        reason=(
            'Known gap tracked in issue #256: module/class/session-scoped pyfakefs fixtures '
            '(fs_module, fs_class, fs_session) leave a fake filesystem resumed for sibling tests '
            'that never requested pyfakefs, with no violation reported. Only the function-scoped '
            '`fs` fixture is currently verified safe.'
        ),
        strict=True,
    )
    def it_does_not_let_a_module_scoped_fake_filesystem_leak_into_a_sibling_test_that_never_requested_it(
        self,
        pytester: pytest.Pytester,
    ) -> None:
        """BUG (issue #254 follow-up).

        pyfakefs's own `pytest_runtest_setup` hook
        resumes any non-function-scoped Patcher (e.g. one created by `fs_module`,
        `fs_class`, or `fs_session`) for EVERY subsequent test in that scope --
        regardless of whether the later test requested any pyfakefs fixture at
        all. `_virtual_filesystem_is_active()` only inspects global module state
        (`pathlib.Path.__module__`, `builtins.open.__module__`, `os`/`shutil`
        identity) and cannot distinguish "this test opted into a fake
        filesystem" from "some earlier test in this module did and left the
        Patcher resumed."

        Concretely: a small test that creates a file via `fs_module` is
        followed by a sibling small test that requests NO pyfakefs fixture at
        all. The sibling still sees -- and successfully reads -- the fabricated
        file the first test created, with zero hermeticity violation reported
        and no test failure. It "passes" against fake data it never consented
        to and believes is real.

        This is distinct from the documented Pause()/fs.pause() caveat (a
        single test using pyfakefs's own API to temporarily restore real access
        to *itself*, documented in docs/compatibility.md,
        docs/troubleshooting/filesystem-violations.md, and
        docs/user-guide/filesystem-isolation.md). Here, an unrelated test that
        never used any pyfakefs fixture inherits another test's fake
        filesystem purely as a side effect of pyfakefs's own hook ordering.
        """
        pytester.makepyfile(
            test_example="""
            import pathlib
            import pytest

            @pytest.mark.small
            def test_1_creates_fake_file(fs_module):
                fs_module.create_file('/secret/leaked.txt', contents='fabricated-by-test-1')

            @pytest.mark.small
            def test_2_never_requested_pyfakefs_but_sees_fake_file():
                # Never requested `fs`, `fs_class`, `fs_module`, or `fs_session`.
                # Believes it is touching the real filesystem. It is not --
                # and no violation is raised for it.
                content = pathlib.Path('/secret/leaked.txt').read_text()
                assert content == 'fabricated-by-test-1'
            """
        )

        result = pytester.runpytest('-v')

        # A test that never opted into a fake filesystem must not silently
        # read fabricated data smuggled in from an unrelated test with zero
        # violation reported. Today both tests pass.
        result.assert_outcomes(failed=1, passed=1)

    @pytest.mark.xfail(
        reason=(
            'Known gap tracked in issue #257: entering `with Patcher():` directly inside a test '
            'body (CALL phase, after this blocker patches builtins.open) can misattribute a cold '
            "import of pyfakefs.patched_packages to the user's test as a TC002 violation. Only "
            'the function-scoped `fs`/`fs_class`/`fs_module`/`fs_session` fixtures (which call '
            'Patcher().setUp() during the SETUP phase, outside this window) are currently verified '
            'safe. Not strict=True: whether the underlying .pyc read is cold depends on which '
            'tests already imported pyfakefs.patched_packages in this process/worker, so this can '
            'XPASS under some xdist/tox orderings without the bug being fixed.'
        ),
        strict=False,
    )
    def it_does_not_false_positive_on_the_manual_patcher_context_manager_on_cold_first_use(
        self,
        pytester: pytest.Pytester,
    ) -> None:
        """BUG (issue #254 family, still reachable through documented API).

        Using pyfakefs's own documented non-fixture API -- `with Patcher():` -- directly
        inside a small test body reproduces the exact false positive #254 fixed
        for the `fs` fixture.

        Root cause: the `fs`/`fs_class`/`fs_module`/`fs_session` fixtures call
        `Patcher().setUp()` during pytest's SETUP phase, which is OUTSIDE this
        plugin's blocker activation window (the blocker only wraps the CALL
        phase, per `pytest_runtest_call` in plugin.py). By the time the test
        body (and this blocker's patched functions) run, pyfakefs has already
        rebound `pathlib`/`os`/`shutil`/`builtins.open`, so `_virtual_filesystem_is_active()`
        correctly reports True from the first access.

        `with Patcher():` invoked directly INSIDE a small test body executes
        during the CALL phase, when this blocker's patches are already
        installed and `_virtual_filesystem_is_active()` still correctly
        reports False (pyfakefs hasn't rebound anything yet). `Patcher.__init__`
        performs a real, one-time import of `pyfakefs.patched_packages`, and on
        a cold import cache, pytest's assertion-rewriting machinery reads that
        module's real `.pyc` file from disk through the ALREADY-patched
        `builtins.open` -- which this blocker misattributes to the user's test
        and reports as a TC002 hermeticity violation, exactly like #254 did for
        the `fs` fixture. The docs recommend pyfakefs as the fix for TC002
        without qualifying that only the fixture form (not the documented
        context-manager form) is currently safe.
        """
        pytester.makepyfile(
            test_example="""
            import pathlib
            import pytest
            from pyfakefs.fake_filesystem_unittest import Patcher

            @pytest.mark.small
            def test_manual_patcher():
                with Patcher() as patcher:
                    patcher.fs.create_file('/data/f.txt', contents='hi')
                    assert pathlib.Path('/data/f.txt').read_text() == 'hi'
            """
        )

        result = pytester.runpytest('-v')

        result.assert_outcomes(passed=1)
