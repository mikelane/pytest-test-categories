"""Integration tests for filesystem blocking pytest hooks.

These tests verify that filesystem blocking is properly integrated with pytest hooks:
- pytest_runtest_call activates blocking for small tests
- ALL filesystem operations are blocked for small tests (no exceptions)
- Medium/large/xlarge tests are not blocked

All tests use @pytest.mark.medium since they involve real pytest infrastructure.
"""

from __future__ import annotations

import pytest


@pytest.mark.medium
class DescribeFilesystemBlockingForSmallTests:
    """Integration tests for filesystem blocking during small test execution."""

    def it_blocks_filesystem_for_small_tests_in_strict_mode(self, pytester: pytest.Pytester) -> None:
        """Verify filesystem is blocked for small tests when enforcement=strict."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_small_with_filesystem():
                with open('/etc/passwd', 'r') as f:
                    f.read()
            """
        )

        result = pytester.runpytest('-v')

        # Test should fail with FilesystemAccessViolationError
        stdout = result.stdout.str()
        assert 'FilesystemAccessViolationError' in stdout or 'HermeticityViolationError' in stdout
        result.assert_outcomes(failed=1)

    def it_blocks_tmp_path_for_small_tests(self, pytester: pytest.Pytester) -> None:
        """Verify small tests cannot use pytest's tmp_path fixture (strict hermeticity).

        This is a BREAKING change from previous versions. Small tests must now be
        completely hermetic - no filesystem access at all, including tmp_path.
        Tests that need filesystem access should use @pytest.mark.medium or mock
        with pyfakefs/io.StringIO.
        """
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            from pathlib import Path

            @pytest.mark.small
            def test_small_with_tmp_path(tmp_path: Path):
                # tmp_path is now blocked for small tests
                test_file = tmp_path / 'test.txt'
                test_file.write_text('hello')  # Should fail
            """
        )

        result = pytester.runpytest('-v')

        # Test should fail - tmp_path is blocked for small tests
        stdout = result.stdout.str()
        assert 'FilesystemAccessViolationError' in stdout or 'HermeticityViolationError' in stdout
        result.assert_outcomes(failed=1)

    def it_does_not_block_filesystem_when_enforcement_off(self, pytester: pytest.Pytester) -> None:
        """Verify filesystem is not blocked when enforcement=off."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = off
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            import os

            @pytest.mark.small
            def test_small_without_blocking():
                # Should be able to check if file exists
                assert os.path.exists('/etc/passwd') or True  # Always pass
            """
        )

        result = pytester.runpytest('-v')

        # Test should pass - no blocking
        result.assert_outcomes(passed=1)

    def it_defaults_to_off_enforcement_for_filesystem(self, pytester: pytest.Pytester) -> None:
        """Verify enforcement defaults to 'off' (opt-in feature)."""
        # No ini setting, no CLI option
        pytester.makepyfile(
            test_example="""
            import pytest
            from pathlib import Path

            @pytest.mark.small
            def test_small_without_config():
                # Filesystem operations should work by default
                Path('/tmp').exists()
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # Test should pass - default is no blocking
        result.assert_outcomes(passed=1)


@pytest.mark.medium
class DescribeFilesystemBlockingForOtherSizes:
    """Integration tests for filesystem blocking with non-small tests."""

    def it_does_not_block_medium_tests(self, pytester: pytest.Pytester) -> None:
        """Verify medium tests are not blocked from filesystem access."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            from pathlib import Path

            @pytest.mark.medium
            def test_medium_with_filesystem():
                # Medium tests should not be blocked
                Path('/tmp').exists()
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # Test should pass - medium tests aren't blocked
        result.assert_outcomes(passed=1)

    def it_does_not_block_large_tests(self, pytester: pytest.Pytester) -> None:
        """Verify large tests are not blocked from filesystem access."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            from pathlib import Path

            @pytest.mark.large
            def test_large_with_filesystem():
                # Large tests should not be blocked
                Path('/tmp').exists()
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # Test should pass - large tests aren't blocked
        result.assert_outcomes(passed=1)

    def it_does_not_block_unsized_tests(self, pytester: pytest.Pytester) -> None:
        """Verify tests without size markers are not blocked."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            from pathlib import Path

            def test_unsized_with_filesystem():
                # Tests without size markers should not be blocked
                Path('/tmp').exists()
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # Test should pass - unsized tests aren't blocked
        result.assert_outcomes(passed=1)


@pytest.mark.medium
class DescribeCombinedResourceBlocking:
    """Integration tests for combined network and filesystem blocking."""

    def it_blocks_both_network_and_filesystem_for_small_tests(self, pytester: pytest.Pytester) -> None:
        """Verify both network AND filesystem are blocked for small tests."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_network="""
            import pytest
            import socket

            @pytest.mark.small
            def test_small_with_network():
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(('httpbin.org', 80))
                s.close()
            """,
            test_filesystem="""
            import pytest

            @pytest.mark.small
            def test_small_with_filesystem():
                with open('/etc/passwd', 'r') as f:
                    f.read()
            """,
        )

        result = pytester.runpytest('-v')

        # Both tests should fail
        result.assert_outcomes(failed=2)


@pytest.mark.medium
class DescribeFilesystemBlockingCleanup:
    """Integration tests for filesystem blocking cleanup."""

    def it_restores_open_after_test_failure(self, pytester: pytest.Pytester) -> None:
        """Verify builtins.open is restored even when test fails."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            from pathlib import Path

            @pytest.mark.small
            def test_failing_small():
                assert False  # This test fails

            @pytest.mark.medium
            def test_medium_after_failure(tmp_path: Path):
                # Open should be restored for this test
                test_file = tmp_path / 'test.txt'
                test_file.write_text('hello')
                assert test_file.read_text() == 'hello'
            """
        )

        result = pytester.runpytest('-v')

        # First test fails, second test passes (open restored)
        result.assert_outcomes(passed=1, failed=1)

    def it_restores_open_after_violation_error(self, pytester: pytest.Pytester) -> None:
        """Verify builtins.open is restored after a filesystem violation."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            from pathlib import Path

            @pytest.mark.small
            def test_violating_small():
                # This should fail with FilesystemAccessViolationError
                with open('/etc/passwd', 'r') as f:
                    f.read()

            @pytest.mark.medium
            def test_medium_after_violation(tmp_path: Path):
                # Open should be restored for this test
                test_file = tmp_path / 'test.txt'
                test_file.write_text('world')
                assert test_file.read_text() == 'world'
            """
        )

        result = pytester.runpytest('-v')

        # First test fails with violation, second test passes (open restored)
        result.assert_outcomes(passed=1, failed=1)

    def it_handles_multiple_small_tests_sequentially_all_blocked(self, pytester: pytest.Pytester) -> None:
        """Verify blocking works correctly across multiple small tests - all are blocked."""
        pytester.makeini("""
            [pytest]
            test_categories_enforcement = strict
        """)
        pytester.makepyfile(
            test_example="""
            import pytest
            from pathlib import Path

            @pytest.mark.small
            def test_small_1(tmp_path: Path):
                # All filesystem access is blocked for small tests
                (tmp_path / 'f1.txt').write_text('1')
                assert True

            @pytest.mark.small
            def test_small_2(tmp_path: Path):
                (tmp_path / 'f2.txt').write_text('2')
                assert True

            @pytest.mark.small
            def test_small_3(tmp_path: Path):
                (tmp_path / 'f3.txt').write_text('3')
                assert True
            """
        )

        result = pytester.runpytest('-v')

        # All tests should FAIL - filesystem is blocked for all small tests
        result.assert_outcomes(failed=3)
