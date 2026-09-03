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

    def it_allows_open_write_for_small_tests_with_pyfakefs(self, pytester: pytest.Pytester) -> None:
        """Verify open() writes through pyfakefs don't false-positive under strict mode."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
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
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
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
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
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
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
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
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
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
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
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
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
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
